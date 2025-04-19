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
from yaml_workflow.tasks import TaskConfig, register_task


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

    # Check the final WorkflowError message (might differ slightly due to root cause propagation)
    assert "Workflow halted at step 'step1'" in str(exc_info.value)
    assert "Deliberate failure" in str(exc_info.value)
    # *** Check the original_error attribute directly ***
    assert isinstance(exc_info.value.original_error, RuntimeError)
    assert str(exc_info.value.original_error) == "Deliberate failure"

    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "failed"
    assert state["execution_state"]["failed_step"]["step_name"] == "step1"
    # Check the error message stored in the state (this should be the formatted one)
    assert state["execution_state"]["failed_step"]["error"] == "Custom error message"


def test_on_error_continue(tmp_path):
    """Test on_error with continue action."""
    workflow = {
        "name": "on-error-continue-test",
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "Step 1 Result"},
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
                "inputs": {"message": "Step 3 Result"},
            },
        ],
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()

    assert (
        result["status"] == "completed"
    ), "Workflow should complete despite step failure"

    # Check final outputs in the result dictionary
    assert "step1" in result["outputs"], "Step 1 output should be present"
    assert result["outputs"]["step1"] == {"result": "Step 1 Result"}
    assert (
        "step2" not in result["outputs"]
    ), "Failed step 2 output should NOT be present"
    assert "step3" in result["outputs"], "Step 3 output should be present"
    assert result["outputs"]["step3"] == {"result": "Step 3 Result"}

    # Check the detailed execution state
    state = engine.state.metadata["execution_state"]
    assert state["status"] == "completed", "Internal state status should be completed"
    assert "step1" in state["step_outputs"]
    # *** Step 2 failed, so its output should NOT be in step_outputs ***
    assert (
        "step2" not in state["step_outputs"]
    ), "Failed step output should not be in state outputs"
    assert "step3" in state["step_outputs"]
    # Check step status (this is tracked separately from outputs)
    # We need a way to get individual step status reliably from state.
    # For now, let's assume the steps_status structure exists or adapt if needed.
    # Placeholder: Assuming get_state() provides this structure or similar.
    full_state = engine.state.get_state()  # Use get_state() which calculates status
    assert full_state["steps"]["step1"]["status"] == "completed"
    assert (
        full_state["steps"]["step2"]["status"] == "failed"
    ), "Step 2 status should be failed"
    assert full_state["steps"]["step3"]["status"] == "completed"
    # *** Since action is 'continue', the workflow completes, but the step *is* marked failed internally ***
    # assert state["failed_step"] is None, "No step should be marked as the final failure point"
    assert (
        state["failed_step"] is not None
    ), "failed_step should be recorded even on continue"
    assert (
        state["failed_step"]["step_name"] == "step2"
    ), "Step 2 should be the recorded failed step"
    assert (
        state["failed_step"]["error"] == "Skipping failed step"
    ), "State should record the formatted error msg"


