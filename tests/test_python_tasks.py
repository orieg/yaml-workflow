from pathlib import Path

import pytest

from yaml_workflow.tasks.python_tasks import python_task


@pytest.fixture
def context():
    return {}


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def test_multiply_numbers(context, workspace):
    step = {
        "name": "multiply",
        "inputs": {"operation": "multiply", "numbers": [2, 3, 4]},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 24


def test_multiply_invalid_input(context, workspace):
    step = {
        "name": "multiply_invalid",
        "inputs": {"operation": "multiply", "numbers": []},
    }
    with pytest.raises(ValueError, match="Numbers must be a non-empty list"):
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
    with pytest.raises(ValueError, match="Division by zero"):
        python_task(step, context, workspace)


def test_custom_handler(context, workspace):
    def custom_func(x, y=1):
        return x + y

    step = {
        "name": "custom",
        "inputs": {
            "operation": "custom",
            "handler": custom_func,
            "args": [5],
            "kwargs": {"y": 3},
        },
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 8


def test_custom_handler_invalid(context, workspace):
    step = {
        "name": "custom_invalid",
        "inputs": {"operation": "custom", "handler": None},
    }
    with pytest.raises(ValueError, match="Custom handler must be a callable"):
        python_task(step, context, workspace)


def test_unknown_operation(context, workspace):
    step = {"name": "unknown", "inputs": {"operation": "unknown"}}
    with pytest.raises(ValueError, match="Unknown operation: unknown"):
        python_task(step, context, workspace)


def test_missing_operation(context, workspace):
    step = {"name": "missing_op", "inputs": {}}
    with pytest.raises(
        ValueError, match="Either code or operation must be specified for Python task"
    ):
        python_task(step, context, workspace)


def test_python_code_execution(context, workspace):
    step = {
        "name": "code_exec",
        "code": """
x = 5
y = 3
result = x * y
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 15


def test_python_code_with_inputs(context, workspace):
    step = {
        "name": "code_with_inputs",
        "code": """
x = x if 'x' in locals() else 0
y = y if 'y' in locals() else 0
result = x + y
""",
        "inputs": {"x": 10, "y": 20},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 30


def test_python_code_with_context(context, workspace):
    context["data"] = {"value": 42}
    step = {
        "name": "code_with_context",
        "code": """
value = context['data']['value']
result = value * 2
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
        ValueError,
        match="Code execution failed: name 'undefined_variable' is not defined",
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
    with pytest.raises(ValueError, match="Code execution failed: expected ':'"):
        python_task(step, context, workspace)


def test_python_multiply_with_params(context, workspace):
    # Set up parameters in context
    context["params"] = {"value_x": "5.5", "value_y": "2.0"}

    step = {
        "name": "calculate",
        "task": "python",
        "code": """
x = float(x)
y = float(y)
result = x * y  # Use result assignment instead of return
""",
        "inputs": {
            "x": context["params"]["value_x"],  # Direct value instead of template
            "y": context["params"]["value_y"],  # Direct value instead of template
        },
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 11.0  # 5.5 * 2.0 = 11.0


def test_python_task_result_in_next_task(context, workspace):
    # First task: Calculate area of a circle
    step1 = {
        "name": "calculate_area",
        "task": "python",
        "code": """
import math
radius = float(radius)
result = math.pi * radius * radius  # Calculate circle area
""",
        "inputs": {"radius": "5.0"},
    }
    result1 = python_task(step1, context, workspace)
    assert result1["result"] == pytest.approx(78.53981633974483)  # pi * 5^2

    # Add the result to context as the workflow engine would
    context["execution_state"] = {"step_outputs": {"calculate_area": result1}}

    # Second task: Use the area to calculate cost (area * cost_per_unit)
    step2 = {
        "name": "calculate_cost",
        "task": "python",
        "code": """
area = context['execution_state']['step_outputs']['calculate_area']['result']
cost_per_unit = float(cost_per_unit)
result = area * cost_per_unit  # Calculate total cost
""",
        "inputs": {"cost_per_unit": "10.0"},
    }
    result2 = python_task(step2, context, workspace)
    assert result2["result"] == pytest.approx(785.3981633974483)  # area * 10


def test_python_task_no_result_variable(context, workspace):
    # Code that doesn't set result variable
    step = {
        "name": "no_result",
        "task": "python",
        "code": """
x = 5
y = 3
z = x * y  # No result assignment
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    # Should try to use last expression
    assert result["result"] == 15  # z = 5 * 3


def test_python_task_multiple_results(context, workspace):
    # Code that sets result multiple times
    step = {
        "name": "multiple_results",
        "task": "python",
        "code": """
result = 5
result = 10
result = 15  # Final value should be stored
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 15


def test_python_task_no_result_no_expression(context, workspace):
    # Code that neither sets result nor has a usable last expression
    step = {
        "name": "no_result_no_expr",
        "task": "python",
        "code": """
# Only comments and empty lines
x = 5  # Assignment isn't considered a result
y = 3  # Another assignment
# Final line is a comment
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] is None  # Should be None when no result is available


def test_python_task_conditional_result(context, workspace):
    # Code that sets result conditionally
    step = {
        "name": "conditional_result",
        "task": "python",
        "code": """
x = 5
y = 3
if x > y:
    result = x * y  # Result set in conditional
""",
        "inputs": {},
    }
    result = python_task(step, context, workspace)
    assert result["result"] == 15  # Condition was true, so result was set
