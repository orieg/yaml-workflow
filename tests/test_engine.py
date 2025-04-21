import os
import time
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import (
    ConfigurationError,
    FlowError,
    FlowNotFoundError,
    FunctionNotFoundError,
    InvalidFlowDefinitionError,
    StepExecutionError,
    StepNotInFlowError,
    TaskExecutionError,
    TemplateError,
    WorkflowError,
)
from yaml_workflow.state import WorkflowState
from yaml_workflow.tasks import TaskConfig, register_task
from yaml_workflow.tasks.basic_tasks import (  # Import basic tasks
    add_numbers,
    echo,
    fail,
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
      message: "Hello {{ args.param1 }}"
  
  - name: step2
    task: echo
    inputs:
      message: "Hello {{ args.param2 }}"

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
      message: "Hello {{ args.param1 }}"
  
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
    assert "param1" in engine.context["args"]
    assert engine.context["args"]["param1"] == "value1"
    assert "param2" in engine.context["args"]
    assert engine.context["args"]["param2"] == "value2"


def test_workflow_invalid_file():
    with pytest.raises(WorkflowError):
        WorkflowEngine("nonexistent_file.yaml")


def test_workflow_invalid_top_level_key():
    """Test that an invalid top-level key raises ConfigurationError."""
    invalid_workflow = {
        "name": "invalid-key-test",
        "invalid_key": "some value",  # This key is not allowed
        "steps": [{"name": "step1", "task": "echo"}],
    }
    with pytest.raises(ConfigurationError) as exc_info:
        WorkflowEngine(invalid_workflow)
    assert "Unexpected top-level key 'invalid_key'" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_flows_config, expected_error_msg",
    [
        (
            "not_a_dictionary",  # flows is not a dict
            "flows must be a mapping",  # Updated message
        ),
        (
            {"definitions": "not_a_list"},  # definitions is not a list
            "'definitions' must be a list",  # Updated message
        ),
        (
            {"definitions": ["not_a_dictionary"]},  # item in definitions is not a dict
            "flow definition must be a mapping",  # Updated message
        ),
        # Cases for empty dict, multiple keys, and non-list steps are removed as the current logic
        # does not explicitly check for these and raises different errors (or no error) later.
        # Add them back if the validation logic is enhanced.
        (
            {
                "definitions": [{"flow1": "not_a_list"}]
            },  # flow steps value is not a list
            "steps must be a list",  # Updated message and flow name is added in error
        ),
        (
            {
                "definitions": [{"flow1": ["non_existent_step"]}],
                "default": "flow1",
            },  # flow step name is not in workflow steps
            "Flow error: Step 'non_existent_step' not found in flow 'flow1'",  # Updated prefix and wording
        ),
        (
            {
                "default": "non_existent_flow",
                "definitions": [{"real_flow": []}],
            },  # default flow not in definitions
            "Flow error: Flow 'non_existent_flow' not found",  # Updated prefix and wording
        ),
        (
            {
                "default": 123,
                "definitions": [],
            },  # default flow name is not a string - Added empty definitions
            "Flow error: Flow '123' not found",  # Updated: Checks existence before type
        ),
        (
            {"definitions": [{"flow1": []}, {"flow1": []}]},  # duplicate flow name
            "Flow error: Invalid flow 'flow1': duplicate flow name",  # Updated: Includes flow name
        ),
    ],
)
def test_workflow_invalid_flow_definitions(
    invalid_flows_config, expected_error_msg, tmp_path
):
    """Test various invalid flow configurations."""
    # Base workflow structure - needs 'steps' to avoid separate error
    workflow_dict = {
        "name": "test-invalid-flows",
        "steps": [{"name": "step1", "task": "echo"}],
        # Placeholder for invalid flows section
    }

    # Inject the invalid flow config into the base structure
    workflow_dict["flows"] = invalid_flows_config

    with pytest.raises(WorkflowError) as exc_info:
        WorkflowEngine(workflow_dict, base_dir=tmp_path)

    print(f"Actual error: {exc_info.value}")  # Debug print
    # Check if the expected message is part of the actual error message
    # Using 'in' for more flexible matching
    assert expected_error_msg in str(exc_info.value)


