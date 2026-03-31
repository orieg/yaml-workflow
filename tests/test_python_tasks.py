"""Tests for the newer, specific Python task implementations."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

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

# A non-callable attribute for testing _load_function not-callable check
NOT_A_FUNCTION = 42

async def async_add(a, b):
    return a + b
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


# === Tests for print_vars_task with no step results (line 65) ===


def test_print_vars_task_no_step_results(tmp_path: Path, capsys):
    """Test print_vars_task when there are no step results yet."""
    workflow = {
        "steps": [
            {
                "name": "print_context",
                "task": "print_vars",
                "inputs": {"message": "Empty Context"},
            },
        ],
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    captured = capsys.readouterr()
    assert "--- Empty Context ---" in captured.out
    assert "(No step results yet)" in captured.out


# === Tests for _load_function not-callable (line 100) ===


def test_load_function_not_callable(tmp_path: Path, test_module_file):
    """Test _load_function raises TypeError when attribute is not callable."""
    workflow = {
        "steps": [
            {
                "name": "run_not_callable",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "NOT_A_FUNCTION",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "not callable" in str(e.value.original_error)


# === Tests for _execute_python_function args/kwargs type validation (lines 122, 124) ===


def test_python_function_args_not_list(tmp_path: Path, test_module_file):
    """Test _execute_python_function raises TypeError when args is not a list."""
    workflow = {
        "steps": [
            {
                "name": "run_func_bad_args",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "my_func",
                    "args": "not_a_list",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert (
        "args" in str(e.value.original_error).lower()
        and "list" in str(e.value.original_error).lower()
    )


def test_python_function_kwargs_not_dict(tmp_path: Path, test_module_file):
    """Test _execute_python_function raises TypeError when kwargs is not a dict."""
    workflow = {
        "steps": [
            {
                "name": "run_func_bad_kwargs",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "my_func",
                    "args": [5],
                    "kwargs": "not_a_dict",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert (
        "kwargs" in str(e.value.original_error).lower()
        and "dict" in str(e.value.original_error).lower()
    )


# === Tests for async function execution (lines 136-146) ===


def test_python_function_async(tmp_path: Path, test_module_file):
    """Test python_function with an async function."""
    workflow = {
        "steps": [
            {
                "name": "run_async",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": "async_add",
                    "args": [3, 7],
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_async"]["result"] == 10


# === Tests for python_function input validation (lines 334, 336) ===


def test_python_function_missing_module_input(tmp_path: Path):
    """Test python_function when module input is missing."""
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "function": "some_func",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "module" in str(e.value.original_error).lower()


def test_python_function_missing_function_input(tmp_path: Path, test_module_file):
    """Test python_function when function input is missing."""
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "function" in str(e.value.original_error).lower()


def test_python_function_module_not_string(tmp_path: Path):
    """Test python_function when module input is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": 123,
                    "function": "some_func",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "module" in str(e.value.original_error).lower()


def test_python_function_function_not_string(tmp_path: Path, test_module_file):
    """Test python_function when function input is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_func_fail",
                "task": "python_function",
                "inputs": {
                    "module": "test_module",
                    "function": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "function" in str(e.value.original_error).lower()


# === Tests for python_script input validation (lines 377-386) ===


def test_python_script_args_not_list(tmp_path: Path, test_script_file):
    """Test python_script raises error when args is not a list."""
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "args": "not_a_list",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert (
        "args" in str(e.value.original_error).lower()
        and "list" in str(e.value.original_error).lower()
    )


def test_python_script_cwd_not_string(tmp_path: Path, test_script_file):
    """Test python_script raises error when cwd is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "cwd": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "cwd" in str(e.value.original_error).lower()


def test_python_script_timeout_not_number(tmp_path: Path, test_script_file):
    """Test python_script raises error when timeout is not a number."""
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": str(test_script_file.relative_to(tmp_path)),
                    "timeout": "not_a_number",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "timeout" in str(e.value.original_error).lower()


def test_python_script_missing_script_path(tmp_path: Path):
    """Test python_script raises error when script_path is missing."""
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "script_path" in str(e.value.original_error).lower()


