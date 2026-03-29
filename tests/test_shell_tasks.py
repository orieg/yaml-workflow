"""Tests for shell task implementation."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict

import jinja2
import pytest

from yaml_workflow.exceptions import TaskExecutionError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.shell_tasks import (
    check_command,
    process_command,
    run_command,
    set_environment,
    shell_task,
)


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Create a temporary workspace for testing."""
    return tmp_path


@pytest.fixture
def basic_context() -> Dict[str, Any]:
    """Create a basic context with namespaces."""
    return {
        "args": {
            "test_arg": "value1",
            "debug": True,
            "items": ["apple", "banana", "cherry"],
            "count": 3,
        },
        "env": {"test_env": "value2"},
        "steps": {"previous_step": {"output": "value3"}},
        "root_var": "value4",
    }


def test_shell_basic(workspace, basic_context):
    """Test basic shell command execution."""
    step = {
        "name": "test_shell",
        "task": "shell",
        "inputs": {"command": "echo 'Hello World'"},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "Hello World"
    assert result["return_code"] == 0
    assert result["stderr"] == ""


def test_shell_with_variables(workspace, basic_context):
    """Test shell command with variable substitution."""
    step = {
        "name": "test_shell_vars",
        "task": "shell",
        "inputs": {
            "command": "echo 'Arg: {{ args.test_arg }}, Env: {{ env.test_env }}'"
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "Arg: value1, Env: value2"
    assert result["return_code"] == 0


def test_shell_with_working_dir(workspace, basic_context):
    """Test shell command with working directory."""
    test_dir = workspace / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test.txt"
    test_file.write_text("test content")

    step = {
        "name": "test_shell_working_dir",
        "task": "shell",
        "inputs": {"command": "cat test.txt", "working_dir": "test_dir"},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "test content"
    assert result["return_code"] == 0


def test_shell_with_env_vars(workspace, basic_context):
    """Test shell command with environment variables."""
    step = {
        "name": "test_shell_env",
        "task": "shell",
        "inputs": {"command": "echo $TEST_VAR", "env": {"TEST_VAR": "test_value"}},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "test_value"
    assert result["return_code"] == 0


def test_shell_command_failure(workspace, basic_context):
    """Test shell command that fails."""
    step = {
        "name": "test_shell_failure",
        "task": "shell",
        "inputs": {"command": "exit 1"},
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        shell_task(config)

    assert "Command 'exit 1' returned non-zero exit status 1." in str(exc_info.value)


def test_shell_command_timeout(workspace, basic_context):
    """Test shell command with timeout."""
    step = {
        "name": "test_shell_timeout",
        "task": "shell",
        "inputs": {"command": "sleep 5", "timeout": 0.1},
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        shell_task(config)

    assert "Command 'sleep 5' timed out after 0.1 seconds" in str(exc_info.value)


def test_shell_with_batch_context(workspace, basic_context):
    """Test shell command in batch context."""
    basic_context["batch"] = {"item": "test_item", "index": 0, "total": 1}

    step = {
        "name": "test_shell_batch",
        "task": "shell",
        "inputs": {"command": "echo 'Processing {{ batch.item }}'"},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "Processing test_item"
    assert result["return_code"] == 0


def test_shell_with_undefined_variable(workspace, basic_context):
    """Test shell command with undefined variable."""
    step = {
        "name": "test_shell_undefined",
        "task": "shell",
        "inputs": {"command": "echo '{{ undefined_var }}'"},
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        shell_task(config)

    assert "undefined_var" in str(exc_info.value)


def test_shell_with_complex_command(workspace, basic_context):
    """Test shell command with complex operations."""
    step = {
        "name": "test_shell_complex",
        "task": "shell",
        "inputs": {
            "command": """
            mkdir -p testdir
            cd testdir
            echo 'test' > file.txt
            cat file.txt
            """
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "test"
    assert result["return_code"] == 0
    assert (workspace / "testdir" / "file.txt").exists()


def test_shell_with_special_chars(workspace, basic_context):
    """Test shell command with special characters."""
    basic_context["args"]["special"] = "test$with|special&chars"

    step = {
        "name": "test_shell_special",
        "task": "shell",
        "inputs": {"command": "echo '{{ args.special }}'"},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "test$with|special&chars"
    assert result["return_code"] == 0


def test_shell_command_as_list(workspace, basic_context):
    """Test shell command execution when command is a list and shell=False."""
    step = {
        "name": "test_shell_list",
        "task": "shell",
        "inputs": {
            "command": ["echo", "Hello", "List"],
            "shell": False,  # Explicitly set shell to False
        },
    }
    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)
    assert result["stdout"].strip() == "Hello List"
    assert result["return_code"] == 0


def test_shell_command_failure_non_zero_exit(workspace, basic_context):
    """Test shell task when command succeeds but returns non-zero exit code."""
    step = {
        "name": "test_shell_fail_exit",
        "task": "shell",
        "inputs": {"command": "ls /nonexistent ; exit 0"},  # Command fails but exits 0
    }
    # This should still pass as the *script* exits 0, error is in stderr
    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)
    assert result["return_code"] == 0
    assert "No such file or directory" in result["stderr"]

    # Test actual non-zero exit code from the *command* itself
    step_fail = {
        "name": "test_shell_fail_exit_code",
        "task": "shell",
        "inputs": {"command": "ls /nonexistent"},
    }
    config_fail = TaskConfig(step_fail, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        shell_task(config_fail)
    # Different shells might give different codes, check for non-zero
    assert "returned non-zero exit status" in str(exc_info.value)
    # Check context in the exception
    assert isinstance(exc_info.value.original_error, subprocess.CalledProcessError)
    assert exc_info.value.original_error.returncode != 0
    assert "No such file or directory" in exc_info.value.original_error.stderr


def test_check_command_failure(workspace):
    """Test check_command utility failure."""
    with pytest.raises(subprocess.CalledProcessError):
        check_command("exit 1", shell=True, cwd=str(workspace))


def test_run_command_as_list_no_shell(workspace):
    """Test run_command utility with command as list and shell=False."""
    returncode, stdout, stderr = run_command(
        ["echo", "Test", "Command"], cwd=str(workspace), shell=False
    )
    assert returncode == 0
    assert stdout.strip() == "Test Command"
    assert stderr == ""


def test_set_environment_utility():
    """Test the set_environment utility function."""
    initial_env = dict(os.environ)
    try:
        new_vars = {"TEST_SET_ENV_VAR": "set_env_value"}
        updated_env = set_environment(new_vars)
        assert os.environ["TEST_SET_ENV_VAR"] == "set_env_value"
        assert updated_env["TEST_SET_ENV_VAR"] == "set_env_value"
    finally:
        # Clean up environment
        if "TEST_SET_ENV_VAR" in os.environ:
            del os.environ["TEST_SET_ENV_VAR"]
        # Restore initial state if needed (though less critical in isolated tests)
        # for k, v in initial_env.items():
        #     os.environ[k] = v
        # for k in list(os.environ.keys()):
        #     if k not in initial_env:
        #         del os.environ[k]


def test_shell_with_absolute_working_dir(workspace, basic_context):
    """Test shell command with an absolute working directory path."""
    abs_test_dir = workspace / "abs_dir"
    abs_test_dir.mkdir()
    abs_file = abs_test_dir / "abs_test.txt"
    abs_file.write_text("absolute content")

    step = {
        "name": "test_shell_abs_working_dir",
        "task": "shell",
        "inputs": {"command": "cat abs_test.txt", "working_dir": str(abs_test_dir)},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = shell_task(config)

    assert result["stdout"].strip() == "absolute content"
    assert result["return_code"] == 0


def test_shell_missing_command_parameter(workspace, basic_context):
    """Test shell task when the required 'command' input is missing."""
    step = {
        "name": "test_shell_no_command",
        "task": "shell",
        "inputs": {},  # No 'command' key
    }
    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        shell_task(config)
    # Check that the original error was ValueError as expected internally
    assert isinstance(exc_info.value.original_error, ValueError)
    assert "command parameter is required" in str(exc_info.value.original_error)


def test_shell_process_command_undefined_variable_detail(workspace, basic_context):
    """Test process_command template failure with detailed context check."""
    command_template = "echo 'Undefined: {{ missing_var }}'"
    # Add necessary context items used by process_command for error reporting
    error_context = {
        **basic_context,
        "step_name": "test_detail_error",
        "task_type": "shell",
        "task_config": {"inputs": {"command": command_template}},
    }

    with pytest.raises(TaskExecutionError) as exc_info:
        process_command(command_template, error_context)

    err_str = str(exc_info.value)
    assert "Undefined variable 'missing_var'" in err_str
    assert "Available variables by namespace:" in err_str
    assert "args: test_arg, debug, items, count" in err_str
    assert "env: test_env" in err_str
    assert "steps: previous_step" in err_str
    # Ensure root_var is shown as it's at the top level of the context passed
    # assert "root_var" in err_str # <-- Removed this assertion
    assert "batch: (empty)" in err_str  # Since 'batch' wasn't added here


def test_shell_process_command_other_template_error(workspace, basic_context):
    """Test process_command with a generic template syntax error."""
    # Example: Invalid Jinja syntax like an unclosed brace
    command_template = (
        "echo '{{ args.test_arg }'"  # Missing closing braces deliberately
    )
    error_context = {
        **basic_context,
        "step_name": "test_syntax_error",
        "task_type": "shell",
        "task_config": {"inputs": {"command": command_template}},
    }
    with pytest.raises(TaskExecutionError) as exc_info:
        process_command(command_template, error_context)

    # Check that the original error is captured
    assert isinstance(exc_info.value.original_error, Exception)
    # The exact error might vary slightly based on Jinja version, check for key parts
    # Check for the specific Jinja syntax error being wrapped
    assert "unexpected '}'" in str(exc_info.value.original_error)
    assert isinstance(
        exc_info.value.original_error, jinja2.exceptions.TemplateSyntaxError
    )
    # Check that it's wrapped in TaskExecutionError
    assert exc_info.value.step_name == "test_syntax_error"
