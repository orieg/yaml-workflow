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
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from jinja2 import StrictUndefined, Template

from .exceptions import (
    FlowError,
    FlowNotFoundError,
    FunctionNotFoundError,
    InvalidFlowDefinitionError,
    StepExecutionError,
    StepNotInFlowError,
    TemplateError,
    WorkflowError,
)
from .state import WorkflowState
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
    ) -> Dict[str, Any]:
        """
        Run the workflow.

        Args:
            params: Optional parameters to pass to the workflow
            resume_from: Optional step name to resume from after failure (preserves outputs)
            start_from: Optional step name to start execution from (fresh start)
            skip_steps: Optional list of step names to skip during execution
            flow: Optional flow name to execute. If not specified, uses default flow.

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

        # Run steps
        results: Dict[str, Any] = {}
        for i, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                raise WorkflowError(f"Invalid step format at position {i}")

            # Get step info
            name = step.get("name", f"step_{i}")

            # Skip steps that are in the skip list
            if skip_steps and name in skip_steps:
                self.logger.info(f"Skipping step: {name} (explicitly skipped)")
                continue

            # Handle resume vs start from logic
            if resume_from:
                # Skip already completed steps when resuming
                if name in self.state.metadata["execution_state"]["completed_steps"]:
                    self.logger.info(f"Skipping completed step: {name}")
                    continue

                # Skip steps until we reach the resume point
                if (
                    name != resume_from
                    and not self.state.metadata["execution_state"]["completed_steps"]
                ):
                    self.logger.info(f"Skipping step before resume point: {name}")
                    continue
            elif start_from:
                # For start-from, simply skip until we reach the starting point
                if name != start_from and not results:
                    self.logger.info(f"Skipping step before start point: {name}")
                    continue

            # Check if step has a condition and evaluate it
            if "condition" in step:
                try:
                    template = Template(step["condition"])
                    condition_result = template.render(**self.context)
                    # Evaluate the rendered condition
                    if not eval(condition_result):
                        self.logger.info(f"Skipping step {name}: condition not met")
                        continue
                except Exception as e:
                    raise WorkflowError(
                        f"Error evaluating condition in step {name}: {str(e)}"
                    )

            task_type = step.get("task")
            if not task_type:
                raise WorkflowError(f"No task type specified for step: {name}")

            # Get task handler
            handler = get_task_handler(task_type)
            if not handler:
                raise WorkflowError(f"Unknown task type: {task_type}")

            # Run task
            self.logger.info(f"Running step {i}: {name}")
            try:
                # Call on_step_start callback if defined
                if hasattr(self, "on_step_start") and self.on_step_start:
                    try:
                        self.on_step_start(name)
                    except Exception as e:
                        self.state.mark_step_failed(name, str(e))
                        raise WorkflowError(f"Error in step {name}: {str(e)}") from e

                result = self._call_task_handler(handler, step)
                self.logger.debug(
                    f"Task returned result of type {type(result)}: {result}"
                )
                results[name] = result
                # Update context with step result
                self.context[name] = result
                # Update workflow state
                self.state.mark_step_complete(name, {name: result})
            except Exception as e:
                # Handle error according to on_error configuration
                result = self._handle_step_error(step, e)
                if result is None:
                    # Error handling indicated workflow should fail
                    raise WorkflowError(f"Error in step {name}: {str(e)}") from e
                # Error was handled, store result and continue
                results[name] = result
                self.context[name] = result

            # Store outputs in context
            outputs: Union[List[str], str, None] = step.get("outputs")
            if outputs is not None:
                self.logger.debug(
                    f"Storing outputs in context. Current context before: {self.context}"
                )
                self.logger.debug(f"Task result type: {type(result)}, value: {result}")
                if isinstance(outputs, str):
                    # Ensure we store raw strings for template variables
                    if isinstance(result, dict) and "content" in result:
                        self.logger.warning(
                            f"Task '{name}' returned a dict with 'content' property - using raw content value"
                        )
                        self.context[outputs] = result["content"]
                    else:
                        self.context[outputs] = result
                    self.logger.debug(
                        f"Stored single output '{outputs}' = {self.context[outputs]}"
                    )
                elif isinstance(outputs, list):
                    if len(outputs) == 1:
                        if isinstance(result, dict) and "content" in result:
                            self.logger.warning(
                                f"Task '{name}' returned a dict with 'content' property - using raw content value"
                            )
                            self.context[outputs[0]] = result["content"]
                        else:
                            self.context[outputs[0]] = result
                        self.logger.debug(
                            f"Stored single output from list '{outputs[0]}' = {self.context[outputs[0]]}"
                        )
                    elif len(outputs) > 1 and isinstance(result, (list, tuple)):
                        for output, value in zip(outputs, result):
                            if isinstance(value, dict) and "content" in value:
                                self.logger.warning(
                                    f"Task '{name}' returned a dict with 'content' property - using raw content value"
                                )
                                self.context[output] = value["content"]
                            else:
                                self.context[output] = value
                            self.logger.debug(
                                f"Stored multiple output '{output}' = {self.context[output]}"
                            )

            self.logger.debug(f"Final context after step '{name}': {self.context}")
            self.logger.info(f"Step '{name}' completed. Outputs: {self.context}")

        self.state.mark_workflow_completed()
        self.logger.info("Workflow completed successfully.")
        self.logger.info("Final workflow outputs:")
        for key, value in results.items():
            self.logger.info(f"  {key}: {value}")

        return {
            "status": "completed",
            "outputs": results,
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

    def _call_task_handler(self, handler: Any, step: Dict[str, Any]) -> Any:
        """
        Call a task handler with TaskConfig.

        Args:
            handler: The task handler function
            step: The step configuration

        Returns:
            Any: The result from the task handler
        """
        # Create TaskConfig and call handler
        config = TaskConfig(step, self.context, self.workspace)
        return handler(config)

    def execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a single workflow step."""
        name = step.get("name")
        if not name:
            raise WorkflowError("Step missing required 'name' field")

        self.current_step = name
        self.logger.info(f"Executing step: {name}")

        try:
            task_type = step.get("task")
            if not task_type:
                raise WorkflowError(f"No task type specified for step: {name}")

            # Get task handler
            handler = get_task_handler(task_type)
            if not handler:
                raise WorkflowError(f"Unknown task type: {task_type}")

            # Run task with appropriate signature
            self.logger.info(f"Running step {name}")
            try:
                # Call on_step_start callback if defined
                if hasattr(self, "on_step_start") and self.on_step_start:
                    try:
                        self.on_step_start(name)
                    except Exception as e:
                        self.state.mark_step_failed(name, str(e))
                        raise WorkflowError(f"Error in step {name}: {str(e)}") from e

                result = self._call_task_handler(handler, step)
                self.logger.debug(
                    f"Task returned result of type {type(result)}: {result}"
                )
                # Update context with step result
                self.context[name] = result
                # Update workflow state
                self.state.mark_step_complete(name, {name: result})
            except Exception as e:
                # Handle error according to on_error configuration
                result = self._handle_step_error(step, e)
                if result is None:
                    # Error handling indicated workflow should fail
                    raise WorkflowError(f"Error in step {name}: {str(e)}") from e
                # Error was handled, store result and continue
                self.context[name] = result

            # Store outputs in context
            outputs: Union[List[str], str, None] = step.get("outputs")
            if outputs is not None:
                self.logger.debug(
                    f"Storing outputs in context. Current context before: {self.context}"
                )
                self.logger.debug(f"Task result type: {type(result)}, value: {result}")
                if isinstance(outputs, str):
                    # Ensure we store raw strings for template variables
                    if isinstance(result, dict) and "content" in result:
                        self.logger.warning(
                            f"Task '{name}' returned a dict with 'content' property - using raw content value"
                        )
                        self.context[outputs] = result["content"]
                    else:
                        self.context[outputs] = result
                    self.logger.debug(
                        f"Stored single output '{outputs}' = {self.context[outputs]}"
                    )
                elif isinstance(outputs, list):
                    if len(outputs) == 1:
                        if isinstance(result, dict) and "content" in result:
                            self.logger.warning(
                                f"Task '{name}' returned a dict with 'content' property - using raw content value"
                            )
                            self.context[outputs[0]] = result["content"]
                        else:
                            self.context[outputs[0]] = result
                        self.logger.debug(
                            f"Stored single output from list '{outputs[0]}' = {self.context[outputs[0]]}"
                        )
                    elif len(outputs) > 1 and isinstance(result, (list, tuple)):
                        for output, value in zip(outputs, result):
                            if isinstance(value, dict) and "content" in value:
                                self.logger.warning(
                                    f"Task '{name}' returned a dict with 'content' property - using raw content value"
                                )
                                self.context[output] = value["content"]
                            else:
                                self.context[output] = value
                            self.logger.debug(
                                f"Stored multiple output '{output}' = {self.context[output]}"
                            )

            self.logger.debug(f"Final context after step '{name}': {self.context}")
            self.logger.info(f"Step '{name}' completed. Outputs: {self.context}")

            # Mark step as completed
            self.state.mark_step_complete(name, {name: result})

        except Exception as e:
            # Handle step error
            result = self._handle_step_error(step, e)
            if result is None:
                raise
        finally:
            self.current_step = None  # Clear current step

    def _handle_step_error(
        self, step: Dict[str, Any], error: Exception
    ) -> Optional[Any]:
        """Handle step execution error based on error handling configuration."""
        name = step.get("name", "unnamed_step")
        error_message = str(error)

        # Get error handling configuration
        error_config = step.get("on_error", {})
        action = error_config.get("action", "fail")
        next_step = error_config.get("next")

        # Add error info to context for template resolution
        self.context["error"] = error_message

        # Process custom error message if provided
        if "message" in error_config:
            try:
                error_message = self.resolve_template(error_config["message"])
            except Exception as e:
                self.logger.warning(f"Failed to resolve error message template: {e}")

        if action == "retry":
            # Get retry configuration
            max_attempts = int(error_config.get("max_attempts", 3))
            delay = float(error_config.get("delay", 1.0))
            backoff = float(error_config.get("backoff", 2.0))

            # Get current retry state
            retry_state = self.state.get_retry_state(name)
            attempt = retry_state.get("attempt", 0) + 1

            # Update retry state
            self.state.update_retry_state(name, {"attempt": attempt})

            if attempt >= max_attempts:
                # Max retries exceeded
                error_message = f"Failed after {attempt} attempts: {error_message}"
                self.state.mark_step_failed(name, error_message)
                self.state.clear_retry_state(name)
                return None

            # Calculate wait time with exponential backoff
            wait_time = delay * (backoff ** (attempt - 1))
            self.logger.info(
                f"Retrying step '{name}' in {wait_time} seconds (attempt {attempt}/{max_attempts})"
            )
            time.sleep(wait_time)

            # Try running the step again
            try:
                handler = get_task_handler(step["task"])
                if handler is None:
                    raise WorkflowError(f"Unknown task type: {step['task']}")
                result = self._call_task_handler(handler, step)
                # Clear retry state on success
                self.state.clear_retry_state(name)
                # Mark step as completed
                self.state.mark_step_complete(name, {name: result})
                return result
            except Exception as retry_error:
                # Get updated retry state to check attempt count
                retry_state = self.state.get_retry_state(name)
                attempt = retry_state.get("attempt", 0)

                if attempt >= max_attempts:
                    # If this was the last retry, mark as failed and clear retry state
                    error_message = (
                        f"Failed after {attempt} attempts: {str(retry_error)}"
                    )
                    self.state.mark_step_failed(name, error_message)
                    self.state.clear_retry_state(name)
                    raise WorkflowError(error_message)

                # Otherwise, handle retry failure recursively
                return self._handle_step_error(step, retry_error)
        elif action == "continue":
            # Mark as failed but continue workflow
            self.state.mark_step_failed(name, error_message)
            return {"error": error_message}
        elif action == "notify":
            # Mark as failed but try to execute notification task if specified
            self.state.mark_step_failed(name, error_message)
            if next_step:
                try:
                    notify_step = next(
                        s
                        for s in self.workflow.get("steps", [])
                        if s.get("name") == next_step
                    )
                    handler = get_task_handler(notify_step["task"])
                    if handler is None:
                        raise WorkflowError(f"Unknown task type: {notify_step['task']}")
                    # Add error info to context for notification
                    self.context["error"] = {
                        "step": name,
                        "message": error_message,
                        "error": str(error),
                    }
                    # Execute notification task but still fail the workflow
                    result = self._call_task_handler(handler, notify_step)
                    self.context[name] = result
                    self.state.mark_step_complete(name, {name: result})
                except Exception as notify_error:
                    self.logger.error(
                        f"Failed to execute notification task: {notify_error}"
                    )
            # Always raise WorkflowError after notification
            raise WorkflowError(error_message)
        elif action == "fail":
            # Mark as failed and raise error
            self.state.mark_step_failed(name, error_message)
            raise WorkflowError(error_message)
        else:
            self.logger.error(f"Unknown error action: {action}")
            self.state.mark_step_failed(name, error_message)
            raise WorkflowError(
                f"Unknown error action '{action}' for step {name}: {error_message}"
            )
