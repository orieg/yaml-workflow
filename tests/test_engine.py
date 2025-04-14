import os
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import (
    FlowNotFoundError,
    InvalidFlowDefinitionError,
    StepNotInFlowError,
    WorkflowError,
)
from yaml_workflow.tasks import register_task


@pytest.fixture
def temp_workflow_file(tmp_path):
    workflow_content = """
name: test_workflow
params:
  param1:
    default: value1
  param2:
    default: value2

steps:
  - name: step1
    task: echo
    inputs:
      message: "Hello {{ param1 }}"
  
  - name: step2
    task: echo
    inputs:
      message: "Hello {{ param2 }}"

flows:
  definitions:
    - flow1:
        - step1
        - step2
  default: flow1
"""
    workflow_file = tmp_path / "workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


@pytest.fixture
def failed_workflow_file(tmp_path):
    workflow_content = """
name: test_workflow
params:
  param1:
    default: value1
  param2:
    default: value2

steps:
  - name: step1
    task: echo
    inputs:
      message: "Hello {{ param1 }}"
  
  - name: step2
    task: fail
    inputs:
      message: "This step always fails"

flows:
  definitions:
    - flow1:
        - step1
        - step2
  default: flow1
"""
    workflow_file = tmp_path / "failed_workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


def test_workflow_initialization(temp_workflow_file):
    engine = WorkflowEngine(str(temp_workflow_file))
    assert engine.name == "test_workflow"
    assert "param1" in engine.context
    assert engine.context["param1"] == "value1"
    assert "param2" in engine.context
    assert engine.context["param2"] == "value2"


def test_workflow_invalid_file():
    with pytest.raises(WorkflowError):
        WorkflowEngine("nonexistent_file.yaml")


def test_workflow_invalid_flow(tmp_path):
    invalid_workflow = """
name: test_workflow
flows:
  definitions:
    - flow1:
        - nonexistent_step
"""
    workflow_file = tmp_path / "invalid_workflow.yaml"
    workflow_file.write_text(invalid_workflow)

    with pytest.raises(StepNotInFlowError):
        WorkflowEngine(str(workflow_file))


def test_workflow_execution(temp_workflow_file):
    engine = WorkflowEngine(str(temp_workflow_file))
    result = engine.run()
    assert result["status"] == "completed"

    # Check if both steps were executed
    state = engine.state.get_state()
    assert "step1" in state["steps"]
    assert "step2" in state["steps"]
    assert state["steps"]["step1"]["status"] == "completed"
    assert state["steps"]["step2"]["status"] == "completed"


def test_workflow_with_custom_params(temp_workflow_file):
    engine = WorkflowEngine(str(temp_workflow_file))
    custom_params = {"param1": "custom1", "param2": "custom2"}
    result = engine.run(params=custom_params)
    assert result["status"] == "completed"

    # Verify custom parameters were used
    assert engine.context["param1"] == "custom1"
    assert engine.context["param2"] == "custom2"


def test_workflow_resume(failed_workflow_file):
    # First run should fail at step2
    engine = WorkflowEngine(str(failed_workflow_file))
    with pytest.raises(WorkflowError):
        engine.run()

    # Verify step1 completed but step2 failed
    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "failed"
    assert "step1" in state["steps"]
    assert state["steps"]["step1"]["status"] == "completed"

    # Now try to resume from step2 with a modified workflow
    engine.workflow["steps"][1][
        "task"
    ] = "echo"  # Change step2 to use echo instead of fail
    result = engine.run(resume_from="step2")
    assert result["status"] == "completed"

    # Verify both steps are now completed
    state = engine.state.get_state()
    assert "step1" in state["steps"]
    assert "step2" in state["steps"]
    assert state["steps"]["step1"]["status"] == "completed"
    assert state["steps"]["step2"]["status"] == "completed"


def test_on_error_fail(tmp_path):
    """Test on_error with fail action."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "fail",
                "inputs": {"message": "Deliberate failure"},
                "on_error": {"action": "fail", "message": "Custom error message"},
            }
        ]
    }
    engine = WorkflowEngine(workflow)

    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    assert "Custom error message" in str(exc_info.value)
    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "failed"
    assert state["execution_state"]["failed_step"]["step_name"] == "step1"
    assert "Custom error message" in state["execution_state"]["failed_step"]["error"]


def test_on_error_continue(tmp_path):
    """Test on_error with continue action."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "Step 1"},
            },
            {
                "name": "step2",
                "task": "fail",
                "inputs": {"message": "Deliberate failure"},
                "on_error": {"action": "continue", "message": "Skipping failed step"},
            },
            {
                "name": "step3",
                "task": "echo",
                "inputs": {"message": "Step 3"},
            },
        ]
    }
    engine = WorkflowEngine(workflow)
    result = engine.run()

    assert result["status"] == "completed"
    state = engine.state.get_state()
    assert "step1" in state["steps"]
    assert "step2" in state["steps"]
    assert "step3" in state["steps"]
    assert state["steps"]["step1"]["status"] == "completed"
    assert state["steps"]["step2"]["status"] == "failed"
    assert state["steps"]["step3"]["status"] == "completed"


def test_on_error_retry(tmp_path):
    """Test on_error with retry action."""
    attempts = []

    @register_task("flaky")
    def flaky_task(step, context, workspace):
        attempts.append(len(attempts) + 1)
        if len(attempts) < 3:
            raise ValueError("Temporary failure")
        return {"success": True}

    workflow = {
        "steps": [
            {
                "name": "flaky_step",
                "task": "flaky",
                "retry": {"max_attempts": 3, "delay": 0.1, "backoff": 1},
                "on_error": {"action": "retry", "message": "Retrying flaky step"},
            }
        ]
    }
    engine = WorkflowEngine(workflow)
    result = engine.run()

    assert result["status"] == "completed"
    assert len(attempts) == 3  # Should succeed on third try
    state = engine.state.get_state()
    assert state["steps"]["flaky_step"]["status"] == "completed"


def test_on_error_notify(tmp_path):
    """Test on_error with notify action."""
    notifications = []

    @register_task("notify")
    def notify_task(step, context, workspace):
        notifications.append(context["error"])
        return {"notified": True}

    workflow = {
        "steps": [
            {
                "name": "failing_step",
                "task": "fail",
                "inputs": {"message": "Deliberate failure"},
                "on_error": {
                    "action": "notify",
                    "message": "Step failed: {{ error }}",
                    "next": "notification",
                },
            },
            {"name": "notification", "task": "notify"},
        ]
    }
    engine = WorkflowEngine(workflow)

    with pytest.raises(WorkflowError):
        engine.run()

    assert len(notifications) == 1
    assert notifications[0]["step"] == "failing_step"
    assert "Deliberate failure" in notifications[0]["error"]


def test_on_error_template_message(tmp_path):
    """Test on_error with template message."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "fail",
                "inputs": {"message": "Error XYZ occurred"},
                "on_error": {
                    "action": "fail",
                    "message": "Task failed with: {{ error }}",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow)

    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    assert "Task failed with: Error XYZ occurred" in str(exc_info.value)
    state = engine.state.get_state()
    assert (
        "Task failed with: Error XYZ occurred"
        in state["execution_state"]["failed_step"]["error"]
    )
