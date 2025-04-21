import copy  # Import copy
import logging
import os  # Import os
import time
from pathlib import Path

import pytest
import yaml

from yaml_workflow.runner import find_latest_log, run_workflow

# Disable root logger propagation during tests to avoid interference
# logging.getLogger().propagate = False


@pytest.fixture
def simple_workflow_content():
    return {
        "name": "Simple Test Workflow",
        "steps": [
            {
                "name": "step_0_mkdir",
                "task": "shell",
                "inputs": {"command": "mkdir -p output/"},
            },
            {
                "name": "step_1",
                "task": "shell",
                "inputs": {"command": "echo 'Hello from Step 1'"},
            },
            {
                "name": "step_2",
                "task": "shell",
                "inputs": {
                    "command": "echo 'Hello from Step 2' > output/step2_output.txt"
                },
            },
        ],
    }


@pytest.fixture
def temp_workflow_file(tmp_path, simple_workflow_content):
    workflow_file = tmp_path / "test_workflow.yaml"
    with open(workflow_file, "w") as f:
        yaml.dump(simple_workflow_content, f)
    return workflow_file


@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "test_workspace"
    # run_workflow creates the directory, no need to mkdir here
    return workspace


@pytest.fixture
def workflow_with_template_error():
    return {
        "name": "Template Error Workflow",
        "steps": [
            {
                "name": "setup",
                "task": "shell",
                "inputs": {"command": "echo 'Setup complete' > output/setup.txt"},
            },
            {
                "name": "template_fail",
                "task": "shell",
                "inputs": {
                    # This will cause TemplateError because 'undefined_var' is not defined
                    "command": "echo '{{ undefined_var }}'"
                },
                # No on_error specified, should default to abort
            },
            {
                "name": "should_not_run",
                "task": "shell",
                "inputs": {
                    "command": "echo 'This should not have executed' > output/should_not_run.txt"
                },
            },
        ],
    }


@pytest.fixture
def workflow_with_template_error_continue(workflow_with_template_error):
    # Request the base fixture as an argument
    # Deep copy to avoid modifying the original fixture dict
    content = copy.deepcopy(workflow_with_template_error)
    # Find the failing step and add on_error: continue
    for step in content["steps"]:
        if step["name"] == "template_fail":
            step["on_error"] = "continue"  # Simple continue string is supported
            break
    return content


@pytest.fixture
def workflow_with_exec_error():
    return {
        "name": "Execution Error Workflow",
        "steps": [
            {
                "name": "setup",
                "task": "shell",
                "inputs": {"command": "echo 'Setup complete' > output/setup.txt"},
            },
            {
                "name": "exec_fail",
                "task": "shell",
                "inputs": {
                    # This will cause TaskExecutionError via CalledProcessError
                    "command": "exit 1"
                },
                # No on_error specified, should default to abort
            },
            {
                "name": "should_not_run_exec",
                "task": "shell",
                "inputs": {
                    "command": "echo 'This should not have executed' > output/should_not_run_exec.txt"
                },
            },
        ],
    }


@pytest.fixture
def workflow_with_exec_error_continue(workflow_with_exec_error):
    # Request the base fixture as an argument
    content = copy.deepcopy(workflow_with_exec_error)
    # Find the failing step and add on_error: continue
    for step in content["steps"]:
        if step["name"] == "exec_fail":
            step["on_error"] = "continue"
            break
    return content


@pytest.fixture
def workflow_with_condition():
    return {
        "name": "Conditional Step Workflow",
        "steps": [
            {
                "name": "setup_flag",
                "task": "echo",  # Use echo to easily set a result
                "inputs": {"message": "false"},  # The result will be the string "false"
            },
            {
                "name": "conditional_step",
                "task": "shell",
                "inputs": {
                    "command": "echo 'Conditional step ran!' > output/conditional.txt"
                },
                # This condition checks the string result of the previous step
                "condition": "{{ steps.setup_flag.result == 'true' }}",  # Should evaluate to false
            },
            {
                "name": "final_step",
                "task": "shell",
                "inputs": {"command": "echo 'Final step ran' > output/final.txt"},
            },
        ],
    }


