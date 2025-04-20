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
def my_func(a, b=2):
    return a * b

def func_with_config(x, config):
    # Access config details if needed (config is injected)
    return x + config.context.get('offset', 0)

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
    assert status["outputs"]["run_func"]["result"]["result"] == 15


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
    with pytest.raises(WorkflowError) as e:
        engine.run()
    # Error message depends on Python version, check for core issue
    # assert "got an unexpected keyword argument 'c'" in str(e.value.original_error)
    # With the current inputs, the missing required argument 'a' should be raised first.
    assert "Missing required argument(s): a" in str(e.value.original_error)


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
    assert "Exiting with error" in status["outputs"]["run_script_fail"]["result"]["stderr"]


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
    assert status["outputs"]["run_code"]["result"]["result"] == 50


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
    workflow = {
        "steps": [
            {
                "name": "run_code_no_res",
                "task": "python_code",
                "inputs": {"code": "x = 100"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()
    assert status["status"] == "completed"
    assert status["outputs"]["run_code_no_res"]["result"]["result"] is None
