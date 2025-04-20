"""Tests for tasks defined in basic_tasks.py."""

from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import StepExecutionError, WorkflowError

# We need to import basic_tasks to ensure its @register_task decorators run
from yaml_workflow.tasks import get_task_handler  # Ensure tasks are registered
from yaml_workflow.tasks import basic_tasks


def test_fail_task(tmp_path: Path):
    """Test that the 'fail' task raises a StepExecutionError."""
    workflow_yaml = f"""
    steps:
      - name: should_fail
        task: fail
        inputs:
          message: "Test failure message"
    """
    workflow_file = tmp_path / "fail_workflow.yaml"
    workflow_file.write_text(workflow_yaml)

    engine = WorkflowEngine(str(workflow_file), workspace=str(tmp_path))

    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    assert "Workflow halted at step 'should_fail'" in str(exc_info.value)
    assert isinstance(exc_info.value.original_error, RuntimeError)
    assert "Test failure message" in str(exc_info.value.original_error)


def test_join_strings_task_default_separator(tmp_path: Path):
    """Test the 'join_strings' task with default separator."""
    workflow_yaml = f"""
    steps:
      - name: join_default
        task: join_strings
        inputs:
          strings:
            - "hello"
            - "world"
            - "from"
            - "test"
    """
    workflow_file = tmp_path / "join_default_workflow.yaml"
    workflow_file.write_text(workflow_yaml)

    engine = WorkflowEngine(str(workflow_file), workspace=str(tmp_path))
    run_status = engine.run()

    assert run_status["status"] == "completed"
    assert "outputs" in run_status
    assert "join_default" in run_status["outputs"]
    assert isinstance(run_status["outputs"]["join_default"], dict)
    assert run_status["outputs"]["join_default"]["result"] == "hello world from test"


def test_join_strings_task_custom_separator(tmp_path: Path):
    """Test the 'join_strings' task with a custom separator."""
    workflow_yaml = f"""
    steps:
      - name: join_custom
        task: join_strings
        inputs:
          strings:
            - "apple"
            - "banana"
            - "cherry"
          separator: ", "
    """
    workflow_file = tmp_path / "join_custom_workflow.yaml"
    workflow_file.write_text(workflow_yaml)

    engine = WorkflowEngine(str(workflow_file), workspace=str(tmp_path))
    run_status = engine.run()

    assert run_status["status"] == "completed"
    assert "outputs" in run_status
    assert "join_custom" in run_status["outputs"]
    assert isinstance(run_status["outputs"]["join_custom"], dict)
    assert run_status["outputs"]["join_custom"]["result"] == "apple, banana, cherry"
