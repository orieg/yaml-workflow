"""
Custom exceptions for the workflow engine.
These exceptions provide more specific error information for different types of workflow failures.
"""

class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""
    pass

class WorkflowDefinitionError(WorkflowError):
    """Raised when there are issues with the workflow definition YAML."""
    pass

class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails (missing required fields, invalid types, etc)."""
    pass

class WorkflowRuntimeError(WorkflowError):
    """Base class for runtime workflow errors."""
    pass

class ModuleImportError(WorkflowRuntimeError):
    """Raised when a module cannot be imported."""
    pass

class FunctionNotFoundError(WorkflowRuntimeError):
    """Raised when a specified function cannot be found in a module."""
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
        super().__init__(f"Failed to resolve input '{variable_name}' in step '{step_name}': {message}")

class OutputHandlingError(WorkflowRuntimeError):
    """Raised when there are issues handling task outputs."""
    def __init__(self, step_name: str, message: str):
        self.step_name = step_name
        super().__init__(f"Output handling failed for step '{step_name}': {message}")

class RequiredVariableError(WorkflowRuntimeError):
    """Raised when a required variable is missing from the context."""
    def __init__(self, variable_name: str, step_name: str = None):
        self.variable_name = variable_name
        self.step_name = step_name
        location = f" in step '{step_name}'" if step_name else ""
        super().__init__(f"Required variable '{variable_name}' not found{location}")

class WorkflowValidationSchema:
    """Schema definitions for workflow validation."""
    REQUIRED_STEP_FIELDS = ['name', 'module', 'function']
    OPTIONAL_STEP_FIELDS = ['inputs', 'outputs', 'condition', 'error_handling', 'retry', 'always_run']
    VALID_ERROR_HANDLING = ['skip', 'fail', 'retry', 'notify'] 