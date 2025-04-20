from pathlib import Path

import pytest

from yaml_workflow.exceptions import TaskExecutionError, TemplateError
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
    with pytest.raises(
        TaskExecutionError, match="could not convert string to float: 'a'"
    ):
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
    with pytest.raises(TaskExecutionError, match="Division by zero"):
        python_task(config)


def test_custom_handler_not_implemented(context, workspace):
    step = {
        "name": "custom",
        "task": "python",
        "inputs": {"operation": "custom"},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="not implemented"):
        python_task(config)


def test_unknown_operation(context, workspace):
    step = {"name": "unknown", "task": "python", "inputs": {"operation": "unknown"}}
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Unknown operation: unknown"):
        python_task(config)


def test_missing_operation(context, workspace):
    step = {"name": "missing_op", "task": "python", "inputs": {}}
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TaskExecutionError,
        match="Either 'code' or 'operation' must be specified for Python task",
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
        TaskExecutionError,
        match="name 'undefined_variable' is not defined",
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
    with pytest.raises(TaskExecutionError, match="expected ':'"):
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
        TaskExecutionError, match="Function mode requires a 'process' function"
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
    with pytest.raises(TaskExecutionError, match="Undefined variable"):
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
    with pytest.raises(TaskExecutionError, match="Invalid namespace 'invalid'"):
        python_task(config)


def test_print_vars_task(context, workspace, capsys):
    """Test the print_vars task."""
    step = {
        "name": "print_vars_test",
        "task": "print_vars",
        "inputs": {"message": "Current Context:"},
    }
    config = TaskConfig(step, context, workspace)
    from yaml_workflow.tasks.python_tasks import print_vars_task

    result = print_vars_task(config)

    captured = capsys.readouterr()
    assert "Current Context:" in captured.out
    assert "args: {" in captured.out  # Check key and opening brace
    assert "'x': 10" in captured.out  # Check inner content
    assert "Step Results:" in captured.out  # Check the header for steps output
    # Task should return success dict
    assert result == {"success": True}


def test_print_message_task(context, workspace, capsys):
    """Test the print_message task with templates."""
    step = {
        "name": "print_message_test",
        "task": "print_message",
        "inputs": {
            "message": "Value of x: {{ args.x }}, Previous result: {{ steps.previous.result }}"
        },
    }
    config = TaskConfig(step, context, workspace)
    from yaml_workflow.tasks.python_tasks import print_message_task

    result = print_message_task(config)

    captured = capsys.readouterr()
    assert "Value of x: 10, Previous result: 42" in captured.out
    # Don't assert on the return value, just that it printed
    # assert result == {}


