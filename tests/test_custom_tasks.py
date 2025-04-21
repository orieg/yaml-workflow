import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.tasks import TaskConfig, get_task_handler, register_task
from yaml_workflow.tasks.base import (
    get_task_logger,
    log_task_error,
    log_task_execution,
    log_task_result,
)


@pytest.fixture
def custom_task_module():
    """Create a custom task module for testing."""

    @register_task("custom")
    def custom_task(config: TaskConfig) -> Dict[str, Any]:
        logger = get_task_logger(config.workspace, config.name or "custom")
        log_task_execution(
            logger,
            {"name": config.name, "type": config.type},
            config._context,
            config.workspace,
        )

        processed = config.process_inputs()
        message = processed.get("message")

        if message is None or message == "":
            raise ValueError("Message cannot be empty")

        logger.info(f"Custom task executing with message: {message}")
        return {"success": True, "output": f"Custom task executed: {message}"}

    return custom_task


def test_custom_task_basic(custom_task_module, temp_workspace):
    """Test basic custom task execution."""
    step = {
        "name": "test_task",
        "task": "custom",
        "inputs": {"message": "Hello"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = custom_task_module(config)
    assert "Custom task executed: Hello" in result["output"]


def test_custom_task_default_message(custom_task_module, temp_workspace):
    """Test custom task with default message."""
    step = {
        "name": "test_task",
        "task": "custom",
        "inputs": {},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(ValueError, match="Message cannot be empty"):
        custom_task_module(config)


def test_custom_task_error_handling(custom_task_module, temp_workspace):
    """Test custom task error handling."""
    step = {
        "name": "test_task",
        "task": "custom",
        "inputs": {"message": None},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(ValueError, match="Message cannot be empty"):
        custom_task_module(config)


def test_custom_task_validation(custom_task_module, temp_workspace):
    """Test custom task input validation."""
    step = {
        "name": "test_task",
        "task": "custom",
        "inputs": {"message": ""},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(ValueError, match="Message cannot be empty"):
        custom_task_module(config)


def test_custom_task_in_workflow(custom_task_module, temp_workspace):
    """Test custom task within a workflow."""
    workflow = {
        "name": "test_workflow",
        "steps": [
            {
                "name": "custom_step",
                "task": "custom",
                "inputs": {"message": "Workflow message"},
            }
        ],
    }

    engine = WorkflowEngine(workflow, temp_workspace)
    result = engine.run()

    assert result["status"] == "completed"
    assert result["outputs"]["custom_step"]["result"]["success"]
    assert (
        "Custom task executed: Workflow message"
        in result["outputs"]["custom_step"]["result"]["output"]
    )


def test_custom_task_with_progress(temp_workspace):
    """Test custom task with progress reporting."""
    progress_updates = []

    @register_task("progress")
    def progress_task(config: TaskConfig) -> Dict[str, Any]:
        processed = config.process_inputs()
        total = processed.get("total", 100)
        for i in range(total):
            progress = (i + 1) / total
            config._context.get("progress_callback", lambda x: None)(progress)
        return {"success": True, "output": "Progress task completed"}

    step = {
        "name": "progress_task",
        "task": "progress",
        "inputs": {"total": 10},
    }
    context = {"progress_callback": progress_updates.append}
    config = TaskConfig(step, context, temp_workspace)
    result = progress_task(config)

    assert len(progress_updates) == 10
    assert progress_updates[-1] == 1.0


def test_custom_task_with_cleanup(temp_workspace):
    """Test custom task with cleanup handling."""
    temp_file = temp_workspace / "temp.txt"

    @register_task("cleanup")
    def cleanup_task(config: TaskConfig) -> Dict[str, Any]:
        temp_file.write_text("Temporary content")
        try:
            return {"success": True, "output": "Task completed"}
        finally:
            temp_file.unlink()

    step = {
        "name": "cleanup_task",
        "task": "cleanup",
        "inputs": {},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = cleanup_task(config)
    assert result["output"] == "Task completed"
    assert not temp_file.exists()


def test_custom_task_with_dependencies(temp_workspace):
    """Test custom task with external dependencies."""

    @register_task("dependent")
    def dependent_task(config: TaskConfig) -> Dict[str, Any]:
        processed = config.process_inputs()
        dependency = processed.get("dependency")
        if not dependency:
            raise ValueError("Missing dependency")
        return {"success": True, "output": f"Task used dependency: {dependency}"}

    step = {
        "name": "dependent_task",
        "task": "dependent",
        "inputs": {"dependency": "test_dep"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = dependent_task(config)
    assert "Task used dependency: test_dep" in result["output"]


def test_custom_task_with_retries():
    """Test custom task with retry mechanism."""
    attempt_count = 0

    @register_task("retry")
    def retry_task(config: TaskConfig) -> Dict[str, Any]:
        nonlocal attempt_count
        attempt_count += 1

        if attempt_count < 3:
            raise ValueError("Temporary failure")
        return {"success": True, "output": "Task succeeded after retries"}

    step = {
        "name": "retry_task",
        "task": "retry",
        "inputs": {},
    }
    config = TaskConfig(step, {}, Path())
    with pytest.raises(ValueError):
        retry_task(config)
    assert attempt_count == 1


def test_custom_task_with_logging(temp_workspace):
    """Test custom task with logging functionality."""
    log_dir = temp_workspace / "logs"
    log_dir.mkdir(exist_ok=True)

    @register_task("logging")
    def logging_task(config: TaskConfig) -> Dict[str, Any]:
        logger = get_task_logger(config.workspace, "test_logging")
        logger.info("Task started")
        result = {"success": True, "output": "Logging task completed"}
        logger.info("Task completed")
        return result

    step = {
        "name": "logging_task",
        "task": "logging",
        "inputs": {},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = logging_task(config)
    assert result["output"] == "Logging task completed"

    # Check that at least one log file was created
    log_files = list(log_dir.glob("*.log"))
    assert len(log_files) > 0


def test_custom_task_registration():
    """Test custom task type registration."""

    @register_task("task1")
    def task1(config: TaskConfig) -> Dict[str, Any]:
        return {"success": True, "output": "Task 1"}

    @register_task("task2")
    def task2(config: TaskConfig) -> Dict[str, Any]:
        return {"success": True, "output": "Task 2"}

    assert get_task_handler("task1") is task1
    assert get_task_handler("task2") is task2
