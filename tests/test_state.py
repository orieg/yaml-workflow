import json
import os
import time
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.workspace import WorkflowState, BatchState


@pytest.fixture
def workflow_state(temp_workspace):
    """Create a workflow state instance."""
    return WorkflowState(temp_workspace)


@pytest.fixture
def batch_state(temp_workspace):
    """Create a batch state instance."""
    return BatchState(temp_workspace, "test_batch")


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
    assert workflow_state.metadata["namespaces"] == {
        "args": {},
        "env": {},
        "steps": {},
        "batch": {}
    }


def test_namespace_state_isolation(workflow_state):
    """Test that namespaces remain isolated in state."""
    workflow_state.update_namespace("args", {"key": "value"})
    workflow_state.update_namespace("env", {"PATH": "/usr/bin"})
    workflow_state.update_namespace("steps", {"step1": {"output": "result"}})
    
    state = workflow_state.get_state()
    assert state["namespaces"]["args"]["key"] == "value"
    assert state["namespaces"]["env"]["PATH"] == "/usr/bin"
    assert state["namespaces"]["steps"]["step1"]["output"] == "result"
    assert "key" not in state["namespaces"]["env"]
    assert "PATH" not in state["namespaces"]["args"]


def test_namespace_variable_access(workflow_state):
    """Test variable access across namespaces."""
    workflow_state.update_namespace("args", {"input": "test"})
    workflow_state.update_namespace("steps", {"step1": {"output": "{{ args.input }}"}})
    
    assert workflow_state.get_variable("input", "args") == "test"
    assert workflow_state.get_variable("step1", "steps")["output"] == "{{ args.input }}"
    assert workflow_state.get_variable("nonexistent", "args") is None


def test_namespace_state_persistence(temp_workspace, workflow_state):
    """Test that namespace state persists correctly."""
    workflow_state.update_namespace("args", {"key": "value"})
    workflow_state.update_namespace("env", {"PATH": "/usr/bin"})
    workflow_state.save()

    new_state = WorkflowState(temp_workspace)
    assert new_state.get_variable("key", "args") == "value"
    assert new_state.get_variable("PATH", "env") == "/usr/bin"


def test_batch_state_initialization(batch_state):
    """Test batch state initialization."""
    assert batch_state.state["processed"] == []
    assert batch_state.state["failed"] == {}
    assert batch_state.state["template_errors"] == {}
    assert batch_state.state["namespaces"]["batch"] == {}
    assert batch_state.state["stats"]["total"] == 0


def test_batch_state_tracking(batch_state):
    """Test batch state tracking."""
    # Track processed items
    batch_state.mark_processed("item1", {"result": "success"})
    assert "item1" in batch_state.state["processed"]
    assert batch_state.state["stats"]["processed"] == 1

    # Track failed items
    batch_state.mark_failed("item2", "error message")
    assert "item2" in batch_state.state["failed"]
    assert batch_state.state["stats"]["failed"] == 1

    # Track template errors
    batch_state.mark_template_error("item3", "undefined variable")
    assert "item3" in batch_state.state["template_errors"]
    assert batch_state.state["stats"]["template_failures"] == 1


def test_batch_state_persistence(temp_workspace):
    """Test batch state persistence."""
    state = BatchState(temp_workspace, "test_persistence")
    state.mark_processed("item1", {"result": "success"})
    state.save()

    loaded_state = BatchState(temp_workspace, "test_persistence")
    assert "item1" in loaded_state.state["processed"]
    assert loaded_state.state["stats"]["processed"] == 1


def test_retry_state_management(workflow_state):
    """Test retry state management with namespace support."""
    retry_state = {
        "attempt": 1,
        "last_error": "Test error",
        "last_attempt": "2024-01-01T00:00:00",
        "namespace": "steps"
    }
    workflow_state.update_retry_state("step1", retry_state)

    state = workflow_state.get_retry_state("step1")
    assert state == retry_state
    assert state["namespace"] == "steps"

    workflow_state.clear_retry_state("step1")
    assert workflow_state.get_retry_state("step1") == {}


def test_state_reset(workflow_state):
    """Test complete state reset including namespaces."""
    workflow_state.update_namespace("args", {"key": "value"})
    workflow_state.mark_step_complete("step1", {"output": "result"})
    workflow_state.reset_state()

    assert workflow_state.metadata["execution_state"]["current_step"] == 0
    assert workflow_state.metadata["execution_state"]["completed_steps"] == []
    assert workflow_state.metadata["namespaces"] == {
        "args": {},
        "env": {},
        "steps": {},
        "batch": {}
    }


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
