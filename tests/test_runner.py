import copy
import logging
import os
import time
from pathlib import Path

import pytest
import yaml

from yaml_workflow.runner import find_latest_log, run_workflow


@pytest.fixture
def simple_workflow_content():
    return {
        "name": "Simple Test Workflow",
        "steps": [
            {
                "name": "step_0_setup",
                "task": "python_code",
                "inputs": {
                    "code": "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); result='setup done'"
                },
            },
            {
                "name": "step_1",
                "task": "echo",
                "inputs": {"message": "Hello from Step 1"},
            },
            {
                "name": "step_2",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'step2_output.txt'), 'w').write('Hello from Step 2'); "
                        "result='step 2 done'"
                    )
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
    return workspace


@pytest.fixture
def workflow_with_template_error():
    return {
        "name": "Template Error Workflow",
        "steps": [
            {
                "name": "setup",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'setup.txt'), 'w').write('Setup complete'); "
                        "result='setup done'"
                    )
                },
            },
            {
                "name": "template_fail",
                "task": "echo",
                "inputs": {
                    # This will cause TemplateError because 'undefined_var' is not defined
                    "message": "{{ undefined_var }}"
                },
            },
            {
                "name": "should_not_run",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'should_not_run.txt'), 'w').write('This should not have executed'); "
                        "result='ran'"
                    )
                },
            },
        ],
    }


@pytest.fixture
def workflow_with_template_error_continue(workflow_with_template_error):
    content = copy.deepcopy(workflow_with_template_error)
    for step in content["steps"]:
        if step["name"] == "template_fail":
            step["on_error"] = "continue"
            break
    return content


@pytest.fixture
def workflow_with_exec_error():
    return {
        "name": "Execution Error Workflow",
        "steps": [
            {
                "name": "setup",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'setup.txt'), 'w').write('Setup complete'); "
                        "result='setup done'"
                    )
                },
            },
            {
                "name": "exec_fail",
                "task": "python_code",
                "inputs": {"code": "raise RuntimeError('Deliberate failure')"},
            },
            {
                "name": "should_not_run_exec",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'should_not_run_exec.txt'), 'w').write('This should not have executed'); "
                        "result='ran'"
                    )
                },
            },
        ],
    }


@pytest.fixture
def workflow_with_exec_error_continue(workflow_with_exec_error):
    content = copy.deepcopy(workflow_with_exec_error)
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
                "task": "echo",
                "inputs": {"message": "false"},
            },
            {
                "name": "conditional_step",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'conditional.txt'), 'w').write('Conditional step ran!'); "
                        "result='ran'"
                    )
                },
                "condition": "{{ steps.setup_flag.result == 'true' }}",
            },
            {
                "name": "final_step",
                "task": "python_code",
                "inputs": {
                    "code": (
                        "import os; d=os.path.join(context['workspace'],'output'); os.makedirs(d, exist_ok=True); "
                        "open(os.path.join(d,'final.txt'), 'w').write('Final step ran'); "
                        "result='final done'"
                    )
                },
            },
        ],
    }


def test_run_workflow_success(temp_workflow_file, temp_workspace):
    """Test a basic successful workflow run."""
    args = {"test_arg": "value"}
    output_dir = temp_workspace / "custom_output"

    result = run_workflow(
        workflow_file=temp_workflow_file,
        args=args,
        workspace_dir=temp_workspace,
        output_dir=output_dir,
    )

    if not result["success"]:
        print(f"Workflow failed. Result:\n{result}")

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    assert temp_workspace.is_dir()
    assert output_dir.is_dir()
    log_dir = temp_workspace / "logs"
    assert log_dir.is_dir()

    log_files = list(log_dir.glob("workflow_*.log"))
    assert len(log_files) == 1
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    assert latest_log == log_files[0]
    log_content = latest_log.read_text()
    assert "Starting workflow" in log_content
    assert "Workflow finished successfully" in log_content

    step2_output_file = temp_workspace / "output" / "step2_output.txt"
    assert step2_output_file.exists()
    assert step2_output_file.read_text().strip() == "Hello from Step 2"


