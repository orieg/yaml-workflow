from pathlib import Path

import pytest

from yaml_workflow.exceptions import TemplateError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.python_tasks import python_task


@pytest.fixture
def context():
    """Create a basic context with namespaces."""
    return {
        "args": {"x": 10, "y": 5, "numbers": [2, 3, 4], "debug": True},
        "env": {"multiplier": 2, "factor": 3},
        "steps": {"previous": {"result": 42}},
    }


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def test_multiply_numbers(context, workspace):
    step = {
        "name": "multiply",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": [2, 3, 4]},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 24.0


def test_multiply_invalid_input(context, workspace):
    step = {
        "name": "multiply_invalid",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": ["a", "b"]},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError, match="could not convert string to float"):
        python_task(config)


def test_divide_numbers(context, workspace):
    step = {
        "name": "divide",
        "task": "python",
        "inputs": {"operation": "divide", "dividend": 10, "divisor": 2},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 5.0


def test_divide_by_zero(context, workspace):
    step = {
        "name": "divide_zero",
        "task": "python",
        "inputs": {"operation": "divide", "dividend": 10, "divisor": 0},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError, match="Division by zero"):
        python_task(config)


def test_custom_handler(context, workspace):
    def custom_func(x):
        return x * 2

    step = {
        "name": "custom",
        "task": "python",
        "inputs": {"operation": "custom", "handler": custom_func, "args": [5]},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 10


def test_custom_handler_invalid(context, workspace):
    step = {
        "name": "custom_invalid",
        "task": "python",
        "inputs": {"operation": "custom", "handler": None},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError, match="Custom handler must be a callable"):
        python_task(config)


def test_unknown_operation(context, workspace):
    step = {"name": "unknown", "task": "python", "inputs": {"operation": "unknown"}}
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError, match="Unknown operation: unknown"):
        python_task(config)


def test_missing_operation(context, workspace):
    step = {"name": "missing_op", "task": "python", "inputs": {}}
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TemplateError,
        match="Either code or operation must be specified for Python task",
    ):
        python_task(config)


def test_python_code_execution(context, workspace):
    step = {
        "name": "code_exec",
        "task": "python",
        "inputs": {
            "code": """
# Calculate sum of squares
numbers = [1, 2, 3, 4, 5]
result = sum(x * x for x in numbers)
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 55


def test_python_code_with_inputs(context, workspace):
    step = {
        "name": "code_inputs",
        "task": "python",
        "inputs": {
            "code": """
# Use input variables
x = input_x
y = input_y
result = x + y
""",
            "input_x": 10,
            "input_y": 20,
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 30


def test_python_code_with_context(context, workspace):
    step = {
        "name": "code_context",
        "task": "python",
        "inputs": {
            "code": """
# Use context variables
result = context["args"]["x"] * context["env"]["multiplier"]
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 20  # 10 * 2


def test_python_code_execution_error(context, workspace):
    step = {
        "name": "code_error",
        "task": "python",
        "inputs": {
            "code": """
# This will raise a NameError
result = undefined_variable
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TemplateError,
        match="Failed to execute Python code: name 'undefined_variable' is not defined",
    ):
        python_task(config)


def test_python_code_syntax_error(context, workspace):
    step = {
        "name": "syntax_error",
        "task": "python",
        "inputs": {
            "code": """
# This has invalid syntax
if True
    result = 42
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TemplateError, match="Failed to execute Python code: expected ':'"
    ):
        python_task(config)


def test_python_multiply_with_params(context, workspace):
    step = {
        "name": "multiply_params",
        "task": "python",
        "inputs": {
            "operation": "multiply",
            "numbers": "{{ args.numbers }}",
            "factor": "{{ env.factor }}",
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 72.0  # (2 * 3 * 4) * 3


def test_python_task_result_in_next_task(context, workspace):
    # First task
    step1 = {
        "name": "task1",
        "task": "python",
        "inputs": {"code": "result = context['steps']['previous']['result']"},
    }
    config1 = TaskConfig(step1, context, workspace)
    result1 = python_task(config1)
    assert result1["result"] == 42

    # Update context with first task's result
    context["steps"]["task1"] = {"result": result1["result"]}

    # Second task using first task's result
    step2 = {
        "name": "task2",
        "task": "python",
        "inputs": {"code": "result = context['steps']['task1']['result'] * 2"},
    }
    config2 = TaskConfig(step2, context, workspace)
    result2 = python_task(config2)
    assert result2["result"] == 84


def test_python_task_no_result_variable(context, workspace):
    step = {
        "name": "no_result",
        "task": "python",
        "inputs": {"code": "x = 42  # No result variable set"},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] is None


def test_python_task_multiple_results(context, workspace):
    step = {
        "name": "multiple_results",
        "task": "python",
        "inputs": {
            "code": """
x = 1
y = 2
result = [x, y]
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == [1, 2]


def test_python_task_no_result_no_expression(context, workspace):
    step = {
        "name": "no_result_no_expr",
        "task": "python",
        "inputs": {"code": "# Just a comment"},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] is None


def test_python_task_conditional_result(context, workspace):
    step = {
        "name": "conditional_result",
        "task": "python",
        "inputs": {
            "code": """
x = context["args"]["x"]
if x > 5:
    result = 'big'
else:
    result = 'small'
"""
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == "big"


def test_python_task_function_mode(context, workspace):
    """Test Python task in function mode with template variables."""
    step = {
        "name": "function_mode",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def process(x, y, multiplier):
    return (x + y) * multiplier
""",
            "args": ["{{ args.x }}", "{{ args.y }}", "{{ env.multiplier }}"],
        },
    }

    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 30  # (10 + 5) * 2


def test_python_task_function_mode_with_defaults(context, workspace):
    """Test function mode with default arguments."""
    step = {
        "name": "function_defaults",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def process(x, y=5, multiplier=2):
    return (x + y) * multiplier
""",
            "args": [10],  # Only provide first argument
        },
    }

    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 30  # (10 + 5) * 2


def test_python_task_function_mode_invalid_signature(context, workspace):
    """Test error handling for invalid function signature."""
    step = {
        "name": "invalid_function",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def wrong_name(x, y):  # Function must be named 'process'
    return x + y
""",
            "args": [1, 2],
        },
    }

    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TemplateError, match="Function mode requires a 'process' function"
    ):
        python_task(config)


def test_python_task_function_mode_with_kwargs(context, workspace):
    """Test function mode with keyword arguments."""
    step = {
        "name": "function_kwargs",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def process(x, y, *, multiplier=1):
    return (x + y) * multiplier
""",
            "args": [2, 3],
            "kwargs": {"multiplier": 4},
        },
    }

    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 20  # (2 + 3) * 4


def test_python_task_function_mode_template_error(context, workspace):
    """Test error handling for undefined template variables in function mode."""
    step = {
        "name": "function_template_error",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def process(x):
    return x * 2
""",
            "args": ["{{ args.missing }}"],
        },
    }

    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError):
        python_task(config)


def test_python_task_function_mode_complex_types(context, workspace):
    """Test function mode with complex argument types."""
    context["args"]["data"] = {"numbers": [1, 2, 3], "factor": 2}

    step = {
        "name": "function_complex",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": """
def process(data):
    return sum(x * data['factor'] for x in data['numbers'])
""",
            "args": ["{{ args.data }}"],
        },
    }

    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 12  # (1 + 2 + 3) * 2


def test_python_task_template_resolution(context, workspace):
    """Test template resolution in Python task inputs."""
    step = {
        "name": "template_test",
        "task": "python",
        "inputs": {
            "operation": "multiply",
            "numbers": "{{ args.numbers }}",
            "factor": "{{ env.multiplier }}",
        },
    }

    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 48.0  # (2 * 3 * 4) * 2


def test_python_task_namespace_error_handling(context, workspace):
    """Test error handling for invalid namespace access."""
    step = {
        "name": "namespace_error",
        "task": "python",
        "inputs": {
            "operation": "multiply",
            "numbers": "{{ invalid.numbers }}",
            "factor": 2,
        },
    }

    config = TaskConfig(step, context, workspace)
    with pytest.raises(TemplateError) as exc_info:
        python_task(config)
    assert "invalid" in str(exc_info.value)