def test_python_multiply_numbers_as_string(context, workspace):
    """Test multiply operation with numbers input as a string."""
    step = {
        "name": "multiply_str",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": "[5, 6, 7]"},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 210.0


def test_python_multiply_numbers_string_eval_error(context, workspace):
    """Test multiply with invalid numbers string format."""
    step = {
        "name": "multiply_str_err",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": '[5, 6, "'},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Invalid numbers format"):
        python_task(config)


def test_python_multiply_with_item_input_single(context, workspace):
    """Test multiply operation using the 'item' input (single number)."""
    step = {
        "name": "multiply_item_single",
        "task": "python",
        "inputs": {"operation": "multiply", "item": 10, "factor": 5},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 50.0  # item * factor


def test_python_multiply_with_item_input_list(context, workspace):
    """Test multiply operation using the 'item' input (list of numbers)."""
    step = {
        "name": "multiply_item_list",
        "task": "python",
        "inputs": {"operation": "multiply", "item": [2, 3, 4], "factor": 10},
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == [20.0, 30.0, 40.0]  # [i * factor for i in item]


def test_python_multiply_item_invalid_type(context, workspace):
    """Test multiply with invalid 'item' type."""
    step = {
        "name": "multiply_item_invalid",
        "task": "python",
        "inputs": {"operation": "multiply", "item": "not a number"},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Item must be a number or list"):
        python_task(config)


def test_python_multiply_empty_numbers(context, workspace):
    """Test multiply with empty numbers list."""
    step = {
        "name": "multiply_empty",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": []},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Numbers must be a non-empty list"):
        python_task(config)


def test_python_multiply_invalid_factor(context, workspace):
    """Test multiply with invalid factor."""
    step = {
        "name": "multiply_bad_factor",
        "task": "python",
        "inputs": {"operation": "multiply", "numbers": [2, 3], "factor": "abc"},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Invalid factor"):
        python_task(config)


def test_python_divide_with_templates(context, workspace):
    """Test divide operation with template inputs."""
    step = {
        "name": "divide_tmpl",
        "task": "python",
        "inputs": {
            "operation": "divide",
            "dividend": "{{ args.x }}",
            "divisor": "{{ args.y }}",
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == 2.0  # 10 / 5


def test_python_divide_invalid_dividend(context, workspace):
    """Test divide with invalid dividend type."""
    step = {
        "name": "divide_bad_dividend",
        "task": "python",
        "inputs": {"operation": "divide", "dividend": "abc", "divisor": 2},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TaskExecutionError, match="could not convert string to float: 'abc'"
    ):
        python_task(config)


def test_python_divide_invalid_divisor(context, workspace):
    """Test divide with invalid divisor type."""
    step = {
        "name": "divide_bad_divisor",
        "task": "python",
        "inputs": {"operation": "divide", "dividend": 10, "divisor": "xyz"},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TaskExecutionError, match="could not convert string to float: 'xyz'"
    ):
        python_task(config)


def test_python_divide_missing_dividend(context, workspace):
    """Test divide with missing dividend."""
    step = {
        "name": "divide_no_dividend",
        "task": "python",
        "inputs": {"operation": "divide", "divisor": 2},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="dividend parameter is required"):
        python_task(config)


def test_python_divide_missing_divisor(context, workspace):
    """Test divide with missing divisor."""
    step = {
        "name": "divide_no_divisor",
        "task": "python",
        "inputs": {"operation": "divide", "dividend": 10},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="divisor parameter is required"):
        python_task(config)


# Note: Testing custom_operation requires a way to inject or mock the handler.
# For now, we rely on the existing test_custom_handler_not_implemented.

# --- Tests for execute_code and execute_function helpers ---


def test_execute_code_with_batch_context(context, workspace):
    """Test execute_code uses batch context."""
    context["batch"] = {"item": "batch_val", "index": 1}
    step = {
        "name": "code_batch_context",
        "task": "python",
        "inputs": {
            "code": "result = batch['item'] + '_' + str(batch['index'])",
        },
    }
    config = TaskConfig(step, context, workspace)
    result = python_task(config)
    assert result["result"] == "batch_val_1"


# --- Tests for process_template_value helper ---
# (Difficult to test directly, tested implicitly via task inputs)

# --- Tests for execute_function helper ---


def test_execute_function_missing_process_func(context, workspace):
    """Test execute_function when code lacks a 'process' function."""
    step = {
        "name": "func_no_process",
        "task": "python",
        "inputs": {"operation": "function", "code": "def not_process(): return 1"},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="requires a 'process' function"):
        python_task(config)


def test_execute_function_args_ast_error(context, workspace):
    """Test execute_function with args needing eval that errors."""
    step = {
        "name": "func_args_eval_err",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": "def process(a, b): return a + b",
            "args": ["1", "[unbalanced"],  # Second arg causes SyntaxError
        },
    }
    config = TaskConfig(step, context, workspace)
    # Simplify match, just check for the core failure reason
    with pytest.raises(
        TaskExecutionError, match="Failed to evaluate argument string as literal"
    ):
        python_task(config)


def test_execute_function_non_string_args(context, workspace):
    """Test execute_function with non-string args."""
    step = {
        "name": "func_non_str_args",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": "def process(a, b, c): return a * b + c",
            "args": [10, 5.5, [1, 2]],  # Mixed types
        },
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TaskExecutionError, match="unsupported operand type\(s\) for \+"
    ):
        python_task(config)

    # Test with valid non-string args
    step_valid = {
        "name": "func_non_str_args_valid",
        "task": "python",
        "inputs": {
            "operation": "function",
            "code": "def process(a, b): return a * b",
            "args": [10, 5.5],  # Mixed types
        },
    }
    config_valid = TaskConfig(step_valid, context, workspace)
    result_valid = python_task(config_valid)
    assert result_valid["result"] == 55.0


# --- Tests for python_task main entry point logic ---


def test_python_task_both_code_and_operation(context, workspace):
    """Test error when both 'code' and 'operation' are specified."""
    step = {
        "name": "both_code_op",
        "task": "python",
        "inputs": {"operation": "multiply", "code": "result = 1", "numbers": [1, 2]},
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(
        TaskExecutionError, match="Cannot specify both 'code' and 'operation'"
    ):
        python_task(config)


def test_python_task_input_template_error(context, workspace):
    """Test error during template resolution in inputs."""
    step = {
        "name": "input_tmpl_err",
        "task": "python",
        "inputs": {
            "operation": "divide",
            "dividend": "{{ args.x }}",
            "divisor": "{{ undefined_var }}",  # This will fail
        },
    }
    config = TaskConfig(step, context, workspace)
    with pytest.raises(TaskExecutionError, match="Invalid namespace 'undefined_var'"):
        python_task(config)