def test_run_workflow_file_not_found(tmp_path):
    """Test running a workflow with a non-existent file."""
    non_existent_file = tmp_path / "non_existent.yaml"
    workspace_dir = tmp_path / "workspace_nf"

    result = run_workflow(workflow_file=non_existent_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert f"Workflow file not found: {non_existent_file}" in result["message"]
    assert result["stdout"] == ""
    assert result["stderr"] == ""


def test_find_latest_log(tmp_path):
    """Test the find_latest_log helper function."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    assert find_latest_log(log_dir) is None

    log1 = log_dir / "workflow_20230101_100000_000000.log"
    log2 = log_dir / "workflow_20230101_110000_000000.log"
    log3 = log_dir / "workflow_20230101_090000_000000.log"
    other_file = log_dir / "other.txt"

    start_time = time.time()
    log1.touch()
    log2.touch()
    log3.touch()
    other_file.touch()

    os.utime(log3, (start_time - 2, start_time - 2))
    os.utime(log1, (start_time - 1, start_time - 1))
    os.utime(log2, (start_time, start_time))

    latest = find_latest_log(log_dir)
    assert latest is not None
    assert latest.name == log2.name

    for item in log_dir.iterdir():
        item.unlink()
    assert find_latest_log(log_dir) is None


def test_run_workflow_invalid_yaml(tmp_path):
    """Test running a workflow with invalid YAML content."""
    invalid_yaml_content = "name: Invalid Workflow\nsteps: [ { name: step1, task: shell inputs: { command: echo hello } } ]"
    workflow_file = tmp_path / "invalid_workflow.yaml"
    workflow_file.write_text(invalid_yaml_content)
    workspace_dir = tmp_path / "workspace_invalid_yaml"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error loading workflow file" in result["message"]
    assert "while parsing a flow mapping" in result["message"]
    assert result["stdout"] == ""
    assert workspace_dir.exists()
    assert (workspace_dir / "logs").exists()


def test_run_workflow_template_error_abort(tmp_path, workflow_with_template_error):
    """Test workflow aborts on TemplateError by default."""
    workflow_file = tmp_path / "template_error_abort.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_template_error))
    workspace_dir = tmp_path / "workspace_template_abort"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error in step 'template_fail'" in result["message"]
    assert "undefined_var" in result["message"]

    assert (workspace_dir / "output" / "setup.txt").exists()
    assert not (workspace_dir / "output" / "should_not_run.txt").exists()

    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "template_fail" in log_content
    assert "Workflow aborted due to error in step 'template_fail'" in log_content


def test_run_workflow_template_error_continue(
    tmp_path, workflow_with_template_error_continue
):
    """Test workflow continues on TemplateError with on_error: continue."""
    workflow_file = tmp_path / "template_error_continue.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_template_error_continue))
    workspace_dir = tmp_path / "workspace_template_continue"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    assert (workspace_dir / "output" / "setup.txt").exists()
    assert (workspace_dir / "output" / "should_not_run.txt").exists()
    assert (
        workspace_dir / "output" / "should_not_run.txt"
    ).read_text().strip() == "This should not have executed"

    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "template_fail" in log_content
    assert "Step 'template_fail' failed but workflow continues:" in log_content
    assert "Workflow finished successfully" in log_content


def test_run_workflow_exec_error_abort(tmp_path, workflow_with_exec_error):
    """Test workflow aborts on ExecutionError by default."""
    workflow_file = tmp_path / "exec_error_abort.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_exec_error))
    workspace_dir = tmp_path / "workspace_exec_abort"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is False
    assert "Error in step 'exec_fail'" in result["message"]
    assert "Deliberate failure" in result["message"]

    assert (workspace_dir / "output" / "setup.txt").exists()
    assert not (workspace_dir / "output" / "should_not_run_exec.txt").exists()

    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "exec_fail" in log_content
    assert "Workflow aborted due to error in step 'exec_fail'" in log_content


def test_run_workflow_exec_error_continue(tmp_path, workflow_with_exec_error_continue):
    """Test workflow continues on ExecutionError with on_error: continue."""
    workflow_file = tmp_path / "exec_error_continue.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_exec_error_continue))
    workspace_dir = tmp_path / "workspace_exec_continue"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    assert (workspace_dir / "output" / "setup.txt").exists()
    assert (workspace_dir / "output" / "should_not_run_exec.txt").exists()
    assert (
        workspace_dir / "output" / "should_not_run_exec.txt"
    ).read_text().strip() == "This should not have executed"

    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "exec_fail" in log_content
    assert "Step 'exec_fail' failed but workflow continues:" in log_content
    assert "Workflow finished successfully" in log_content


def test_run_workflow_step_skip_condition(tmp_path, workflow_with_condition):
    """Test that a step is skipped if its condition is false."""
    workflow_file = tmp_path / "conditional_workflow.yaml"
    workflow_file.write_text(yaml.dump(workflow_with_condition))
    workspace_dir = tmp_path / "workspace_conditional"

    result = run_workflow(workflow_file=workflow_file, workspace_dir=workspace_dir)

    assert result["success"] is True
    assert "Workflow completed successfully" in result["message"]

    assert not (workspace_dir / "output" / "conditional.txt").exists()

    final_output_file = workspace_dir / "output" / "final.txt"
    assert final_output_file.exists()
    assert final_output_file.read_text().strip() == "Final step ran"

    log_dir = workspace_dir / "logs"
    latest_log = find_latest_log(log_dir)
    assert latest_log is not None
    log_content = latest_log.read_text()
    assert "Skipping step: conditional_step due to condition." in log_content
    assert "Workflow finished successfully" in log_content