def test_on_error_retry(tmp_path):
    """Test on_error with retry action."""
    attempts = []

    @register_task("flaky")
    def flaky_task(config: TaskConfig):
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
    """Test on_error with notify action and error flow jump."""
    notifications = []

    @register_task("notify")
    def notify_task(config: TaskConfig):
        # Ensure error context exists before accessing
        error_context = config._context.get("error")
        assert error_context is not None, "Error context should exist in notify task"
        notifications.append(error_context)
        return {"notified": True}

    workflow = {
        "steps": [
            {
                "name": "failing_step",
                "task": "fail",
                "inputs": {"message": "Deliberate failure"},
                "on_error": {
                    "action": "notify",  # Action could also be 'fail' if we just want the jump
                    "message": "Step failed: {{ error }}",  # Formatted message for state/logs
                    "next": "notification",  # Jump target
                },
            },
            {
                "name": "notification",
                "task": "notify",
                # This step runs *after* the error context is set
            },
            {
                "name": "final_step_after_notify",
                "task": "echo",
                "inputs": {"message": "After notification"},
                # This step should also run if notify doesn't halt
            },
        ]
    }
    engine = WorkflowEngine(workflow)

    # The workflow should *complete* successfully after jumping to the notification step
    result = engine.run()

    assert result["status"] == "completed", "Workflow should complete after error jump"
    assert len(notifications) == 1, "Notification task should have been called once"
    assert (
        notifications[0]["step"] == "failing_step"
    ), "Error context should record the failing step"
    assert (
        "Deliberate failure" in notifications[0]["error"]
    ), "Error context should contain original error message"
    # Check that the final step also ran
    assert (
        "final_step_after_notify" in result["outputs"]
    ), "Steps after error jump should execute"


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
                    # The {{ error }} template now resolves to the error context dict
                    "message": "Task failed with context: {{ error }}",
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow)

    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    # Check the final WorkflowError message
    assert "Workflow halted at step 'step1'" in str(exc_info.value)
    assert "Error XYZ occurred" in str(
        exc_info.value
    )  # Root cause should be in the message
    # *** Check the original_error attribute ***
    assert isinstance(exc_info.value.original_error, RuntimeError)
    assert str(exc_info.value.original_error) == "Error XYZ occurred"

    state = engine.state.get_state()
    # *** Check the formatted error message stored in the state ***
    expected_state_error = "Task failed with context: {'step': 'step1', 'error': 'Error XYZ occurred', 'raw_error': RuntimeError('Error XYZ occurred')}"
    # Note: Comparing dicts as strings can be fragile, but sufficient here
    # A more robust check might parse the string back to a dict or check keys/values
    # For now, compare the start of the string representation
    assert state["execution_state"]["failed_step"]["error"].startswith(
        "Task failed with context: {'step': 'step1'"
    )
    assert (
        "'error': 'Error XYZ occurred'"
        in state["execution_state"]["failed_step"]["error"]
    )


def test_step_output_namespace(tmp_path):
    """Test that step outputs are correctly placed in the steps namespace."""
    workflow_dict = {
        "name": "test-steps-namespace",
        "steps": [
            {
                "name": "echo_step",
                "task": "echo",
                "inputs": {"message": "Echo Output"},
            },
            {
                "name": "shell_step",
                "task": "shell",
                "inputs": {"command": "printf 'Shell Output'"},
            },
            {
                "name": "check_outputs",
                "task": "echo",
                "inputs": {
                    "message": "Echo:{{ steps.echo_step.result }} Shell:{{ steps.shell_step.result.stdout }}"
                },
            },
        ],
    }
    engine = WorkflowEngine(workflow_dict, base_dir=tmp_path)
    result = engine.run()

    assert result["status"] == "completed"

    # Check final context
    final_context = engine.context
    assert "steps" in final_context
    assert "echo_step" in final_context["steps"]
    assert final_context["steps"]["echo_step"] == {"result": "Echo Output"}

    assert "shell_step" in final_context["steps"]
    shell_step_output_container = final_context["steps"]["shell_step"]
    print(f"DEBUG: shell_step output container = {shell_step_output_container}")
    assert (
        "result" in shell_step_output_container
    ), "'result' key missing from shell_step output container"
    shell_step_result = shell_step_output_container["result"]
    assert isinstance(shell_step_result, dict), "shell_step result should be a dict"
    assert (
        shell_step_result.get("stdout") == "Shell Output"
    ), f"Unexpected stdout: {shell_step_result.get('stdout')}"
    assert (
        "return_code" in shell_step_result
    ), "return_code key missing from shell_step result dict"
    assert (
        shell_step_result.get("return_code") == 0
    ), f"Unexpected return code: {shell_step_result.get('return_code')}"

    # Check final step output which used the previous steps' outputs
    assert "check_outputs" in final_context["steps"]
    # The output message should be the same as the template resolved correctly
    expected_message = "Echo:Echo Output Shell:Shell Output"
    assert final_context["steps"]["check_outputs"] == {
        "result": expected_message
    }, f"Unexpected check_outputs result: {final_context['steps']['check_outputs']}"

    # Check final returned outputs dict
    final_outputs = result["outputs"]
    assert final_outputs["echo_step"] == {"result": "Echo Output"}
    # Check the nested structure for shell_step in final_outputs
    assert "shell_step" in final_outputs
    assert "result" in final_outputs["shell_step"]
    assert final_outputs["shell_step"]["result"]["stdout"] == "Shell Output"
    assert final_outputs["check_outputs"] == {
        "result": expected_message
    }, f"Unexpected check_outputs in final_outputs: {final_outputs.get('check_outputs')}"