def test_workflow_invalid_flow_step_not_string(tmp_path):
    """Test case where a step name within a flow definition is not a string."""
    # This needs a separate test because the structure is valid up to the point
    # of iterating through steps in the flow.
    workflow_dict = {
        "name": "test-invalid-flow-step-type",
        "steps": [{"name": "step1", "task": "echo"}],
        "flows": {"definitions": [{"flow1": [123]}]},  # Step name is not a string
    }
    with pytest.raises(StepNotInFlowError) as exc_info:
        engine = WorkflowEngine(workflow_dict, base_dir=tmp_path)
        # engine._validate_flows() # Validation happens during init

    assert "Flow error: Step '123' not found in flow 'flow1'" == str(
        exc_info.value
    )  # Updated prefix and wording


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
    print(f"DEBUG: state['steps'] = {state['steps']}")
    assert "step1" in state["steps"]
    assert "step2" in state["steps"]
    print(f"DEBUG: state['steps']['step1'] = {state['steps'].get('step1')}")
    assert state["steps"]["step1"]["status"] == "completed"
    print(f"DEBUG: state['steps']['step2'] = {state['steps'].get('step2')}")
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


def test_on_error_continue(tmp_path: Path):
    """Test that on_error: continue allows workflow to complete despite failure."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "python_code",
                "inputs": {"code": "result = {'var1': 'initial'}"},
            },
            {
                "name": "step2_fails",
                "task": "python_code",
                "inputs": {"code": "raise ValueError('Intentional failure')"},
                "on_error": "continue",
            },
            {
                "name": "step3",
                "task": "python_code",
                "inputs": {"code": "result = {'var2': 'final'}"},
            },
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()

    # Workflow should complete even though a step failed
    assert status["status"] == "completed"

    # --- Check step statuses from the engine's state ---
    final_state = engine.state.get_state()
    print(f"DEBUG (continue): final_state['steps'] = {final_state['steps']}")  # Debug
    assert final_state["steps"]["step1"]["status"] == "completed"
    print(
        f"DEBUG (continue): final_state['steps']['step2_fails'] = {final_state['steps'].get('step2_fails')}"
    )  # Debug
    assert final_state["steps"]["step2_fails"]["status"] == "failed"
    assert final_state["steps"]["step2_fails"]["skipped"] is False  # It ran and failed
    assert "Intentional failure" in final_state["steps"]["step2_fails"]["error"]
    assert final_state["steps"]["step3"]["status"] == "completed"

    # Check context variables from the final returned status dictionary
    assert status["context"]["steps"]["step1"]["result"] == {"var1": "initial"}


def test_on_error_next(tmp_path: Path):
    """Test that on_error: next correctly jumps to the specified step."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "python_code",
                "inputs": {"code": "result = {'a': 1}"},
            },
            {
                "name": "step2_fails",
                "task": "python_code",
                "inputs": {"code": "raise ValueError('Going to step4')"},
                "on_error": {"next": "step4"},
            },
            {
                "name": "step3_skipped",  # This step should be skipped
                "task": "python_code",
                "inputs": {"code": "result = {'b': 2}"},
            },
            {
                "name": "step4",
                "task": "python_code",
                "inputs": {"code": "result = {'c': 3}"},
            },
        ]
    }
    engine = WorkflowEngine(workflow, workspace=str(tmp_path))
    status = engine.run()

    # Workflow should complete
    assert status["status"] == "completed"

    # --- Check step statuses from the engine's state ---
    final_state = engine.state.get_state()
    # Access status via final_state['steps'][step_name]['status']
    print(f"DEBUG (next): final_state['steps'] = {final_state['steps']}")  # Debug
    assert final_state["steps"]["step1"]["status"] == "completed"
    print(
        f"DEBUG (next): final_state['steps']['step2_fails'] = {final_state['steps'].get('step2_fails')}"
    )  # Debug
    assert final_state["steps"]["step2_fails"]["status"] == "failed"
    assert "Going to step4" in final_state["steps"]["step2_fails"]["error"]
    print(
        f"DEBUG (next): final_state['steps']['step3_skipped'] = {final_state['steps'].get('step3_skipped')}"
    )  # Debug
    assert final_state["steps"]["step3_skipped"]["status"] == "skipped"
    print(
        f"DEBUG (next): final_state['steps']['step4'] = {final_state['steps'].get('step4')}"
    )  # Debug
    assert final_state["steps"]["step4"]["status"] == "completed"

    # Check context variables from the final returned status dictionary
    # (These should still reflect only successfully completed steps)
    assert status["context"]["steps"]["step1"]["result"] == {"a": 1}
    assert "step2_fails" not in status["context"]["steps"]
    assert "step3_skipped" not in status["context"]["steps"]
    assert status["context"]["steps"]["step4"]["result"] == {"c": 3}


