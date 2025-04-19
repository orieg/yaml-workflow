"""
Core workflow engine implementation.
"""

import importlib
import inspect
import logging
import logging.handlers
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, cast

import yaml
from jinja2 import StrictUndefined, Template

from .exceptions import (
    FlowError,
    FlowNotFoundError,
    FunctionNotFoundError,
    InvalidFlowDefinitionError,
    StepExecutionError,
    StepNotInFlowError,
    TaskExecutionError,
    TemplateError,
    WorkflowError,
)
from .state import ExecutionState, WorkflowState
from .tasks import TaskConfig, get_task_handler
from .template import TemplateEngine
from .utils.yaml_utils import get_safe_loader
from .workspace import create_workspace, get_workspace_info


def setup_logging(workspace: Path, name: str) -> logging.Logger:
    """
    Set up logging configuration for the workflow.

    Args:
        workspace: Workspace directory
        name: Name of the workflow

    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    logs_dir = workspace / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create log file path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{name}_{timestamp}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Create and return workflow logger
    logger = logging.getLogger("workflow")
    logger.info(f"Logging to: {log_file}")
    return logger


class WorkflowEngine:
    """Main workflow engine class."""

    def __init__(
        self,
        workflow: str | Dict[str, Any],
        workspace: Optional[str] = None,
        base_dir: str = "runs",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the workflow engine.

        Args:
            workflow: Path to workflow YAML file or workflow definition dictionary
            workspace: Optional custom workspace directory
            base_dir: Base directory for workflow runs
            metadata: Optional pre-loaded metadata for resuming workflows

        Raises:
            WorkflowError: If workflow file not found or invalid
        """
        # Load workflow definition
        if isinstance(workflow, dict):
            self.workflow = workflow
            self.workflow_file = None
        else:
            self.workflow_file = Path(workflow)
            if not self.workflow_file.exists():
                raise WorkflowError(f"Workflow file not found: {workflow}")

            # Load workflow from file
            try:
                with open(self.workflow_file) as f:
                    self.workflow = yaml.load(f, Loader=get_safe_loader())
            except yaml.YAMLError as e:
                raise WorkflowError(f"Invalid YAML in workflow file: {e}")

        # Validate workflow structure
        if not isinstance(self.workflow, dict):
            raise WorkflowError("Invalid workflow format: root must be a mapping")

        # Validate required sections
        if not self.workflow.get("steps") and not self.workflow.get("flows"):
            raise WorkflowError(
                "Invalid workflow file: missing both 'steps' and 'flows' sections"
            )

        # Get workflow name
        self.name = self.workflow.get("name")
        if not self.name:
            if self.workflow_file:
                self.name = self.workflow_file.stem
            else:
                self.name = "workflow"

        # Create workspace
        self.workspace = create_workspace(self.name, workspace, base_dir)
        self.workspace_info = get_workspace_info(self.workspace)

        # Set up logging
        self.logger = setup_logging(self.workspace, self.name)

        # Initialize workflow state with pre-loaded metadata if available
        self.state = WorkflowState(self.workspace, metadata)

        # Initialize template engine
        self.template_engine = TemplateEngine()

        # Initialize context with default parameter values
        self.context = {
            "workflow_name": self.name,
            "workspace": str(self.workspace),
            "run_number": self.workspace_info.get("run_number"),
            "timestamp": datetime.now().isoformat(),
            # Initialize namespaced variables
            "args": {},
            "env": dict(os.environ),
            "steps": {},
        }

        # Add workflow file path if available
        if self.workflow_file:
            self.context["workflow_file"] = str(self.workflow_file.absolute())

        # Load default parameter values from workflow file
        params = self.workflow.get("params", {})
        for param_name, param_config in params.items():
            if isinstance(param_config, dict) and "default" in param_config:
                # Store in both root (backward compatibility) and args namespace
                default_value = param_config["default"]
                self.context[param_name] = default_value
                self.context["args"][param_name] = default_value
            elif isinstance(param_config, dict):
                # Handle case where param is defined but no default
                self.context["args"][param_name] = None
            else:
                # Handle simple parameter definition
                self.context[param_name] = param_config
                self.context["args"][param_name] = param_config

        # If there's existing state, restore step outputs to context
        if self.state.metadata.get("execution_state", {}).get("step_outputs"):
            step_outputs = self.state.metadata["execution_state"]["step_outputs"]
            for step_name, outputs in step_outputs.items():
                if isinstance(outputs, dict):
                    # If outputs is a dict with a single key matching step name, use its value
                    if len(outputs) == 1 and step_name in outputs:
                        self.context[step_name] = outputs[step_name]
                    else:
                        self.context[step_name] = outputs
                else:
                    self.context[step_name] = outputs

        # Validate flows if present
        self._validate_flows()

        self.logger.info(f"Initialized workflow: {self.name}")
        self.logger.info(f"Workspace: {self.workspace}")
        self.logger.info(f"Run number: {self.context['run_number']}")
        if params:
            self.logger.info("Default parameters loaded:")
            for name, value in self.context["args"].items():
                self.logger.info(f"  {name}: {value}")

        self.current_step = None  # Track current step for error handling

    def _validate_flows(self) -> None:
        """Validate workflow flows configuration."""
        flows = self.workflow.get("flows", {})
        if not flows:
            return

        if not isinstance(flows, dict):
            raise InvalidFlowDefinitionError("root", "flows must be a mapping")

        # Validate flows structure
        if "definitions" not in flows:
            raise InvalidFlowDefinitionError("root", "missing 'definitions' section")

        if not isinstance(flows["definitions"], list):
            raise InvalidFlowDefinitionError("root", "'definitions' must be a list")

        # Validate each flow definition
        defined_flows: Set[str] = set()
        for flow_def in flows["definitions"]:
            if not isinstance(flow_def, dict):
                raise InvalidFlowDefinitionError(
                    "unknown", "flow definition must be a mapping"
                )

            for flow_name, steps in flow_def.items():
                if not isinstance(steps, list):
                    raise InvalidFlowDefinitionError(flow_name, "steps must be a list")

                # Check for duplicate flow names
                if flow_name in defined_flows:
                    raise InvalidFlowDefinitionError(flow_name, "duplicate flow name")
                defined_flows.add(flow_name)

                # Validate step references
                workflow_steps = {
                    step.get("name") for step in self.workflow.get("steps", [])
                }
                for step in steps:
                    if step not in workflow_steps:
                        raise StepNotInFlowError(step, flow_name)

        # Validate default flow
        default_flow = flows.get("default")
        if default_flow and default_flow not in defined_flows and default_flow != "all":
            raise FlowNotFoundError(default_flow)

    def _get_flow_steps(self, flow_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get ordered list of steps for a flow."""
        all_steps = self.workflow.get("steps", [])
        if not all_steps:
            raise WorkflowError("No steps defined in workflow")

        # If no flows defined or flow is "all", return all steps
        flows = self.workflow.get("flows", {})
        if not flows or flow_name == "all":
            return all_steps

        # Get flow definition
        flow_to_use = flow_name or flows.get("default", "all")
        if flow_to_use == "all":
            return all_steps

        # Find flow steps in definitions
        flow_steps = None
        defined_flows: Set[str] = set()
        for flow_def in flows.get("definitions", []):
            if isinstance(flow_def, dict):
                defined_flows.update(flow_def.keys())
                if flow_to_use in flow_def:
                    flow_steps = flow_def[flow_to_use]
                    break

        if not flow_steps:
            raise FlowNotFoundError(flow_to_use)

        # Map step names to step configurations
        step_map = {step.get("name"): step for step in all_steps}
        ordered_steps = []
        for step_name in flow_steps:
            if step_name not in step_map:
                raise StepNotInFlowError(step_name, flow_to_use)
            ordered_steps.append(step_map[step_name])

        return ordered_steps

    def run(
        self,
        params: Optional[Dict[str, Any]] = None,
        resume_from: Optional[str] = None,
        start_from: Optional[str] = None,
        skip_steps: Optional[List[str]] = None,
        flow: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Run the workflow.

        Args:
            params: Optional parameters to pass to the workflow
            resume_from: Optional step name to resume from after failure (preserves outputs)
            start_from: Optional step name to start execution from (fresh start)
            skip_steps: Optional list of step names to skip during execution
            flow: Optional flow name to execute. If not specified, uses default flow.
            max_retries: Global maximum number of retries for failed steps (default: 3)

        Returns:
            dict: Workflow results
        """
        # Update context with provided parameters (overriding defaults)
        if params:
            # Update both root (backward compatibility) and args namespace
            self.context.update(params)
            self.context["args"].update(params)
            self.logger.info("Parameters provided:")
            for name, value in params.items():
                self.logger.info(f"  {name}: {value}")

        # Handle resume from parameter validation failure
        if (
            resume_from
            and self.state.metadata["execution_state"]["failed_step"]
            and self.state.metadata["execution_state"]["failed_step"]["step_name"]
            == "parameter_validation"
        ):
            # Reset state but keep the failed status
            self.state.reset_state()
            self.state.metadata["execution_state"]["status"] = "failed"
            resume_from = None

        # Validate required parameters
        workflow_params = self.workflow.get("params", {})
        for param_name, param_config in workflow_params.items():
            if isinstance(param_config, dict):
                if param_config.get("required", False):
                    if (
                        param_name not in self.context["args"]
                        or self.context["args"][param_name] is None
                    ):
                        error_msg = f"Required parameter '{param_name}' is undefined"
                        self.state.mark_step_failed("parameter_validation", error_msg)
                        raise WorkflowError(error_msg)
                    if "minLength" in param_config:
                        value = str(self.context["args"][param_name])
                        if len(value) < param_config["minLength"]:
                            error_msg = f"Parameter '{param_name}' must be at least {param_config['minLength']} characters long"
                            self.state.mark_step_failed(
                                "parameter_validation", error_msg
                            )
                            raise WorkflowError(error_msg)

        # Get flow configuration
        flows = self.workflow.get("flows", {})

        # Determine which flow to use
        if resume_from:
            # When resuming, use the flow from the previous execution
            saved_flow = self.state.get_flow()
            if saved_flow and flow and saved_flow != flow:
                raise WorkflowError(
                    f"Cannot resume with different flow. Previous flow was '{saved_flow}', "
                    f"requested flow is '{flow}'"
                )
            flow = saved_flow
        else:
            # For new runs, determine the flow to use
            flow_to_use = flow or flows.get("default", "all")

            # Validate flow exists if specified
            if flow and flows:
                # Check if flow exists in definitions
                defined_flows: Set[str] = set()
                for flow_def in flows.get("definitions", []):
                    if isinstance(flow_def, dict):
                        defined_flows.update(flow_def.keys())

                if flow != "all" and flow not in defined_flows:
                    raise FlowNotFoundError(flow)

            # Set the flow before we start
            if flows or (flow and flow != "all"):
                self.state.set_flow(flow_to_use)
                self.logger.info(f"Using flow: {flow_to_use}")
            flow = flow_to_use

        # Get steps for the specified flow
        try:
            steps = self._get_flow_steps(flow)
        except WorkflowError as e:
            self.logger.error(str(e))
            raise

        if not steps:
            raise WorkflowError("No steps to execute")

        # Handle workflow resumption vs fresh start
        if resume_from:
            # Verify workflow is in failed state and step exists
            state = self.state.metadata["execution_state"]
            if state["status"] != "failed" or not state["failed_step"]:
                raise WorkflowError("Cannot resume: workflow is not in failed state")
            if not any(step.get("name") == resume_from for step in steps):
                raise WorkflowError(
                    f"Cannot resume: step '{resume_from}' not found in workflow"
                )

            # Restore outputs from completed steps
            self.context.update(self.state.get_completed_outputs())
            self.logger.info(f"Resuming workflow from failed step: {resume_from}")
        else:
            # Reset state for fresh run
            self.state.reset_state()
            # Set the flow for the new run (again after reset)
            if flows or (flow and flow != "all"):
                self.state.set_flow(flow)

        # Initialize execution state if not resuming
        if not resume_from:
            self.state.initialize_execution()

        # Restore step outputs from state if resuming or has previous state
        if self.state.metadata.get("execution_state", {}).get("step_outputs"):
            self.context["steps"] = self.state.metadata["execution_state"][
                "step_outputs"
            ].copy()

        # Determine the sequence of steps to execute
        all_steps = self._get_flow_steps(flow)
        step_dict = {step["name"]: step for step in all_steps}

        # Determine starting point
        start_index = 0
        if resume_from:
            if resume_from not in step_dict:
                raise StepNotInFlowError(
                    resume_from,
                    flow or "default",
                )
            start_index = next(
                (i for i, step in enumerate(all_steps) if step["name"] == resume_from),
                0,
            )
            self.logger.info(f"Resuming workflow from step: {resume_from}")
        elif start_from:
            if start_from not in step_dict:
                raise StepNotInFlowError(start_from, flow or "default")
            start_index = next(
                (i for i, step in enumerate(all_steps) if step["name"] == start_from),
                0,
            )
            self.logger.info(f"Starting workflow from step: {start_from}")

        # Apply initial skips only - runtime skips are handled in execute_step
        steps_to_execute_initially = all_steps[start_index:]
        initial_skip_set = set(skip_steps or [])
        steps_to_execute = [
            step
            for step in steps_to_execute_initially
            if step["name"] not in initial_skip_set
        ]

        # Main execution loop
        current_index = 0
        executed_step_names: Set[str] = set(self.state.get_executed_steps())
        while current_index < len(steps_to_execute):
            step = steps_to_execute[current_index]
            step_name = step["name"]

            # Skip if already executed (in case of resume/retry jumps)
            if step_name in executed_step_names:
                self.logger.info(f"Skipping already executed step: {step_name}")
                current_index += 1
                continue

            # Execute step with retry/error handling
            try:
                self.execute_step(step, max_retries)
                executed_step_names.add(step_name)
                current_index += 1
            except TaskExecutionError as e:
                # Check if it was a retry request first!
                if isinstance(e, RetryStepException):
                    self.logger.debug(
                        f"Caught RetryStepException for step '{step_name}'. Looping."
                    )
                    # Don't increment current_index, just continue the loop
                    continue

                # Not a retry, so it's either a jump or a final halt
                self.logger.debug(
                    f"TaskExecutionError caught in run loop for step '{step_name}'. Checking for error flow."
                )
                error_flow_target = self.state.get_error_flow_target()
                if error_flow_target:
                    # --- Handle Error Flow Jump ---
                    self.logger.info(
                        f"Jumping to error handling step: {error_flow_target}"
                    )
                    if error_flow_target not in step_dict:
                        raise StepNotInFlowError(
                            error_flow_target,
                            flow or "default",
                        )
                    # Find the index of the target step in the original list
                    try:
                        target_index_in_all = next(
                            i
                            for i, s in enumerate(all_steps)
                            if s["name"] == error_flow_target
                        )
                        # Find the corresponding index in the potentially filtered steps_to_execute
                        # This is complex if skips happened. Easier to rebuild the list from target.
                        # Rebuild steps_to_execute from the target onwards
                        steps_to_execute = [
                            s
                            for s in all_steps[target_index_in_all:]
                            if s["name"] not in initial_skip_set
                        ]
                        current_index = 0
                        self.state.clear_error_flow_target()
                        continue
                    except StopIteration:
                        # Should not happen if step_dict check passed, but belt-and-suspenders
                        self.logger.error(
                            f"Internal error: Could not find index for error target '{error_flow_target}'"
                        )
                        raise
                else:
                    # The error was already marked as terminally failed in execute_step
                    # which also sets the workflow state to failed.
                    # Re-raise a WorkflowError to signal the end of execution
                    root_cause = e.original_error or e  # Get the actual root cause
                    final_error_message = f"Workflow halted at step '{step_name}' due to unhandled error: {root_cause}"  # Use root cause in message
                    self.logger.error(final_error_message)
                    # No need to call mark_workflow_failed here; mark_step_failed in execute_step handles it.
                    # *** Simplification: Pass the *actual* root cause as original_error ***
                    raise WorkflowError(
                        final_error_message, original_error=root_cause
                    ) from root_cause
            except Exception as e:
                # Catch unexpected errors during engine loop logic itself
                self.logger.error(
                    f"Unexpected engine error during step '{step_name}': {e}",
                    exc_info=True,
                )
                # Mark the step as failed (which also marks workflow as failed)
                # Use a generic error message as this is an engine-level failure
                engine_error_msg = (
                    f"Unexpected engine error during step '{step_name}': {e}"
                )
                if (
                    self.current_step
                ):  # current_step might be None if error happens outside a step
                    self.state.mark_step_failed(self.current_step, engine_error_msg)
                else:
                    # If we don't know the step, mark the workflow directly (though this is less ideal)
                    # We might need a way to handle non-step-specific failures better.
                    # For now, let's just log and re-raise, assuming execute_step handled state.
                    pass  # Avoid redundant state marking if possible

                # Wrap this in StepExecutionError for clarity, only passing original_error
                raise StepExecutionError(step_name, original_error=e)

        # Save final state only if no exceptions occurred during the loop
        # Check status before marking completed
        final_state = cast(ExecutionState, self.state.metadata["execution_state"])
        if final_state["status"] != "failed":
            self.state.mark_workflow_completed()
            self.state.save()
            self.logger.info("Workflow completed successfully.")
            self.logger.info("Final workflow outputs:")
            for key, value in self.context["steps"].items():
                self.logger.info(f"  {key}: {value}")

        return {
            "status": "completed",
            "outputs": self.context["steps"],
            "execution_state": self.state.metadata["execution_state"],
        }

    def setup_workspace(self) -> Path:
        """
        Set up the workspace for this workflow run.

        Returns:
            Path: Path to the workspace directory
        """
        # Get workflow name from usage section or file name
        workflow_name = self.workflow.get("usage", {}).get("name") or (
            self.workflow_file.stem if self.workflow_file else "unnamed_workflow"
        )

        # Create workspace
        self.workspace = create_workspace(
            workflow_name=workflow_name,
            custom_dir=getattr(self, "workspace_dir", None),
            base_dir=getattr(self, "base_dir", "runs"),
        )

        # Initialize workspace info in context
        workspace_info = get_workspace_info(self.workspace)
        self.context.update(
            {
                "workspace": str(self.workspace),
                "run_number": int(self.workspace.name.split("_run_")[-1]),
                "timestamp": datetime.now().isoformat(),
                "workflow_name": workflow_name,
                "workflow_file": str(
                    self.workflow_file.absolute() if self.workflow_file else ""
                ),
            }
        )

        self.logger.info(f"Created workspace: {self.workspace}")
        return self.workspace

    def resolve_template(self, template_str: str) -> str:
        """
        Resolve template with both direct and namespaced variables.

        Args:
            template_str: Template string to resolve

        Returns:
            str: Resolved template string

        Raises:
            TemplateError: If template resolution fails
        """
        return self.template_engine.process_template(template_str, self.context)

    def resolve_value(self, value: Any) -> Any:
        """
        Resolve a single value that might contain templates.

        Args:
            value: Value to resolve, can be any type

        Returns:
            Resolved value with templates replaced
        """
        if isinstance(value, str):
            return self.template_engine.process_template(value, self.context)
        elif isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self.resolve_value(v) for v in value]
        return value

    def resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all inputs using Jinja2 template resolution.

        Args:
            inputs: Input dictionary

        Returns:
            Dict[str, Any]: Resolved inputs
        """
        return self.template_engine.process_value(inputs, self.context)

    def execute_step(self, step: Dict[str, Any], global_max_retries: int) -> None:
        """
        Execute a single workflow step.

        Args:
            step: Step definition dictionary
            global_max_retries: Global default for maximum retries

        Raises:
            TaskExecutionError: If step execution ultimately fails after retries.
            StepExecutionError: For issues preparing the step itself.
            RetryStepException: If step should be retried.
        """
        step_name = step.get("name")
        if not step_name:
            raise StepExecutionError(
                "Unnamed Step",
                Exception("Step definition missing required 'name' field"),
            )

        self.current_step = step_name
        self.logger.info(f"Executing step: {step_name}")
        self.state.set_current_step(step_name)

        # Prepare task config
        task_config = TaskConfig(
            step=step,
            context=self.context,
            workspace=self.workspace,
        )

        # Find the task handler
        task_type = step.get("task")
        if not task_type:
            # Raise StepExecutionError for config issues before task execution attempt
            raise StepExecutionError(
                step_name, Exception("Step definition missing 'task' definition")
            )

        handler = get_task_handler(task_type)
        if not handler:
            # Raise StepExecutionError for config issues before task execution attempt
            raise StepExecutionError(
                step_name, Exception(f"Unknown task type: '{task_type}'")
            )

        # --- Condition Check ---
        condition = step.get("condition")
        should_execute = True
        if condition:
            try:
                # Resolve the template, which should result in "True" or "False" (case-insensitive)
                resolved_condition_str = (
                    str(self.resolve_template(condition)).strip().lower()
                )

                # Check if the resolved string indicates truthiness
                if resolved_condition_str != "true":
                    should_execute = False

                self.logger.debug(
                    f"Step '{step_name}' condition '{condition}' resolved to string '{resolved_condition_str}'. Should execute: {should_execute}"
                )
            except Exception as e:
                # Treat condition resolution errors as skip, but log a warning
                self.logger.warning(
                    f"Could not resolve condition '{condition}' for step '{step_name}': {e}. Skipping step."
                )
                should_execute = False

        if not should_execute:
            self.logger.info(
                f"Skipping step '{step_name}' due to condition: {condition}"
            )
            # NOTE: We might want to record skipped steps in the state later.
            # For now, just return without executing or marking success/failure.
            return

        # --- Refactored Execution and Error Handling ---
        step_failed = False
        step_error: Optional[Exception] = None
        result: Any = None

        try:
            # --- Execute Task Handler ---
            result = handler(task_config)
            self.logger.debug(f"Step '{step_name}' completed successfully in handler.")

        except Exception as e:
            # --- Catch ANY exception from the handler ---
            self.logger.warning(
                f"Step '{step_name}' caught exception during execution: {e}"
            )
            step_failed = True
            step_error = e  # Store the caught error

            # Ensure it's a TaskExecutionError, wrapping if necessary
            if not isinstance(step_error, TaskExecutionError):
                self.logger.debug(
                    f"Wrapping non-TaskExecutionError: {type(step_error).__name__}"
                )
                step_error = TaskExecutionError(
                    step_name=step_name,
                    original_error=step_error,
                    # Pass the raw step dict as task_config for context
                    task_config=task_config.step,
                )
            else:
                self.logger.debug(f"Caught existing TaskExecutionError: {step_error}")

        # --- Handle Successful Execution (if not failed) ---
        if not step_failed:
            self.logger.debug(f"Processing successful result for step '{step_name}'.")
            output_value_for_context: Any = (
                None  # Value to potentially map to top-level
            )

            # Update context with step result under 'steps' namespace
            if isinstance(result, dict):
                self.context["steps"][step_name] = result
                # Use the 'result' key if present, otherwise the whole dict for potential mapping
                output_value_for_context = result.get("result", result)
            else:  # Handle non-dict results (e.g., strings from shell)
                self.context["steps"][step_name] = {"result": result}
                output_value_for_context = (
                    result  # Use the raw result for potential mapping
                )

            # *** Handle explicit 'outputs' mapping ***
            outputs_mapping = step.get("outputs")
            if isinstance(outputs_mapping, str):
                # If 'outputs' is a single string, map the determined value
                output_var_name = outputs_mapping
                self.context[output_var_name] = output_value_for_context
                # Also store in args namespace for compatibility/clarity? Maybe not needed.
                # self.context["args"][output_var_name] = output_value_for_context
                self.logger.debug(f"Mapped step output to context['{output_var_name}']")
            elif isinstance(outputs_mapping, dict):
                # If 'outputs' is a dict, map specified keys from the result *dict*
                if isinstance(result, dict):
                    for result_key, context_key in outputs_mapping.items():
                        if result_key in result:
                            self.context[context_key] = result[result_key]
                            self.logger.debug(
                                f"Mapped step output '{result_key}' to context['{context_key}']"
                            )
                        else:
                            self.logger.warning(
                                f"Output key '{result_key}' not found in result for step '{step_name}'"
                            )
                else:
                    # Cannot map dict keys from non-dict result
                    self.logger.warning(
                        f"Cannot apply 'outputs' mapping dict to non-dict result for step '{step_name}'"
                    )

            # Mark step as executed successfully in state
            self.state.mark_step_success(step_name, self.context["steps"][step_name])
            self.state.reset_step_retries(step_name)
            self.current_step = None
            self.logger.info(f"Step '{step_name}' executed successfully.")
            # Save state and exit method on success
            self.state.save()
            return

        # --- Handle Failure (if caught) ---
        # This block only runs if step_failed is True
        # We also assert step_error is a TaskExecutionError due to wrapping above
        assert isinstance(
            step_error, TaskExecutionError
        ), "Internal error: step_error should be TaskExecutionError here"

        self.logger.debug(f"Processing failure for step '{step_name}'.")
        # --- Retry and Error Flow Logic ---
        on_error_config = step.get("on_error", {})
        max_retries_for_step = on_error_config.get("retry", global_max_retries)
        retry_count = self.state.get_step_retry_count(step_name)

        error_to_propagate = step_error.original_error or step_error
        error_str_for_message = str(error_to_propagate)

        if retry_count < max_retries_for_step:
            # --- Handle Retry ---
            self.state.increment_step_retry(step_name)
            self.logger.info(
                f"Retrying step '{step_name}' (Attempt {retry_count + 1}/{max_retries_for_step})"
            )
            delay = float(on_error_config.get("delay", 0))
            if delay > 0:
                self.logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
            # Save state before raising retry exception
            self.state.save()
            raise RetryStepException(step_name, original_error=error_to_propagate)
        else:
            # --- Handle Final Failure (No More Retries) ---
            self.logger.error(f"Step '{step_name}' failed after {retry_count} retries.")
            error_info = {"step": step_name, "error": error_str_for_message}
            self.context["error"] = error_info
            self.context["error"]["raw_error"] = error_to_propagate

            error_message_template = on_error_config.get("message")
            final_error_message_for_state = str(
                step_error
            )  # Use TaskExecutionError message by default
            if error_message_template:
                try:
                    formatted_message = self.resolve_template(error_message_template)
                    self.logger.error(f"Formatted error message: {formatted_message}")
                    final_error_message_for_state = formatted_message
                except Exception as template_err:
                    self.logger.warning(
                        f"Failed to resolve on_error.message template: {template_err}"
                    )
                    final_error_message_for_state = (
                        f"{error_str_for_message} (failed to format custom message)"
                    )

            action = on_error_config.get("action", "fail")

            if action == "continue":
                self.logger.warning(
                    f"Step '{step_name}' failed, but workflow continues due to on_error.action='continue'"
                )
                self.state.mark_step_failed(step_name, final_error_message_for_state)
                self.state.clear_error_flow_target()
                # Save state and return, allowing run loop to continue
                self.state.save()
                return  # NOTE: Execution stops here for 'continue'

            error_next_step = on_error_config.get("next")
            if error_next_step:
                self.logger.info(
                    f"Proceeding to error handling step: {error_next_step}"
                )
                self.state.set_error_flow_target(error_next_step)
                # Save state before raising exception for jump
                self.state.save()
                raise TaskExecutionError(
                    step_name, original_error=error_to_propagate
                )  # Re-raise TaskExecutionError for jump
            else:
                self.logger.error(
                    f"No error handling ('on_error.next' or 'continue') defined for step '{step_name}'. Halting workflow."
                )
                self.state.mark_step_failed(step_name, final_error_message_for_state)
                # Save state before raising exception for halt
                self.state.save()
                raise TaskExecutionError(
                    step_name, original_error=error_to_propagate
                )  # Re-raise TaskExecutionError for halt

        # Note: The finally block is removed as state saving is handled explicitly
        # in success, continue, retry, jump, and halt paths.


# Custom exception for signaling retry
class RetryStepException(TaskExecutionError):
    """Indicates a step should be retried."""

    pass
