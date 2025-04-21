"""Tests for the newer, specific Python task implementations."""

import sys
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import TaskExecutionError, WorkflowError

# Import tasks to ensure registration
from yaml_workflow.tasks import python_tasks


@pytest.fixture
def test_module_file(tmp_path: Path):
    """Create a dummy module file for python_function tests."""
    module_content = """
import asyncio
import logging
# from yaml_workflow.tasks.config import TaskConfig # No longer needed

logger = logging.getLogger(__name__)

def my_func(a, b=2):
    return a * b

# Renamed and simplified: no longer takes TaskConfig
def func_with_offset(x, offset_val):
    logger.info(f"[func_with_offset] Received x={x}, offset_val={offset_val}")
    return x + offset_val

def func_raises_error(y):
    raise ValueError(\"Intentional function error\")
"""
    module_path = tmp_path / "test_module.py"
    module_path.write_text(module_content)
    # Add directory to sys.path so importlib can find it
    sys.path.insert(0, str(tmp_path))
    yield module_path
    sys.path.pop(0)  # Clean up sys.path


@pytest.fixture
def test_script_file(tmp_path: Path):
    """Create a dummy script file for python_script tests."""
    script_content = """
import sys
import os

print(f\"Script running in CWD: {os.getcwd()}\")
if len(sys.argv) > 1:
    print(f\"Arg: {sys.argv[1]}\")
    if sys.argv[1] == 'fail':
        print(\"Exiting with error\", file=sys.stderr)
        sys.exit(1)
    elif sys.argv[1] == 'absolute':
        print(\"Absolute path test successful\")
    sys.exit(0)
else:
    print(\"No args received\")
    sys.exit(0)
"""
    script_path = tmp_path / "test_script.py"
    script_path.write_text(script_content)
    script_path.chmod(0o755)  # Make executable
    return script_path


@pytest.fixture
def test_exec_module_file(tmp_path: Path):
    """Create a dummy executable module for python_module tests."""
    module_dir = tmp_path / "exec_module"
    module_dir.mkdir()
    main_content = """
import sys
print(\"Module executed\")
if len(sys.argv) > 1 and sys.argv[1] == 'fail':
    print(\"Module failing\", file=sys.stderr)
    sys.exit(5)
else:
    sys.exit(0)
"""
    (module_dir / "__main__.py").write_text(main_content)
    # Add parent directory to sys.path for python -m resolution
    sys.path.insert(0, str(tmp_path))
    yield "exec_module"
    sys.path.pop(0)


# === python_function Tests ===