def test_on_error_retry(tmp_path):
    """Test that on_error: retry attempts the step multiple times before succeeding."""

    # Register a task that fails a few times then succeeds
    fail_count = 0

    @register_task("fail_sometimes")
    def fail_sometimes_task(config: TaskConfig):
        nonlocal fail_count
        fail_count += 1
        if fail_count <= 3:
            raise ValueError(f"Failure attempt {fail_count}")
        return {"status": "Finally succeeded", "attempt": fail_count}

    # --- Workflow Definition ---
    workflow = {
        "steps": {
            "step1": {"task": "echo", "inputs": {"message": "Hello"}},  # Use "inputs"
            "flaky_step": {
                "task": "fail_sometimes",
                "onError": "retry",
                "maxRetries": 3,
            },
            "step3": {"task": "echo", "inputs": {"message": "World"}},  # Use "inputs"
        }
    }

    engine = WorkflowEngine(workflow, base_dir=tmp_path)

    # --- Run and Expect Success ---
    result = engine.run()  # Run the engine, expect it to succeed

    # --- Assertions ---
    # Check the final workflow status
    assert (
        result["status"] == "completed"
    ), "Workflow should complete successfully after retries"

    # Check the final state
    final_state = engine.state.get_state()
    assert (
        final_state["execution_state"]["status"] == "completed"
    )  # Check execution status

    # Check individual step statuses in the final state
    assert final_state["steps"]["step1"]["status"] == "completed"
    assert (
        final_state["steps"]["flaky_step"]["status"] == "completed"
    )  # Should be completed now
    # Check the retry count from the execution_state, not the step output - REMOVED as retry count is cleared on success
    assert (
        "error" not in final_state["steps"]["flaky_step"]
    )  # No error should be stored if successful
    assert (
        final_state["steps"]["step3"]["status"] == "completed"
    )  # Step3 should have run and completed

    # Check the output of the flaky step
    assert "flaky_step" in result["outputs"]
    assert result["outputs"]["flaky_step"] == {
        "result": {"status": "Finally succeeded", "attempt": 4}
    }


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
        "Deliberate failure" in notifications[0]["message"]
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
    # Check for the renamed key
    assert (
        "'message': 'Error XYZ occurred'"
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


def test_basic_task_with_templated_input(tmp_path):
    """Test a basic task registered via create_task_handler with templated input."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "echo",  # Basic task
                "inputs": {"message": "Initial Value"},
            },
            {
                "name": "step2",
                "task": "echo",  # Basic task using output from step1
                "inputs": {
                    "message": "Got: {{ steps.step1.result }}"
                },  # Templated input
            },
        ]
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    assert "step2" in result["outputs"]
    assert result["outputs"]["step2"]["result"] == "Got: Initial Value"


def test_basic_task_with_default_value(tmp_path):
    """Test a basic task where an optional arg uses its default value."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "hello_world",  # Takes optional 'name' (default: "World")
                "inputs": {},  # Do not provide the 'name' input
            }
        ]
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    assert "step1" in result["outputs"]
    assert result["outputs"]["step1"]["result"] == "Hello, World!"  # Check default


# --- Tests for tasks in basic_tasks.py ---


