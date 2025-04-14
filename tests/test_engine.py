import os
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import (
    InvalidFlowDefinitionError,
    StepNotInFlowError,
    WorkflowError,
)


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
