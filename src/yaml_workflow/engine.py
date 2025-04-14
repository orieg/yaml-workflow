"""
Core workflow engine implementation.
"""

import importlib
import inspect
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from jinja2 import Template

from .exceptions import (
    FlowError,
    FlowNotFoundError,
    FunctionNotFoundError,
    InvalidFlowDefinitionError,
    StepExecutionError,
    StepNotInFlowError,
    WorkflowError,
)
from .state import WorkflowState
from .tasks import get_task_handler
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
    ):
        """
        Initialize the workflow engine.

        Args:
            workflow: Path to workflow YAML file or workflow definition dictionary
            workspace: Optional custom workspace directory
            base_dir: Base directory for workflow runs

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
            with open(self.workflow_file) as f:
                self.workflow = yaml.safe_load(f)

        # Validate workflow structure
        if not isinstance(self.workflow, dict):
            raise WorkflowError("Invalid workflow format: root must be a mapping")

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

        # Initialize workflow state
        self.state = WorkflowState(self.workspace)

        # Initialize context with default parameter values
        self.context = {
            "workflow_name": self.name,
            "workspace": str(self.workspace),
            "run_number": self.workspace_info.get("run_number"),
            "timestamp": datetime.now().isoformat(),
        }

        # Add workflow file path if available
        if self.workflow_file:
            self.context["workflow_file"] = str(self.workflow_file.absolute())

        # Load default parameter values from workflow file
        params = self.workflow.get("params", {})
        for param_name, param_config in params.items():
            if isinstance(param_config, dict) and "default" in param_config:
                self.context[param_name] = param_config["default"]

        # Validate flows if present
        self._validate_flows()

        self.logger.info(f"Initialized workflow: {self.name}")
        self.logger.info(f"Workspace: {self.workspace}")
        self.logger.info(f"Run number: {self.context['run_number']}")
        if params:
            self.logger.info("Default parameters loaded:")
            for name, value in self.context.items():
                if name in params:
                    self.logger.info(f"  {name}: {value}")

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
            self.context.update(params)
            self.logger.info("Parameters provided:")
            for name, value in params.items():
                self.logger.info(f"  {name}: {value}")

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
            if self.state.metadata["execution_state"]["status"] != "failed":
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

                result = handler(step, self.context, self.workspace)
                self.logger.debug(
                    f"Task returned result of type {type(result)}: {result}"
                )
                results[name] = result
                # Update context with step result
                self.context[name] = result
                # Update workflow state
                self.state.mark_step_complete(name, {name: result})
            except Exception as e:
                self.state.mark_step_failed(name, str(e))
                raise WorkflowError(f"Error in step {name}: {str(e)}") from e

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

    def resolve_value(self, value: Any) -> Any:
        """
        Resolve a value, replacing any ${var} references with context values.

        Args:
            value: Value to resolve

        Returns:
            Any: Resolved value
        """
        if isinstance(value, str) and "${" in value:
            # Simple variable substitution
            for var_name, var_value in self.context.items():
                placeholder = "${" + var_name + "}"
                if placeholder in value:
                    value = value.replace(placeholder, str(var_value))
        return value

    def resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all inputs, replacing variables with their values from context.

        Args:
            inputs: Input dictionary

        Returns:
            Dict[str, Any]: Resolved inputs
        """
        resolved: Dict[str, Any] = {}
        for key, value in inputs.items():
            if isinstance(value, dict):
                resolved[key] = self.resolve_inputs(value)
            elif isinstance(value, list):
                resolved[key] = [self.resolve_value(v) for v in value]
            else:
                resolved[key] = self.resolve_value(value)
        return resolved

    def execute_step(self, step: Dict[str, Any]) -> None:
        """
        Execute a single workflow step.

        Args:
            step: Step definition from workflow
        """
        name = step.get("name", "unnamed_step")
        self.logger.info(f"Running step: {name}")

        # Import module
        try:
            module = importlib.import_module(step["module"])
        except ImportError as e:
            raise ModuleNotFoundError(name, step["module"]) from e

        # Get function
        try:
            func = getattr(module, step["function"])
        except AttributeError as e:
            raise FunctionNotFoundError(name, step["module"], step["function"]) from e

        # Prepare inputs
        inputs = self.resolve_inputs(step.get("inputs", {}))

        # Add workspace to inputs if function accepts it
        sig = inspect.signature(func)
        if "workspace" in sig.parameters and self.workspace:
            inputs["workspace"] = self.workspace

        self.logger.info(f"Step inputs: {inputs}")

        # Execute function
        try:
            result = func(**inputs)
            self.logger.debug(f"Task returned result of type {type(result)}: {result}")
        except Exception as e:
            raise StepExecutionError(name, e) from e

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