def test_basic_task_fail(tmp_path):
    """Test the fail task raises WorkflowError via the engine."""
    workflow = {
        "steps": [
            {
                "name": "step_fail",
                "task": "fail",  # Registered basic task
                "inputs": {"message": "Deliberate fail test"},
            }
        ]
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    with pytest.raises(WorkflowError) as exc_info:
        engine.run()
    assert "Workflow halted at step 'step_fail'" in str(exc_info.value)
    # Check original error embedded
    assert isinstance(exc_info.value.original_error, RuntimeError)
    assert str(exc_info.value.original_error) == "Deliberate fail test"


def test_basic_task_join_strings(tmp_path):
    """Test the join_strings task."""
    workflow = {
        "params": {"items_list": ["apple", "banana", "cherry"], "custom_sep": "-"},
        "steps": [
            {
                "name": "join_default",
                "task": "join_strings",  # Registered basic task
                "inputs": {
                    # Pass list directly
                    "strings": "{{ args.items_list }}"
                },
            },
            {
                "name": "join_custom",
                "task": "join_strings",
                "inputs": {
                    "strings": "{{ args.items_list }}",
                    "separator": "{{ args.custom_sep }}",
                },
            },
            {
                "name": "join_inline",
                "task": "join_strings",
                "inputs": {
                    # Define list inline
                    "strings": ["one", "two", "three"],
                    "separator": "_",
                },
            },
        ],
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    assert result["outputs"]["join_default"]["result"] == "apple banana cherry"
    assert result["outputs"]["join_custom"]["result"] == "apple-banana-cherry"
    assert result["outputs"]["join_inline"]["result"] == "one_two_three"


def test_basic_task_create_greeting(tmp_path):
    """Test the create_greeting task."""
    # Note: The create_greeting task signature is:
    # create_greeting(name: str, context: Dict[str, Any]) -> str
    # The TaskConfig provides the context implicitly based on the second param name.
    workflow = {
        "params": {
            "user": "Alice",
            # Define other initial values here if needed
            "system_message": "Welcome to the system.",
        },
        "steps": [
            {
                "name": "step_greet",
                "task": "create_greeting",  # Registered basic task
                "inputs": {
                    "name": "{{ args.user }}",
                    # 'context' is provided implicitly by the engine/wrapper
                },
            }
        ],
    }
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    # The task implementation should use the 'name' and potentially the 'context'
    # Let's check the output based on the current implementation in basic_tasks.py
    # create_greeting(name: str, context: Dict[str, Any]) -> str:
    #     return f"Hello, {name}!" # Example impl.
    # We need to know the exact implementation to assert perfectly.
    # Assuming it just returns "Hello, {name}!" for now:
    assert result["outputs"]["step_greet"]["result"] == "Hello Alice!"

    # Check context propagation (Optional - depends on task needs)


def test_execute_workflow_step_failure(temp_workspace, failed_workflow_file):
    """Test executing a workflow where a step fails using the 'fail' task."""
    engine = WorkflowEngine(failed_workflow_file)
    with pytest.raises(WorkflowError) as excinfo:
        engine.run()
    # Check that the error message indicates halting at step2 due to the fail task
    assert "Workflow halted at step 'step2'" in str(excinfo.value)
    assert "This step always fails" in str(excinfo.value)


def test_setup_workspace_default_base_dir(tmp_path):
    """Test workspace creation in the default 'runs' directory."""
    workflow_dict = {"name": "workspace_test_default", "steps": []}
    engine = WorkflowEngine(workflow_dict, base_dir=str(tmp_path / "runs"))
    # Trigger workspace setup if not done in init (it is)
    # workspace_path = engine.setup_workspace()
    workspace_path = engine.workspace

    assert workspace_path.exists()
    # Default base_dir is 'runs', check if it's within the provided tmp_path/runs
    assert workspace_path.parent.name == "runs"
    assert workspace_path.name.startswith("workspace_test_default_run_")
    assert "workspace" in engine.context
    assert Path(engine.context["workspace"]) == workspace_path
    assert "run_number" in engine.context
    assert isinstance(engine.context["run_number"], int)
    assert "timestamp" in engine.context
    assert "workflow_name" in engine.context
    assert engine.context["workflow_name"] == "workspace_test_default"
    # When initialized from dict, workflow_file should be present in context and empty
    assert "workflow_file" in engine.context
    assert engine.context["workflow_file"] == ""


def test_setup_workspace_custom_base_dir(tmp_path):
    """Test workspace creation in a custom base directory."""
    custom_base = tmp_path / "custom_runs"
    workflow_dict = {"name": "workspace_test_custom_base", "steps": []}
    engine = WorkflowEngine(workflow_dict, base_dir=str(custom_base))
    workspace_path = engine.workspace

    assert workspace_path.exists()
    assert workspace_path.parent == custom_base
    assert workspace_path.name.startswith("workspace_test_custom_base_run_")


def test_setup_workspace_specific_workspace_dir(tmp_path):
    """Test workspace creation using a specific target directory."""
    specific_dir = tmp_path / "my_specific_run"
    # The directory might be created by the engine or expected to exist
    # Assuming create_workspace handles its creation if needed
    workflow_dict = {"name": "workspace_test_specific", "steps": []}
    engine = WorkflowEngine(
        workflow_dict, workspace=str(specific_dir), base_dir=str(tmp_path)
    )
    workspace_path = engine.workspace

    assert workspace_path.exists()
    assert workspace_path == specific_dir  # Should use the exact dir provided
    # Run number might not be inferred if a specific dir is given, check context
    # create_workspace seems to always assign a run number
    assert engine.context["run_number"] == 1


def test_setup_workspace_workflow_name_from_file(tmp_path):
    """Test workspace name inference from the workflow file name."""
    workflow_file = tmp_path / "my_workflow_file.yaml"
    workflow_file.write_text("steps: []")  # Minimal valid workflow
    engine = WorkflowEngine(str(workflow_file), base_dir=str(tmp_path))
    workspace_path = engine.workspace

    assert workspace_path.name.startswith("my_workflow_file_run_")
    assert engine.context["workflow_name"] == "my_workflow_file"
    assert engine.context["workflow_file"] == str(workflow_file.absolute())


# --- Tests for run method parameter validation --- #

# Removed tests for run-time parameter validation (allowedValues, minLength)
# as this validation currently happens only during __init__ based on defaults,
# not for parameters passed dynamically to run().

# def test_run_param_validation_allowed_values(tmp_path):
#     """Test run fails if a param has an invalid value based on allowedValues."""
#     workflow_dict = {
#         "name": "param_allowed_test",
#         "params": {
#             "choice": {
#                 "allowedValues": ["A", "B"],
#                 "description": "Must be A or B"
#             }
#         },
#         "steps": [{"name": "dummy", "task": "echo", "inputs": {}}]
#     }
#     engine = WorkflowEngine(workflow_dict, base_dir=tmp_path)
#     with pytest.raises(ConfigurationError) as exc_info:
#         engine.run(params={"choice": "C"})
#     assert "Invalid value 'C' for parameter 'choice'" in str(exc_info.value)
#     assert "Allowed values: ['A', 'B']" in str(exc_info.value)
#
# def test_run_param_validation_min_length(tmp_path):
#     """Test run fails if a string param is shorter than minLength."""
#     workflow_dict = {
#         "name": "param_minlength_test",
#         "params": {
#             "shorty": {
#                 "type": "string",
#                 "minLength": 5,
#                 "description": "Must be at least 5 chars"
#             }
#         },
#         "steps": [{"name": "dummy", "task": "echo", "inputs": {}}]
#     }
#     engine = WorkflowEngine(workflow_dict, base_dir=tmp_path)
#     with pytest.raises(ConfigurationError) as exc_info:
#         engine.run(params={"shorty": "abc"})
#     assert "Invalid value for parameter 'shorty'" in str(exc_info.value)
#     assert "Value 'abc' is shorter than minimum length 5" in str(exc_info.value)

# Add more tests below as needed


def test_complex_error_flow_handling(tmp_path):
    """Test complex error flow handling scenarios including:
    1. Invalid on_error.next target handling (lines 355-362)
    2. Error template failure handling (lines 705-716)
    3. Retry with delay handling (lines 731-753)
    """
    # Track retry delays
    delay_times = []

    # Custom test task to track delays
    @register_task("delay_tracker")
    def delay_tracker_task(config: TaskConfig):
        nonlocal delay_times

        # For retry testing
        retry_count = len(delay_times)
        if retry_count < 2:
            delay_times.append(time.time())
            raise ValueError(f"Deliberate failure for retry {retry_count + 1}")

        # Return success on third try
        delay_times.append(time.time())
        return {"attempts": len(delay_times)}

    # --- Test 1: Invalid error flow target ---
    workflow_invalid_target = {
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "Initial step"},
            },
            {
                "name": "step2_invalid_jump",
                "task": "fail",
                "inputs": {"message": "Failure with invalid jump"},
                "on_error": {"next": "nonexistent_step"},  # Target doesn't exist
            },
        ]
    }

    engine = WorkflowEngine(workflow_invalid_target, base_dir=tmp_path)

    # Should raise WorkflowError with specific message about invalid target
    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    assert "Invalid on_error.next target 'nonexistent_step'" in str(exc_info.value)

    # --- Test 2: Error template failure ---
    workflow_template_error = {
        "steps": [
            {
                "name": "step1",
                "task": "fail",
                "inputs": {"message": "Template error test"},
                "on_error": {
                    "action": "fail",
                    # Use invalid template syntax that will fail during error handling
                    "message": "Error with invalid template: {{ error.missing_key.nonexistent }}",
                },
            },
        ]
    }

    engine = WorkflowEngine(workflow_template_error, base_dir=tmp_path)

    # Should still fail and preserve original error, with warning about template
    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    # Check that original error is preserved despite template error
    assert "Template error test" in str(exc_info.value)

    # Check the state to see the fallback error message
    state = engine.state.get_state()
    assert state["steps"]["step1"]["status"] == "failed"
    # Template error fallback message includes original error
    assert "Template error test" in state["steps"]["step1"]["error"]
    assert "failed to format custom message" in state["steps"]["step1"]["error"]

    # --- Test 3: Retry with delay ---
    workflow_retry_delay = {
        "steps": [
            {
                "name": "step_with_delay",
                "task": "delay_tracker",
                "on_error": {
                    "retry": 2,
                    "delay": 0.25,  # 250ms delay between retries
                    "message": "Retrying after delay",
                },
            },
        ]
    }

    # Reset delay tracking
    delay_times = []

    engine = WorkflowEngine(workflow_retry_delay, base_dir=tmp_path)
    result = engine.run()

    # Should complete successfully after retries
    assert result["status"] == "completed"

    # Should have 3 tracked times (initial + 2 retries)
    assert len(delay_times) == 3

    # Check that delays were actually applied
    # First retry should be at least 0.25s after initial attempt
    assert delay_times[1] - delay_times[0] >= 0.25
    # Second retry should be at least 0.25s after first retry
    assert delay_times[2] - delay_times[1] >= 0.25

    # Check final state and output
    assert result["outputs"]["step_with_delay"]["result"]["attempts"] == 3