def test_run_workflow_success(temp_workflow_file, temp_workspace):
    """Test a basic successful workflow run."""
    args = {"test_arg": "value"}
    output_dir = temp_workspace / "custom_output"  # Test custom output dir

    result = run_workflow(
        workflow_file=temp_workflow_file,
        args=args,
        workspace_dir=temp_workspace,
        output_dir=output_dir,
    )

    # Print result if failed for debugging
    if not result["success"]:
        print(f"Workflow failed. Result:\n{result}")

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    # Check directories were created
    assert temp_workspace.is_dir()
    assert output_dir.is_dir()
    log_dir = temp_workspace / "logs"
    assert log_dir.is_dir()

    # Check log file was created
    log_files = list(log_dir.glob("workflow_*.log"))
    assert len(log_files) == 1
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    assert latest_log == log_files[0]
    log_content = latest_log.read_text()
    assert "Starting workflow" in log_content
    assert "Running Step: step_1" in log_content
    assert "Running Step: step_2" in log_content
    assert "Workflow finished successfully" in log_content
    assert f"Arguments: {args}" in log_content  # Check args logging

    # Check output file from step 2 was created in the correct output dir
    step2_output_file = temp_workspace / "output" / "step2_output.txt"
    assert step2_output_file.exists()
    assert step2_output_file.read_text().strip() == "Hello from Step 2"


