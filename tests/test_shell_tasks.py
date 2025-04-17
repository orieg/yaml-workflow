"""Tests for shell task implementation."""

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from yaml_workflow.exceptions import TaskExecutionError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.shell_tasks import shell_task


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
    assert result["exit_code"] == 0
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
    assert result["exit_code"] == 0


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
    assert result["exit_code"] == 0


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
    assert result["exit_code"] == 0


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

    assert "Command failed with exit code 1" in str(exc_info.value)


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

    assert "Command timed out" in str(exc_info.value)


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
    assert result["exit_code"] == 0


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
    assert result["exit_code"] == 0
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
    assert result["exit_code"] == 0