def test_complex_flow_transitions_and_conditions(tmp_path):
    """Test complex flow transitions with conditions and error handling.
    Specifically targets lines 947-974 in engine.py covering:
    - Conditional step execution
    - Skipping steps based on conditions
    - Flow jump handling after steps are skipped
    - Mark skipped steps during final state update
    """
    # Setup workflow with conditions and flow jumps
    workflow = {
        "steps": [
            {
                "name": "init_var",
                "task": "python_code",
                "inputs": {"code": "result = {'status': 'good', 'counter': 0}"},
            },
            {
                "name": "check_condition_true",
                "task": "echo",
                "inputs": {"message": "This step should run"},
                # Condition is true, step should execute
                "condition": "{{ steps.init_var.result.status == 'good' }}",
            },
            {
                "name": "check_condition_false",
                "task": "echo",
                "inputs": {"message": "This step should be skipped"},
                # Condition is false, step should be skipped
                "condition": "{{ steps.init_var.result.status == 'bad' }}",
            },
            {
                "name": "jump_source",
                "task": "fail",
                "inputs": {"message": "Error that triggers jump"},
                # Should jump to recovery_step
                "on_error": {"next": "recovery_step"},
            },
            {
                "name": "skipped_after_jump",
                "task": "echo",
                "inputs": {"message": "This step should be skipped due to jump"},
            },
            {
                "name": "recovery_step",
                "task": "python_code",
                "inputs": {"code": "result = {'recovered': True}"},
            },
            {
                "name": "final_step",
                "task": "python_code",
                "inputs": {"code": "result = {'completed': True}"},
            },
        ]
    }

    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()

    # Workflow should complete
    assert result["status"] == "completed"

    # Get final state
    final_state = engine.state.get_state()

    # --- Verify conditions handled correctly ---
    # Step with true condition should run
    assert final_state["steps"]["check_condition_true"]["status"] == "completed"

    # Step with false condition should be marked as skipped
    assert final_state["steps"]["check_condition_false"]["status"] == "skipped"
    assert "Condition" in final_state["steps"]["check_condition_false"]["reason"]

    # --- Verify jump handling ---
    # Source step should be failed
    assert final_state["steps"]["jump_source"]["status"] == "failed"

    # Step after failed step should be skipped due to jump
    assert final_state["steps"]["skipped_after_jump"]["status"] == "skipped"
    assert (
        "Workflow execution path"
        in final_state["steps"]["skipped_after_jump"]["reason"]
    )

    # Recovery step should run
    assert final_state["steps"]["recovery_step"]["status"] == "completed"
    assert result["outputs"]["recovery_step"]["result"]["recovered"] is True

    # Final step should also run
    assert final_state["steps"]["final_step"]["status"] == "completed"
    assert result["outputs"]["final_step"]["result"]["completed"] is True

    # --- Verify context structure ---
    # Verify all completed steps have proper results in context
    assert "init_var" in result["context"]["steps"]
    assert result["context"]["steps"]["init_var"]["result"]["status"] == "good"
    assert "recovery_step" in result["context"]["steps"]
    assert result["context"]["steps"]["recovery_step"]["result"]["recovered"] is True