def test_run_workflow_file_not_found(tmp_path):
    """Test running a workflow with a non-existent file."""
    non_existent_file = tmp_path / "non_existent.yaml"
    workspace_dir = (
        tmp_path / "workspace_nf"
    )  # Use a path, but don't expect it to be created

    result = run_workflow(workflow_file=non_existent_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert f"Workflow file not found: {non_existent_file}" in result["message"]
    assert result["stdout"] == ""
    assert result["stderr"] == ""

    # # Workspace should NOT be created if workflow file not found
    # assert not workspace_dir.exists() # Explicitly check it doesn't exist
    # assert workspace_dir.is_dir() # REMOVED
    # assert (workspace_dir / "logs").is_dir() # REMOVED
    # assert (workspace_dir / "output").is_dir() # REMOVED


def test_find_latest_log(tmp_path):
    """Test the find_latest_log helper function."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # No logs
    assert find_latest_log(log_dir) is None

    # Create some log files
    log1 = log_dir / "workflow_20230101_100000_000000.log"
    log2 = log_dir / "workflow_20230101_110000_000000.log"  # Target: Latest
    log3 = log_dir / "workflow_20230101_090000_000000.log"
    other_file = log_dir / "other.txt"

    # Create files with potentially close modification times initially
    start_time = time.time()
    log1.touch()
    log2.touch()
    log3.touch()
    other_file.touch()

    # Explicitly set modification times to ensure log2 is latest
    # Use timestamps slightly apart to avoid filesystem resolution issues
    os.utime(log3, (start_time - 2, start_time - 2))  # Oldest
    os.utime(log1, (start_time - 1, start_time - 1))  # Middle
    os.utime(log2, (start_time, start_time))  # Newest

    latest = find_latest_log(log_dir)
    assert latest is not None
    assert latest.name == log2.name  # Should now correctly find log2

    # Test with empty dir again
    for item in log_dir.iterdir():
        item.unlink()
    assert find_latest_log(log_dir) is None


def test_run_workflow_invalid_yaml(tmp_path):
    """Test running a workflow with invalid YAML content."""
    invalid_yaml_content = "name: Invalid Workflow\nsteps: [ { name: step1, task: shell inputs: { command: echo hello } } ]"  # Missing colon after inputs
    workflow_file = tmp_path / "invalid_workflow.yaml"
    workflow_file.write_text(invalid_yaml_content)
    workspace_dir = tmp_path / "workspace_invalid_yaml"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error loading workflow file" in result["message"]
    assert "while parsing a flow mapping" in result["message"]
    assert result["stdout"] == ""
    # Workspace and logs SHOULD be created even on YAML load error for logging
    assert workspace_dir.exists()
    assert (workspace_dir / "logs").exists()
    # assert not workspace_dir.exists() # Workspace should not be created on YAML load error


def test_run_workflow_template_error_abort(tmp_path, workflow_with_template_error):
    """Test workflow aborts on TemplateError by default."""
    workflow_file = tmp_path / "template_error_abort.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_template_error))
    workspace_dir = tmp_path / "workspace_template_abort"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error in step 'template_fail'" in result["message"]
    assert "Template error:" in result["message"]
    assert (
        "undefined_var" in result["message"]
    )  # Check if the variable name is mentioned

    # Check that setup step ran, but the later step did not
    assert (workspace_dir / "output" / "setup.txt").exists()
    assert not (workspace_dir / "output" / "should_not_run.txt").exists()

    # Check logs for error message
    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Template error in step 'template_fail'" in log_content
    assert "Workflow aborted due to error in step 'template_fail'" in log_content


def test_run_workflow_template_error_continue(
    tmp_path, workflow_with_template_error_continue
):
    """Test workflow continues on TemplateError with on_error: continue."""
    workflow_file = tmp_path / "template_error_continue.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_template_error_continue))
    workspace_dir = tmp_path / "workspace_template_continue"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    # Workflow should report success because the error was handled by continuing
    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    # Check that setup step ran AND the later step also ran
    assert (workspace_dir / "output" / "setup.txt").exists()
    assert (workspace_dir / "output" / "should_not_run.txt").exists()
    assert (
        workspace_dir / "output" / "should_not_run.txt"
    ).read_text().strip() == "This should not have executed"

    # Check logs for warning message about handled error
    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Template error in step 'template_fail'" in log_content
    assert "Step 'template_fail' failed but workflow continues:" in log_content
    assert "Running Step: should_not_run" in log_content  # Verify next step ran
    assert "Workflow finished successfully" in log_content


def test_run_workflow_exec_error_abort(tmp_path, workflow_with_exec_error):
    """Test workflow aborts on ExecutionError by default."""
    workflow_file = tmp_path / "exec_error_abort.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_exec_error))
    workspace_dir = tmp_path / "workspace_exec_abort"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error in step 'exec_fail'" in result["message"]
    # Check for specific execution error details in the message
    assert "returned non-zero exit status 1" in result["message"]

    # Check that setup step ran, but the later step did not
    assert (workspace_dir / "output" / "setup.txt").exists()
    assert not (workspace_dir / "output" / "should_not_run_exec.txt").exists()

    # Check logs for error message
    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Error executing step 'exec_fail'" in log_content
    assert "CalledProcessError" in log_content  # Underlying error type
    assert "Workflow aborted due to error in step 'exec_fail'" in log_content


def test_run_workflow_exec_error_continue(tmp_path, workflow_with_exec_error_continue):
    """Test workflow continues on ExecutionError with on_error: continue."""
    workflow_file = tmp_path / "exec_error_continue.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_exec_error_continue))
    workspace_dir = tmp_path / "workspace_exec_continue"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    # Workflow should report success because the error was handled by continuing
    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    # Check that setup step ran AND the later step also ran
    assert (workspace_dir / "output" / "setup.txt").exists()
    assert (workspace_dir / "output" / "should_not_run_exec.txt").exists()
    assert (
        workspace_dir / "output" / "should_not_run_exec.txt"
    ).read_text().strip() == "This should not have executed"

    # Check logs for warning message about handled error
    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Error executing step 'exec_fail'" in log_content
    assert "CalledProcessError" in log_content  # Underlying error type
    assert "Step 'exec_fail' failed but workflow continues:" in log_content
    assert "Running Step: should_not_run_exec" in log_content  # Verify next step ran
    assert "Workflow finished successfully" in log_content


def test_run_workflow_step_skip_condition(tmp_path, workflow_with_condition):
    """Test that a step is skipped if its condition is false."""
    workflow_file = tmp_path / "conditional_workflow.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_condition))
    workspace_dir = tmp_path / "workspace_conditional"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    # Check that the conditional step's output file does NOT exist
    assert not (workspace_dir / "output" / "conditional.txt").exists()

    # Check that the final step's output file DOES exist
    final_output_file = workspace_dir / "output" / "final.txt"
    assert final_output_file.exists()
    assert final_output_file.read_text().strip() == "Final step ran"

    # Check logs for skipping message and final step execution
    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Skipping step: conditional_step due to condition." in log_content
    assert "Running Step: final_step" in log_content
    assert "Workflow finished successfully" in log_content


# TODO: Add tests for:
# - Invalid YAML format
# - TemplateError handling (continue/abort)
# - Task ExecutionError handling (continue/abort)
# - Step skipping due to condition
# - Default workspace/output dir usage
# - Capture stderr
# - Workflow with no steps
# - Interaction with config_file (if implemented)
