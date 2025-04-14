import json
import os
import time
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.workspace import WorkflowState


@pytest.fixture
def workflow_state(temp_workspace):
    """Create a workflow state instance."""
    return WorkflowState(temp_workspace)


@pytest.fixture
def sample_workflow(temp_workspace):
    """Create a sample workflow file."""
    workflow_content = """
name: test_workflow
description: Test workflow for state management

steps:
  - name: step1
    task: echo
    params:
      message: "Step 1"
  
  - name: step2
    task: echo
    params:
      message: "Step 2"
  
  - name: step3
    task: echo
    params:
      message: "Step 3"
"""
    workflow_file = temp_workspace / "workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


@pytest.fixture
def failing_workflow(temp_workspace):
    """Create a workflow file with a failing step."""
    workflow_content = """
name: test_workflow
description: Test workflow for state management

steps:
  - name: step1
    task: echo
    inputs:
      message: "Step 1"
  
  - name: step2
    task: fail
    inputs:
      message: "Step 2 failure"
  
  - name: step3
    task: echo
    inputs:
      message: "Step 3"
"""
    workflow_file = temp_workspace / "workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


def test_workflow_state_initialization(workflow_state):
    """Test workflow state initialization."""
    assert workflow_state.metadata["execution_state"]["current_step"] == 0
    assert workflow_state.metadata["execution_state"]["completed_steps"] == []
    assert workflow_state.metadata["execution_state"]["failed_step"] is None
    assert workflow_state.metadata["execution_state"]["status"] == "not_started"


def test_workflow_step_completion(workflow_state):
    """Test marking steps as completed."""
    workflow_state.mark_step_complete("step1", {"step1": "output1"})
    state = workflow_state.get_state()

    assert state["steps"]["step1"]["status"] == "completed"
    assert state["steps"]["step1"]["outputs"] == {"step1": "output1"}
    assert workflow_state.metadata["execution_state"]["current_step"] == 1
    assert "step1" in workflow_state.metadata["execution_state"]["completed_steps"]


def test_workflow_step_failure(workflow_state):
    """Test marking steps as failed."""
    workflow_state.mark_step_failed("step2", "Test error")
    state = workflow_state.get_state()

    assert state["steps"]["step2"]["status"] == "failed"
    assert workflow_state.metadata["execution_state"]["status"] == "failed"
    assert (
        workflow_state.metadata["execution_state"]["failed_step"]["step_name"]
        == "step2"
    )
    assert (
        workflow_state.metadata["execution_state"]["failed_step"]["error"]
        == "Test error"
    )


def test_workflow_completion(workflow_state):
    """Test marking workflow as completed."""
    workflow_state.mark_step_complete("step1", {"step1": "output1"})
    workflow_state.mark_step_complete("step2", {"step2": "output2"})
    workflow_state.mark_workflow_completed()

    assert workflow_state.metadata["execution_state"]["status"] == "completed"
    assert "completed_at" in workflow_state.metadata["execution_state"]


def test_workflow_state_persistence(temp_workspace, workflow_state):
    """Test state persistence to file."""
    # Add some state
    workflow_state.mark_step_complete("step1", {"step1": "output1"})
    workflow_state.save()

    # Create new state instance and verify persistence
    new_state = WorkflowState(temp_workspace)
    assert new_state.metadata["execution_state"]["completed_steps"] == ["step1"]
    assert new_state.metadata["execution_state"]["step_outputs"]["step1"] == {
        "step1": "output1"
    }


def test_workflow_resume_capability(temp_workspace, failing_workflow):
    """Test workflow resume capability."""
    engine = WorkflowEngine(str(failing_workflow))

    # First run should fail at step2
    try:
        engine.run()
    except Exception:
        pass

    # Verify state after failure
    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "failed"
    assert "step1" in state["execution_state"]["completed_steps"]
    assert state["execution_state"]["failed_step"]["step_name"] == "step2"

    # Modify workflow to make step2 succeed
    engine.workflow["steps"][1][
        "task"
    ] = "echo"  # Change step2 to use echo instead of fail
    engine.workflow["steps"][1]["inputs"] = {
        "message": "Step 2"
    }  # Update inputs for echo task
    result = engine.run(resume_from="step2")

    # Verify completion
    assert result["status"] == "completed"
    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "completed"
    assert all(
        step in state["execution_state"]["completed_steps"]
        for step in ["step1", "step2", "step3"]
    )


def test_workflow_state_reset(workflow_state):
    """Test resetting workflow state."""
    # Add some state
    workflow_state.mark_step_complete("step1", {"step1": "output1"})
    workflow_state.mark_step_failed("step2", "Test error")

    # Reset state
    workflow_state.reset_state()

    # Verify reset
    assert workflow_state.metadata["execution_state"]["current_step"] == 0
    assert workflow_state.metadata["execution_state"]["completed_steps"] == []
    assert workflow_state.metadata["execution_state"]["failed_step"] is None
    assert workflow_state.metadata["execution_state"]["status"] == "not_started"
    assert workflow_state.metadata["execution_state"]["step_outputs"] == {}


def test_workflow_output_tracking(workflow_state):
    """Test tracking of step outputs."""
    outputs1 = {"result": "output1", "status": "success"}
    outputs2 = {"result": "output2", "count": 42}

    workflow_state.mark_step_complete("step1", outputs1)
    workflow_state.mark_step_complete("step2", outputs2)

    completed_outputs = workflow_state.get_completed_outputs()
    assert completed_outputs["step1"] == outputs1
    assert completed_outputs["step2"] == outputs2


def test_workflow_flow_tracking(workflow_state):
    """Test tracking of workflow flow."""
    # Set flow
    workflow_state.set_flow("main")
    assert workflow_state.get_flow() == "main"

    # Change flow
    workflow_state.set_flow("alternate")
    assert workflow_state.get_flow() == "alternate"

    # Clear flow
    workflow_state.set_flow(None)
    assert workflow_state.get_flow() is None