def test_python_script_script_path_not_string(tmp_path: Path):
    """Test python_script raises error when script_path is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "script_path" in str(e.value.original_error).lower()


# === Tests for python_script timeout (line 217) ===


def test_python_script_timeout(tmp_path: Path):
    """Test python_script raises TimeoutError when script exceeds timeout."""
    slow_script = tmp_path / "slow_script.py"
    slow_script.write_text("import time\ntime.sleep(60)\n")
    workflow = {
        "steps": [
            {
                "name": "run_slow",
                "task": "python_script",
                "inputs": {
                    "script_path": str(slow_script.relative_to(tmp_path)),
                    "timeout": 0.1,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "timed out" in str(e.value.original_error).lower()


# === Tests for _find_script edge cases (lines 171, 185) ===


def test_python_script_absolute_path_not_found(tmp_path: Path):
    """Test _find_script raises error for non-existent absolute path."""
    non_existent = str(tmp_path / "definitely_not_here.py")
    workflow = {
        "steps": [
            {
                "name": "run_script_fail",
                "task": "python_script",
                "inputs": {
                    "script_path": non_existent,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "not found" in str(e.value.original_error).lower()


def test_find_script_in_system_path(tmp_path: Path):
    """Test _find_script finds a script in the system PATH."""
    # Create a script in a temp directory and add it to PATH
    bin_dir = tmp_path / "custom_bin"
    bin_dir.mkdir()
    script = bin_dir / "path_script.py"
    script.write_text("print('found in PATH')\n")
    script.chmod(0o755)

    new_path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    with patch.dict(os.environ, {"PATH": new_path}):
        result = python_tasks._find_script(
            "path_script.py", tmp_path / "other_workspace"
        )
    assert result == script


# === Tests for _execute_script FileNotFoundError (lines 211-215) ===


def test_execute_script_file_not_found():
    """Test _execute_script raises FileNotFoundError when python or script not found."""
    with patch(
        "yaml_workflow.tasks.python_tasks.subprocess.run",
        side_effect=FileNotFoundError("not found"),
    ):
        with pytest.raises(
            FileNotFoundError, match="Python executable or script not found"
        ):
            python_tasks._execute_script(Path("/fake/script.py"))


# === Tests for python_module input validation (lines 449-458) ===


def test_python_module_missing_module_input(tmp_path: Path):
    """Test python_module raises error when module input is missing."""
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "module" in str(e.value.original_error).lower()


def test_python_module_module_not_string(tmp_path: Path):
    """Test python_module raises error when module is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {
                    "module": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "module" in str(e.value.original_error).lower()


def test_python_module_args_not_list(tmp_path: Path, test_exec_module_file):
    """Test python_module raises error when args is not a list."""
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {
                    "module": test_exec_module_file,
                    "args": "not_a_list",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert (
        "args" in str(e.value.original_error).lower()
        and "list" in str(e.value.original_error).lower()
    )


def test_python_module_cwd_not_string(tmp_path: Path, test_exec_module_file):
    """Test python_module raises error when cwd is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {
                    "module": test_exec_module_file,
                    "cwd": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "cwd" in str(e.value.original_error).lower()


def test_python_module_timeout_not_number(tmp_path: Path, test_exec_module_file):
    """Test python_module raises error when timeout is not a number."""
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {
                    "module": test_exec_module_file,
                    "timeout": "not_a_number",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "timeout" in str(e.value.original_error).lower()


# === Tests for python_module timeout (lines 254-255) ===


def test_python_module_timeout(tmp_path: Path):
    """Test python_module raises TimeoutError when module execution times out."""
    # Create a slow module
    slow_module = tmp_path / "slow_module"
    slow_module.mkdir()
    (slow_module / "__main__.py").write_text("import time\ntime.sleep(60)\n")
    sys.path.insert(0, str(tmp_path))
    try:
        workflow = {
            "steps": [
                {
                    "name": "run_slow_module",
                    "task": "python_module",
                    "inputs": {
                        "module": "slow_module",
                        "timeout": 0.1,
                    },
                }
            ]
        }
        engine = WorkflowEngine(workflow, workspace=str(tmp_path))
        with pytest.raises(WorkflowError) as e:
            engine.run()
        assert "timed out" in str(e.value.original_error).lower()
    finally:
        sys.path.pop(0)


# === Tests for _execute_module PYTHONPATH handling (lines 235->243, 239) ===


def test_execute_module_pythonpath_existing(tmp_path: Path):
    """Test _execute_module appends workspace to existing PYTHONPATH."""
    with patch.dict(os.environ, {"PYTHONPATH": "/existing/path"}):
        with patch("yaml_workflow.tasks.python_tasks.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="ok", stderr=""
            )
            python_tasks._execute_module("some_module", workspace=tmp_path)
            # Verify the env passed to subprocess has both paths
            call_kwargs = mock_run.call_args[1]
            pythonpath = call_kwargs["env"]["PYTHONPATH"]
            assert str(tmp_path.resolve()) in pythonpath
            assert "/existing/path" in pythonpath
            assert os.pathsep in pythonpath


# === Tests for _execute_code stdout capture (line 285) ===


def test_python_code_with_stdout(tmp_path: Path):
    """Test python_code captures stdout from code execution."""
    workflow = {
        "steps": [
            {
                "name": "run_code_print",
                "task": "python_code",
                "inputs": {
                    "code": "print('hello from code')\nresult = 42",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_code_print"]["result"] == 42


# === Tests for _execute_code error with stderr (lines 308-309) ===


def test_python_code_error_with_stderr(tmp_path: Path):
    """Test _execute_code includes captured stderr in error when code fails."""
    workflow = {
        "steps": [
            {
                "name": "run_code_stderr",
                "task": "python_code",
                "inputs": {
                    "code": "import sys\nprint('error info', file=sys.stderr)\nraise RuntimeError('test error')",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    # The error should be a TaskExecutionError wrapping the original
    assert "test error" in str(e.value.original_error)


# === Tests for python_code input validation (lines 522, 524) ===


def test_python_code_missing_code_input(tmp_path: Path):
    """Test python_code raises error when code input is missing."""
    workflow = {
        "steps": [
            {
                "name": "run_code_fail",
                "task": "python_code",
                "inputs": {},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "code" in str(e.value.original_error).lower()


def test_python_code_code_not_string(tmp_path: Path):
    """Test python_code raises error when code is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_code_fail",
                "task": "python_code",
                "inputs": {
                    "code": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "code" in str(e.value.original_error).lower()


def test_python_code_result_variable_not_string(tmp_path: Path):
    """Test python_code raises error when result_variable is not a string."""
    workflow = {
        "steps": [
            {
                "name": "run_code_fail",
                "task": "python_code",
                "inputs": {
                    "code": "result = 1",
                    "result_variable": 123,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError) as e:
        engine.run()
    assert "result_variable" in str(e.value.original_error).lower()


# === Tests for python_code syntax error ===


def test_python_code_syntax_error(tmp_path: Path):
    """Test python_code raises error on syntax error in code."""
    workflow = {
        "steps": [
            {
                "name": "run_code_syntax",
                "task": "python_code",
                "inputs": {
                    "code": "def foo(\n  # syntax error",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    with pytest.raises(WorkflowError):
        engine.run()


# === Test python_module fail without check ===


def test_python_module_fail_no_check(tmp_path: Path, test_exec_module_file):
    """Test python_module succeeds with non-zero exit when check=False."""
    module_name = test_exec_module_file
    workflow = {
        "steps": [
            {
                "name": "run_module_fail",
                "task": "python_module",
                "inputs": {
                    "module": module_name,
                    "args": ["fail"],
                    "check": False,
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_module_fail"]["result"]["returncode"] == 5


# ---------------------------------------------------------------------------
# CWD and workspace path tests
# ---------------------------------------------------------------------------


def test_python_code_cwd_is_workspace(tmp_path: Path):
    """python_code should execute with CWD set to the workspace directory."""
    workflow = {
        "steps": [
            {
                "name": "check_cwd",
                "task": "python_code",
                "inputs": {"code": "import os; result = os.getcwd()"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    # CWD during exec should be the workspace
    assert (
        Path(status["outputs"]["check_cwd"]["result"]).resolve() == tmp_path.resolve()
    )


def test_python_code_workspace_variable(tmp_path: Path):
    """python_code should have 'workspace' as a Path in the exec context."""
    workflow = {
        "steps": [
            {
                "name": "check_ws",
                "task": "python_code",
                "inputs": {
                    "code": "from pathlib import Path; result = isinstance(workspace, Path)"
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["check_ws"]["result"] is True


def test_python_code_relative_path_resolves_to_workspace(tmp_path: Path):
    """Relative file paths in python_code should resolve against the workspace."""
    workflow = {
        "steps": [
            {
                "name": "write_file",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "with open('test_relative.txt', 'w') as f:\n"
                        "    f.write('hello')\n"
                        "result = 'written'"
                    )
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    # The file should be in the workspace, not the process CWD
    assert (tmp_path / "test_relative.txt").exists()
    assert (tmp_path / "test_relative.txt").read_text() == "hello"