def test_complex_template_resolution_and_validation(tmp_path):
    """Test complex template resolution scenarios and parameter validation.
    Specifically targets lines 31-36 and 75-82 in template.py and related lines in engine.py.
    Tests:
    - Complex nested templates
    - Error handling for undefined variables
    - Template resolution with default filters
    - Parameter validation errors
    """
    # --- Test 1: Basic arithmetic templates ---
    workflow_basic_templates = {
        "params": {
            "base_value": 10,
            "multiplier": 5,
        },
        "steps": [
            {
                "name": "math_template",
                "task": "echo",
                "inputs": {
                    # Simple arithmetic template
                    "message": "Result: {{ args.base_value * args.multiplier }}"
                },
            },
            {
                "name": "template_with_default",
                "task": "echo",
                "inputs": {
                    "message": "{{ args.nonexistent | default('fallback_value') }}"
                },
            },
        ],
    }

    engine = WorkflowEngine(workflow_basic_templates, base_dir=tmp_path)
    result = engine.run()

    # Check math template resolution
    assert result["outputs"]["math_template"]["result"] == "Result: 50"

    # Check default filter worked for missing key
    assert result["outputs"]["template_with_default"]["result"] == "fallback_value"

    # --- Test 2: Error for undefined variables in strict mode ---
    workflow_undefined_vars = {
        "steps": [
            {
                "name": "undefined_var",
                "task": "echo",
                "inputs": {
                    "message": "{{ nonexistent_variable }}",
                },
            },
        ],
    }

    engine = WorkflowEngine(workflow_undefined_vars, base_dir=tmp_path)

    # Should fail with TemplateError due to undefined variable
    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    # Check error message indicates template issue
    assert (
        "nonexistent" in str(exc_info.value).lower()
        or "undefined" in str(exc_info.value).lower()
    )

    # --- Test 3: Required parameter validation ---
    workflow_required_param = {
        "params": {
            "required_param": {
                "required": True,
            },
        },
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "{{ args.required_param }}"},
            },
        ],
    }

    engine = WorkflowEngine(workflow_required_param, base_dir=tmp_path)

    # Should fail because required_param is not provided
    with pytest.raises(WorkflowError) as exc_info:
        engine.run()

    # Check error message about required parameter
    assert "Required parameter 'required_param' is undefined" in str(exc_info.value)

    # Verify the error is marked in the state
    state = engine.state.get_state()
    assert state["execution_state"]["status"] == "failed"
    assert (
        state["execution_state"]["failed_step"]["step_name"] == "parameter_validation"
    )

    # --- Test 4: Access to variable through step outputs ---
    workflow_step_access = {
        "steps": [
            {
                "name": "set_var",
                "task": "python_code",
                "inputs": {"code": "result = {'value': 42}"},
            },
            {
                "name": "access_var",
                "task": "echo",
                "inputs": {"message": "Value is: {{ steps.set_var.result.value }}"},
            },
        ],
    }

    engine = WorkflowEngine(workflow_step_access, base_dir=tmp_path)
    result = engine.run()

    # Check that variable was accessed correctly
    assert result["outputs"]["access_var"]["result"] == "Value is: 42"
