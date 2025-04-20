"""Tests for custom exceptions."""

import pytest

from yaml_workflow.exceptions import (
    FunctionNotFoundError,
    InputResolutionError,
    InputValidationError,
    InvalidFlowDefinitionError,
)
from yaml_workflow.exceptions import (
    ModuleNotFoundError as WorkflowModuleNotFoundError,  # Alias to avoid pytest conflict
)
from yaml_workflow.exceptions import (
    OutputHandlingError,
    OutputValidationError,
    RequiredVariableError,
    StepError,
    StepExecutionError,
    StepNotInFlowError,
    TaskExecutionError,
    TemplateError,
    VariableNotFoundError,
    WorkflowError,
    WorkflowTimeoutError,
)


def test_step_error():
    """Test StepError instantiation."""
    step_name = "test_step"
    message = "Something went wrong"
    err = StepError(step_name, message)
    assert err.step_name == step_name
    assert f"Error in step '{step_name}': {message}" == str(err)


def test_module_not_found_error():
    """Test ModuleNotFoundError instantiation."""
    step_name = "test_step"
    module_name = "nonexistent_module"
    err = WorkflowModuleNotFoundError(step_name, module_name)
    assert err.step_name == step_name
    assert f"Module '{module_name}' not found" in str(err)


def test_function_not_found_error():
    """Test FunctionNotFoundError instantiation."""
    step_name = "test_step"
    module_name = "some_module"
    func_name = "missing_func"
    err = FunctionNotFoundError(step_name, module_name, func_name)
    assert err.step_name == step_name
    assert f"Function '{func_name}' not found in module '{module_name}'" in str(err)


def test_input_validation_error():
    """Test InputValidationError instantiation."""
    step_name = "test_step"
    input_name = "bad_input"
    message = "must be integer"
    err = InputValidationError(step_name, input_name, message)
    assert err.step_name == step_name
    assert f"Invalid input '{input_name}': {message}" in str(err)


def test_output_validation_error():
    """Test OutputValidationError instantiation."""
    step_name = "test_step"
    output_name = "wrong_output"
    message = "format incorrect"
    err = OutputValidationError(step_name, output_name, message)
    assert err.step_name == step_name
    assert f"Invalid output '{output_name}': {message}" in str(err)


def test_variable_not_found_error():
    """Test VariableNotFoundError instantiation."""
    var_name = "missing_var"
    err = VariableNotFoundError(var_name)
    assert f"Variable '{var_name}' not found" in str(err)


def test_step_execution_error():
    """Test StepExecutionError instantiation."""
    step_name = "failing_step"
    original = ValueError("original issue")
    err = StepExecutionError(step_name, original)
    assert err.step_name == step_name
    assert err.original_error == original
    assert f"Execution failed: {str(original)}" in str(err)


def test_workflow_timeout_error():
    """Test WorkflowTimeoutError instantiation."""
    timeout = 60.5
    err = WorkflowTimeoutError(timeout)
    assert f"exceeded timeout of {timeout} seconds" in str(err)


def test_input_resolution_error():
    """Test InputResolutionError instantiation."""
    step_name = "resolve_step"
    var_name = "unresolved_input"
    message = "could not find value"
    err = InputResolutionError(step_name, var_name, message)
    assert err.step_name == step_name
    assert err.variable_name == var_name
    assert (
        f"Failed to resolve input '{var_name}' in step '{step_name}': {message}"
        == str(err)
    )


def test_output_handling_error():
    """Test OutputHandlingError instantiation."""
    step_name = "output_step"
    message = "cannot write output"
    err = OutputHandlingError(step_name, message)
    assert err.step_name == step_name
    assert f"Output handling failed for step '{step_name}': {message}" == str(err)


def test_required_variable_error_no_step():
    """Test RequiredVariableError instantiation without step context."""
    var_name = "global_required"
    err = RequiredVariableError(var_name)
    assert err.variable_name == var_name
    assert err.step_name is None
    assert f"Required variable '{var_name}' not found" == str(err)


def test_required_variable_error_with_step():
    """Test RequiredVariableError instantiation with step context."""
    var_name = "step_required"
    step_name = "needs_var_step"
    err = RequiredVariableError(var_name, step_name)
    assert err.variable_name == var_name
    assert err.step_name == step_name
    assert f"Required variable '{var_name}' not found in step '{step_name}'" == str(err)


def test_invalid_flow_definition_error():
    """Test InvalidFlowDefinitionError instantiation."""
    flow_name = "bad_flow"
    reason = "missing steps"
    err = InvalidFlowDefinitionError(flow_name, reason)
    assert err.flow_name == flow_name
    assert err.reason == reason
    assert f"Invalid flow '{flow_name}': {reason}" in str(err)


def test_step_not_in_flow_error():
    """Test StepNotInFlowError instantiation."""
    step_name = "orphan_step"
    flow_name = "main_flow"
    err = StepNotInFlowError(step_name, flow_name)
    assert err.step_name == step_name
    assert err.flow_name == flow_name
    assert f"Step '{step_name}' not found in flow '{flow_name}'" in str(err)


def test_template_error_no_original():
    """Test TemplateError without an original error."""
    message = "bad template syntax"
    err = TemplateError(message)
    assert err.original_error is None
    assert f"Template error: {message}" == str(err)


def test_template_error_with_original():
    """Test TemplateError wrapping an original error."""
    message = "resolution failed"
    original = KeyError("missing key")
    err = TemplateError(message, original)
    assert err.original_error == original
    assert f"Template error: {message}" == str(err)


def test_workflow_error_no_original():
    """Test base WorkflowError without original error."""
    message = "base workflow issue"
    err = WorkflowError(message)
    assert err.original_error is None
    assert message == str(err)


def test_workflow_error_with_original():
    """Test base WorkflowError wrapping an original error."""
    message = "wrapped issue"
    original = TypeError("bad type")
    err = WorkflowError(message, original)
    assert err.original_error == original
    assert message == str(err)


def test_task_execution_error():
    """Test TaskExecutionError instantiation."""
    step_name = "failing_task"
    original = RuntimeError("task runtime issue")
    task_config = {"input": "value"}
    err = TaskExecutionError(step_name, original, task_config)
    assert err.step_name == step_name
    assert err.original_error == original
    assert err.task_config == task_config
    assert f"Task '{step_name}' failed: {str(original)}" == str(err)
