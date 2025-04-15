from pathlib import Path

import pytest

from yaml_workflow.tasks.python_tasks import python_task
from yaml_workflow.exceptions import TemplateError


@pytest.fixture
def context():
    return {}


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def test_multiply_numbers(context, workspace):
    step = {"name": "multiply", "inputs": {"operation": "multiply", "numbers": [2, 3, 4]}}
    result = python_task(step, context, workspace)
    assert result["result"] == 24.0


def test_multiply_invalid_input(context, workspace):
    step = {
        "name": "multiply_invalid",
        "inputs": {"operation": "multiply", "numbers": ["a", "b"]},
    }
    with pytest.raises(TemplateError, match="could not convert string to float"):
        python_task(step, context, workspace)


def test_divide_numbers(context, workspace):
    step = {
        "name": "divide",
        "inputs": {"operation": "divide", "dividend": 10, "divisor": 2},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 5.0


def test_divide_by_zero(context, workspace):
    step = {
        "name": "divide_zero",
        "inputs": {"operation": "divide", "dividend": 10, "divisor": 0},
    }
    with pytest.raises(TemplateError, match="Division by zero"):
        python_task(step, context, workspace)


def test_custom_handler(context, workspace):
    def custom_func(x):
        return x * 2

    step = {
        "name": "custom",
        "inputs": {"operation": "custom", "handler": custom_func, "args": [5]},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 10


def test_custom_handler_invalid(context, workspace):
    step = {"name": "custom_invalid", "inputs": {"operation": "custom", "handler": None}}
    with pytest.raises(TemplateError, match="Custom handler must be a callable"):
        python_task(step, context, workspace)


def test_unknown_operation(context, workspace):
    step = {"name": "unknown", "inputs": {"operation": "unknown"}}
    with pytest.raises(TemplateError, match="Unknown operation: unknown"):
        python_task(step, context, workspace)


def test_missing_operation(context, workspace):
    step = {"name": "missing_op", "inputs": {}}
    with pytest.raises(
        TemplateError, match="Either code or operation must be specified for Python task"
    ):
        python_task(step, context, workspace)


def test_python_code_execution(context, workspace):
    step = {
        "name": "code_exec",
        "code": """
# Calculate sum of squares
numbers = [1, 2, 3, 4, 5]
result = sum(x * x for x in numbers)
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 55


def test_python_code_with_inputs(context, workspace):
    step = {
        "name": "code_inputs",
        "code": """
# Use input variables
x = input_x
y = input_y
result = x + y
""",
        "inputs": {"input_x": 10, "input_y": 20},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 30


def test_python_code_with_context(context, workspace):
    context["value"] = 42
    step = {
        "name": "code_context",
        "code": """
# Use context variables
result = context["value"] * 2
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 84


def test_python_code_execution_error(context, workspace):
    step = {
        "name": "code_error",
        "code": """
# This will raise a NameError
result = undefined_variable
""",
        "inputs": {},
    }
    with pytest.raises(
        TemplateError,
        match="Failed to execute Python code: name 'undefined_variable' is not defined",
    ):
        python_task(step, context, workspace)


def test_python_code_syntax_error(context, workspace):
    step = {
        "name": "syntax_error",
        "code": """
# This has invalid syntax
if True
    result = 42
""",
        "inputs": {},
    }
    with pytest.raises(TemplateError, match="Failed to execute Python code: expected ':'"):
        python_task(step, context, workspace)


def test_python_multiply_with_params(context, workspace):
    step = {
        "name": "multiply_params",
        "inputs": {"operation": "multiply", "numbers": [2, 3], "factor": 2},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 12.0


def test_python_task_result_in_next_task(context, workspace):
    # First task
    step1 = {
        "name": "task1",
        "code": "result = 42",
        "inputs": {},
    }
    result1 = python_task(step1, context, workspace)
    assert result1["result"] == 42

    # Store result in context
    context["steps"] = {"task1": {"result": result1["result"]}}

    # Second task using first task's result
    step2 = {
        "name": "task2",
        "code": "result = context['steps']['task1']['result'] * 2",
        "inputs": {},
    }
    result2 = python_task(step2, context, workspace)
    assert result2["result"] == 84


def test_python_task_no_result_variable(context, workspace):
    step = {
        "name": "no_result",
        "code": "x = 42  # No result variable set",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] is None


def test_python_task_multiple_results(context, workspace):
    step = {
        "name": "multiple_results",
        "code": """
x = 1
y = 2
result = [x, y]
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == [1, 2]


def test_python_task_no_result_no_expression(context, workspace):
    step = {
        "name": "no_result_no_expr",
        "code": "# Just a comment",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] is None


def test_python_task_conditional_result(context, workspace):
    step = {
        "name": "conditional_result",
        "code": """
x = 10
if x > 5:
    result = 'big'
else:
    result = 'small'
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == "big"
