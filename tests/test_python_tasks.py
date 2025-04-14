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
    with pytest.raises(ValueError, match="Operation must be specified"):
        python_task(step, context, workspace)