def test_python_function_success(tmp_path: Path, test_module_file):
    workflow = {
        "steps": [
            {
                "name": "run_func",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "my_func",
                    "args": [5],
                    "kwargs": {"b": 3},
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    # Check the output of the run_func step
    assert "result" in status["outputs"]["run_func"]
    assert status["outputs"]["run_func"]["result"] == 15


def test_python_function_missing_function(tmp_path: Path, test_module_file):
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "non_existent_func",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "Function 'non_existent_func' not found" in str(e.value.original_error)


def test_python_function_missing_module(tmp_path: Path):
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "non_existent_module",
                    "function": "some_func",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "Module 'non_existent_module' not found" in str(e.value.original_error)


def test_python_function_bad_args(tmp_path: Path, test_module_file):
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "my_func",
                    "kwargs": {"c": 3},  # Wrong kwarg name
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    # Expect WorkflowError as the engine wraps TaskExecutionError on final halt
    with pytest.raises(WorkflowError) as e:
        engine.run()
    # Assert on the message within the WorkflowError (should contain original reason)
    assert "Error binding arguments for my_func" in str(e.value)
    assert "missing a required argument: 'a'" in str(e.value)


def test_python_function_internal_error(tmp_path: Path, test_module_file):
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "func_raises_error",
                    "args": [1],
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "Intentional function error" in str(e.value.original_error)


def test_python_function_with_taskconfig(tmp_path: Path, test_module_file):
    """Test passing context via explicit inputs."""
    workflow = {
        "params": {"offset": {"default": 5}},
        "steps": [
            {
                "name": "run_func_config",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "func_with_offset",
                    "args": [10],
                    "kwargs": {"offset_val": "{{ args.offset }}"},
                },
            }
        ],
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_func_config"]["result"] == 15


# === python_script Tests ===


def test_python_script_success(tmp_path: Path, test_script_file):
    workflow = {
        "steps": [
            {
                "name": "run_script",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "args": ["hello"],
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_script"]["result"]["returncode"] == 0
    assert "Arg: hello" in status["outputs"]["run_script"]["result"]["stdout"]


def test_python_script_not_found(tmp_path: Path):
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {"script_path": "non_existent_script.py"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "Script 'non_existent_script.py' not found" in str(e.value.original_error)


def test_python_script_absolute_path(tmp_path: Path, test_script_file):
    workflow = {
        "steps": [
            {
                "name": "run_script_abs",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.absolute()),  # Absolute path
                    "args": ["absolute"],
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_script_abs"]["result"]["returncode"] == 0
    assert (
        "Absolute path test successful"
        in status["outputs"]["run_script_abs"]["result"]["stdout"]
    )


def test_python_script_fail_no_check(tmp_path: Path, test_script_file):
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "args": ["fail"],
                    "check": False,  # Don't raise error on failure
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_script_fail"]["result"]["returncode"] == 1
    assert (
        "Exiting with error" in status["outputs"]["run_script_fail"]["result"]["stderr"]
    )


def test_python_script_fail_with_check(tmp_path: Path, test_script_file):
    workflow = {
        "steps": [
            {
                "name": "run_script_check",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "args": ["fail"],
                    "check": True,  # Default, should raise error
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "failed with exit code 1" in str(e.value.original_error)
    assert "Exiting with error" in str(e.value.original_error)


# === python_module Tests ===


def test_python_module_success(tmp_path: Path, test_exec_module_file):
    module_name = test_exec_module_file
    workflow = {
        "steps": [
            {
                "name": "run_module",
                "task": "python_module",
                "inputs": {"module": module_name},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_module"]["result"]["returncode"] == 0
    assert "Module executed" in status["outputs"]["run_module"]["result"]["stdout"]


def test_python_module_fail_check(tmp_path: Path, test_exec_module_file):
    module_name = test_exec_module_file
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {"module": module_name, "args": ["fail"]},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert f"Module '{module_name}' failed with exit code 5" in str(
        e.value.original_error
    )
    assert "Module failing" in str(e.value.original_error)


# === python_code Tests ===


def test_python_code_success(tmp_path: Path):
    workflow = {
        "steps": [
            {
                "name": "run_code",
                "task": "python_code",
                "inputs": {"code": "result = 10 * 5", "result_variable": "result"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    # Access the direct result value
    assert status["outputs"]["run_code"]["result"] == 50


def test_python_code_exec_error(tmp_path: Path):
    workflow = {
        "steps": [
            {
                "name": "run_code_fail",
                "task": "python_code",
                "inputs": {"code": "result = 1 / 0"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "division by zero" in str(e.value.original_error)


def test_python_code_result_var_error(tmp_path: Path):
    workflow = {
        "steps": [
            {
                "name": "run_code_fail",
                "task": "python_code",
                "inputs": {
                    "code": "x = 5",
                    "result_variable": "result",  # Variable 'result' is never assigned
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "Result variable 'result' not found" in str(e.value.original_error)


def test_python_code_no_result_var(tmp_path: Path):
    # Test that it returns None when result_variable is omitted
    # or when 'result' is not explicitly assigned.
    workflow = {
        "steps": [
            {
                "name": "run_code_no_res",
                "task": "python_code",
                "inputs": {"code": "x = 100"},  # No 'result' variable assigned
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    # Access the direct result value, which should be None
    assert status["outputs"]["run_code_no_res"]["result"] is None


# Assuming the test definition starts around line 500
# def test_python_function_too_many_pos_args_no_varargs(...):
#    ...
#    with pytest.raises(WorkflowError) as e:
#        engine.run()
#    # Change the type expected for the original error
#    assert isinstance(e.value.original_error, TaskExecutionError) # <<< Line 516 (approx)

# Corrected version:


def test_python_function_too_many_pos_args_no_varargs(tmp_path: Path, test_module_file):
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "my_func",
                    "args": [1, 2, 3],  # Too many positional arguments
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert isinstance(e.value.original_error, TypeError)


# === Tests for print_vars_task and print_message_task ===


def test_print_message_task(tmp_path: Path, capsys):
    workflow = {
        "params": {"user_name": "WorkflowUser"},
        "steps": [
            {
                "name": "print_greeting",
                "task": "print_message",
                "inputs": {"message": "Hello, {{ args.user_name }}!"},
            }
        ],
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    captured = capsys.readouterr()
    assert "Hello, WorkflowUser!" in captured.out
    assert status["outputs"]["print_greeting"]["result"]["success"] is True
    assert status["outputs"]["print_greeting"]["result"]["printed_length"] == len(
        "Hello, WorkflowUser!"
    )


def test_print_message_task_empty(tmp_path: Path, capsys):
    workflow = {
        "steps": [
            {
                "name": "print_empty",
                "task": "print_message",
                "inputs": {"message": ""},  # Empty message
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    captured = capsys.readouterr()
    assert captured.out == "\n"
    assert status["outputs"]["print_empty"]["result"]["success"] is True
    assert status["outputs"]["print_empty"]["result"]["printed_length"] == 0


def test_print_vars_task(tmp_path: Path, capsys):
    workflow = {
        "params": {"input_arg": "test_value"},
        "steps": [
            {
                "name": "setup_step",
                "task": "python_code",
                "inputs": {"code": "result = {'data': 123}"},
            },
            {
                "name": "print_context",
                "task": "print_vars",
                "inputs": {"message": "Debug Context"},
            },
        ],
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    captured = capsys.readouterr()
    assert "--- Debug Context ---" in captured.out
    assert "Workflow Variables:" in captured.out
    assert "args: {'input_arg': 'test_value'}" in captured.out
    assert "Step Results:" in captured.out
    # Check key components of the step result representation
    # More robust to formatting changes from pprint
    assert "'setup_step':" in captured.out
    assert "'result':" in captured.out
    assert "'data': 123" in captured.out
    assert status["outputs"]["print_context"]["result"]["success"] is True
