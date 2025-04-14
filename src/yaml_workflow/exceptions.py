"""
Custom exceptions for the YAML Workflow Engine.
"""

from typing import Optional


class WorkflowError(Exception):
    """Base exception class for all workflow-related errors."""

    pass


class WorkflowValidationError(WorkflowError):
    """Raised when workflow YAML validation fails."""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow file cannot be found."""

    pass


class StepError(WorkflowError):
    """Base exception class for step-related errors."""

    def __init__(self, step_name: str, message: str):
        self.step_name = step_name
        super().__init__(f"Error in step '{step_name}': {message}")


class ModuleNotFoundError(StepError):
    """Raised when a module specified in a step cannot be found."""

    def __init__(self, step_name: str, module_name: str):
        super().__init__(step_name, f"Module '{module_name}' not found")


class FunctionNotFoundError(StepError):
    """Raised when a function specified in a step cannot be found in the module."""

    def __init__(self, step_name: str, module_name: str, function_name: str):
        super().__init__(
            step_name, f"Function '{function_name}' not found in module '{module_name}'"
        )


class InputValidationError(StepError):
    """Raised when step input validation fails."""

    def __init__(self, step_name: str, input_name: str, message: str):
        super().__init__(step_name, f"Invalid input '{input_name}': {message}")


class OutputValidationError(StepError):
    """Raised when step output validation fails."""

    def __init__(self, step_name: str, output_name: str, message: str):
        super().__init__(step_name, f"Invalid output '{output_name}': {message}")


class VariableNotFoundError(WorkflowError):
    """Raised when a referenced variable is not found in the workflow context."""

    def __init__(self, variable_name: str):
        super().__init__(f"Variable '{variable_name}' not found in workflow context")


class StepExecutionError(StepError):
    """Raised when a step fails during execution."""

    def __init__(self, step_name: str, original_error: Exception):
        super().__init__(step_name, f"Execution failed: {str(original_error)}")
        self.original_error = original_error


class WorkflowTimeoutError(WorkflowError):
    """Raised when a workflow exceeds its timeout limit."""

    def __init__(self, timeout_seconds: float):
        super().__init__(
            f"Workflow execution exceeded timeout of {timeout_seconds} seconds"
        )


class WorkflowDefinitionError(WorkflowError):
    """Raised when there are issues with the workflow definition YAML."""

    pass


class WorkflowRuntimeError(WorkflowError):
    """Base class for runtime workflow errors."""

    pass


class ModuleImportError(WorkflowRuntimeError):
    """Raised when a module cannot be imported."""

    pass


class TaskExecutionError(WorkflowRuntimeError):
    """Raised when a task fails during execution."""

    def __init__(self, step_name: str, original_error: Exception):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Task '{step_name}' failed: {str(original_error)}")


class InputResolutionError(WorkflowRuntimeError):
    """Raised when input variables cannot be resolved."""

    def __init__(self, step_name: str, variable_name: str, message: str):
        self.step_name = step_name
        self.variable_name = variable_name
        super().__init__(
            f"Failed to resolve input '{variable_name}' in step '{step_name}': {message}"
        )


class OutputHandlingError(WorkflowRuntimeError):
    """Raised when there are issues handling task outputs."""

    def __init__(self, step_name: str, message: str):
        self.step_name = step_name
        super().__init__(f"Output handling failed for step '{step_name}': {message}")


class RequiredVariableError(WorkflowRuntimeError):
    """Raised when a required variable is missing from the context."""

    def __init__(self, variable_name: str, step_name: Optional[str] = None):
        self.variable_name = variable_name
        self.step_name = step_name
        location = f" in step '{step_name}'" if step_name else ""
        super().__init__(f"Required variable '{variable_name}' not found{location}")


class WorkflowValidationSchema:
    """Schema definitions for workflow validation."""

    REQUIRED_STEP_FIELDS = ["name", "module", "function"]
    OPTIONAL_STEP_FIELDS = [
        "inputs",
        "outputs",
        "condition",
        "error_handling",
        "retry",
        "always_run",
    ]
    VALID_ERROR_HANDLING = ["skip", "fail", "retry", "notify"]


class FlowError(WorkflowError):
    """Base exception class for flow-related errors."""

    def __init__(self, message: str):
        super().__init__(f"Flow error: {message}")


class FlowNotFoundError(FlowError):
    """Raised when a specified flow is not found."""

    def __init__(self, flow_name: str):
        super().__init__(f"Flow '{flow_name}' not found")
        self.flow_name = flow_name


class InvalidFlowDefinitionError(FlowError):
    """Raised when a flow definition is invalid."""

    def __init__(self, flow_name: str, reason: str):
        super().__init__(f"Invalid flow '{flow_name}': {reason}")
        self.flow_name = flow_name
        self.reason = reason


class StepNotInFlowError(FlowError):
    """Raised when trying to access a step that is not in the current flow."""

    def __init__(self, step_name: str, flow_name: str):
        super().__init__(f"Step '{step_name}' not found in flow '{flow_name}'")
        self.step_name = step_name
        self.flow_name = flow_name
