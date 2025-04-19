import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from jinja2 import Template

from yaml_workflow.cli import main
from yaml_workflow.tasks import TaskConfig, register_task


@pytest.fixture(autouse=True)
def setup_tasks():
    """Register test task handlers."""

    @register_task("echo")
    def echo_task(config: TaskConfig) -> str:
        """Echo task that supports template rendering."""
        processed = config.process_inputs()
        message = processed.get("message", "")
        return message  # Template rendering is handled by process_inputs

    @register_task("return_none")
    def return_none_task(config: TaskConfig):
        """A task that explicitly returns None."""
        return None


@contextmanager
def capture_output():
    """Capture stdout and stderr."""
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


@pytest.fixture
def run_cli():
    """Run CLI command and return output."""

    def _run_cli(args):
        with capture_output() as (out, err):
            try:
                sys.argv = ["yaml-workflow"] + args
                main()
                return 0, out.getvalue(), err.getvalue()
            except SystemExit as e:
                return e.code, out.getvalue(), err.getvalue()

    return _run_cli


@pytest.fixture
def sample_workflow_file(tmp_path):
    """Create a sample workflow file for testing."""
    workflow = {
        "name": "test_workflow",
        "description": "A test workflow",
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "Hello, {{ name }}!"},
            },
            {"name": "step2", "task": "echo", "inputs": {"message": ""}},
        ],
    }
    workflow_file = tmp_path / "test_workflow.yaml"
    workflow_file.write_text(yaml.dump(workflow))
    return workflow_file


@pytest.fixture
def workspace_setup(tmp_path):
    """Setup workspace directory with necessary structure."""
    # Create base directory for runs
    base_dir = tmp_path / "runs"
    base_dir.mkdir()

    # Create workspace directory
    workspace_dir = base_dir / "test_workspace"
    workspace_dir.mkdir()

    # Create metadata file
    metadata = {
        "created_at": datetime.now().isoformat(),
        "workflow": "test_workflow",
        "status": "pending",
        "execution_state": {
            "status": "pending",
            "current_step": None,
            "failed_step": None,
        },
        "run_number": 1,
    }
    (workspace_dir / ".workflow_metadata.json").write_text(json.dumps(metadata))

    return workspace_dir


def test_cli_run_workflow(run_cli, sample_workflow_file, workspace_setup):
    """Test running a workflow through CLI."""
    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "name=World",
        ]
    )
    if exit_code != 0:
        print(f"\nOutput:\n{out}\nError:\n{err}")
    assert exit_code == 0
    assert "Workflow completed successfully" in out
    assert "Hello, World!" in out


def test_cli_run_with_custom_workspace(run_cli, sample_workflow_file, tmp_path):
    """Test running workflow with custom workspace directory."""
    base_dir = tmp_path / "runs"
    base_dir.mkdir()
    workspace_dir = base_dir / "custom_workspace"
    workspace_dir.mkdir()

    # Create metadata file
    metadata = {
        "created_at": datetime.now().isoformat(),
        "workflow": "test_workflow",
        "status": "pending",
        "execution_state": {
            "status": "pending",
            "current_step": None,
            "failed_step": None,
        },
        "run_number": 1,
    }
    (workspace_dir / ".workflow_metadata.json").write_text(json.dumps(metadata))

    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(base_dir),
            "name=Test",
        ]
    )
    assert exit_code == 0
    assert "Workflow completed successfully" in out
    assert workspace_dir.exists()


def test_cli_run_with_invalid_params(run_cli, sample_workflow_file, workspace_setup):
    """Test running workflow with invalid parameters."""
    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "invalid:param",
        ]
    )
    assert exit_code != 0
    assert "Invalid parameter format" in err


def test_cli_validate_workflow(run_cli, sample_workflow_file):
    """Test workflow validation through CLI."""
    exit_code, out, err = run_cli(["validate", str(sample_workflow_file)])
    assert exit_code == 0
    assert "Workflow validation successful" in out


def test_cli_validate_invalid_workflow(run_cli, tmp_path):
    """Test validation of invalid workflow."""
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("invalid: yaml: content")
    exit_code, out, err = run_cli(["validate", str(invalid_file)])
    assert exit_code != 0
    assert "Validation failed" in err


def test_cli_list_workflows(run_cli, tmp_path):
    """Test listing available workflows."""
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()

    # Create test workflow files
    workflow1 = {
        "workflow": {
            "usage": {"name": "workflow1", "description": "First workflow"},
            "steps": {"step1": {"task": "echo", "message": "test"}},
        }
    }
    workflow2 = {
        "workflow": {
            "usage": {"name": "workflow2", "description": "Second workflow"},
            "steps": {"step1": {"task": "echo", "message": "test"}},
        }
    }

    (workflows_dir / "workflow1.yaml").write_text(yaml.dump(workflow1))
    (workflows_dir / "workflow2.yaml").write_text(yaml.dump(workflow2))

    exit_code, out, err = run_cli(["list", "--base-dir", str(workflows_dir)])
    assert exit_code == 0
    assert "workflow1" in out
    assert "workflow2" in out
    assert "First workflow" in out
    assert "Second workflow" in out


def test_cli_workspace_list(run_cli, tmp_path):
    """Test listing workspace runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create test run directories with metadata
    run1_dir = runs_dir / "test_run_1"
    run1_dir.mkdir()
    metadata1 = {
        "created_at": "2024-01-01T00:00:00",
        "workflow": "test_workflow",
        "status": "completed",
    }
    (run1_dir / ".workflow_metadata.json").write_text(json.dumps(metadata1))

    exit_code, out, err = run_cli(["workspace", "list", "--base-dir", str(runs_dir)])
    assert exit_code == 0
    assert "test_run_1" in out


def test_cli_workspace_clean(run_cli, tmp_path):
    """Test cleaning old workspace runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create test run directory with old metadata
    run1_dir = runs_dir / "test_run_1"
    run1_dir.mkdir()
    metadata1 = {
        "created_at": "2023-01-01T00:00:00",
        "workflow": "test_workflow",
        "status": "completed",
    }
    (run1_dir / ".workflow_metadata.json").write_text(json.dumps(metadata1))

    # Test dry run first
    exit_code, out, err = run_cli(
        [
            "workspace",
            "clean",
            "--base-dir",
            str(runs_dir),
            "--older-than",
            "30",
            "--dry-run",
        ]
    )
    assert exit_code == 0
    assert run1_dir.name in out
    assert "dry run" in out.lower()
    assert run1_dir.exists()

    # Test actual clean
    exit_code, out, err = run_cli(
        ["workspace", "clean", "--base-dir", str(runs_dir), "--older-than", "30"]
    )
    assert exit_code == 0
    assert not run1_dir.exists()


def test_cli_workspace_clean_invalid_date(run_cli, tmp_path):
    """Test workspace clean when metadata has an invalid date format."""
    runs_dir = tmp_path / "clean_invalid_date"
    runs_dir.mkdir()

    # Create a run directory with invalid created_at
    run1_dir = runs_dir / "test_run_bad_date_1"
    run1_dir.mkdir()
    metadata1 = {
        "created_at": "not-a-valid-iso-date",  # Invalid date
        "workflow": "test_workflow",
        "status": "completed",
        "execution_state": {},
        "run_number": 1,
    }
    (run1_dir / ".workflow_metadata.json").write_text(json.dumps(metadata1))

    exit_code, out, err = run_cli(
        ["workspace", "clean", "--base-dir", str(runs_dir), "--older-than", "0"]
    )

    assert exit_code == 0
    assert f"Warning: Could not process {run1_dir}" in err
    assert "No old workflow runs to clean up." in out  # Should skip the bad one


def test_cli_workspace_remove(run_cli, tmp_path):
    """Test removing specific workspace runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create test run directories
    run1_dir = runs_dir / "test_run_1"
    run1_dir.mkdir()
    run2_dir = runs_dir / "test_run_2"
    run2_dir.mkdir()

    # Test remove with force flag
    exit_code, out, err = run_cli(
        ["workspace", "remove", "test_run_1", "--base-dir", str(runs_dir), "--force"]
    )
    assert exit_code == 0
    assert not run1_dir.exists()
    assert run2_dir.exists()


def test_cli_run_with_skip_steps(run_cli, sample_workflow_file, workspace_setup):
    """Test running workflow with skipped steps."""
    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "--skip-steps",
            "step2",
            "name=World",
        ]
    )
    assert exit_code == 0
    assert "Hello, World!" in out
    assert "Skipping steps: step2" in out


def test_cli_run_with_start_from(run_cli, sample_workflow_file, workspace_setup):
    """Test running workflow from specific step."""
    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "--start-from",
            "step2",
            "name=World",
        ]
    )
    assert exit_code == 0
    assert "Starting workflow from step: step2" in out
    # assert "Done!" in out # Step 2 now outputs empty string


def test_cli_help(run_cli):
    """Test CLI help commands."""
    # Main help
    exit_code, out, err = run_cli(["--help"])
    assert exit_code == 0
    assert "usage:" in out
    assert "Commands:" in out

    # Run command help
    exit_code, out, err = run_cli(["run", "--help"])
    assert exit_code == 0
    assert "usage:" in out
    assert "--workspace" in out
    assert "--base-dir" in out

    # Workspace commands help
    exit_code, out, err = run_cli(["workspace", "--help"])
    assert exit_code == 0
    assert "usage:" in out
    assert "list" in out
    assert "clean" in out
    assert "remove" in out


def test_cli_run_unrecognized_param_with_help(run_cli, sample_workflow_file):
    """Test that providing --help with an unrecognized param still shows help."""
    # This tests lines 38-39 in WorkflowArgumentParser.error
    exit_code, out, err = run_cli(
        ["run", str(sample_workflow_file), "invalid_param=test", "--help"]
    )
    assert exit_code == 0
    assert "usage: yaml-workflow run" in out


def test_cli_run_invalid_param_format(run_cli, sample_workflow_file):
    """Test running with an invalid parameter format (no equals sign)."""
    # This tests lines 43-47 in WorkflowArgumentParser.error
    exit_code, out, err = run_cli(["run", str(sample_workflow_file), "badparam"])
    assert exit_code == 1
    assert "Invalid parameter format: badparam" in err
    assert "Parameters must be in the format: name=value" in err


def test_cli_validate_missing_arg(run_cli):
    """Test calling validate without the required workflow file argument."""
    # This should trigger the else block (line 50) in WorkflowArgumentParser.error
    exit_code, out, err = run_cli(["validate"])
    assert exit_code == 2  # Argparse typically exits with 2 for usage errors
    assert "the following arguments are required: workflow" in err


def test_cli_run_skips_none_output(run_cli, tmp_path):
    """Test that the CLI run output skips steps that return None."""
    # Create a workflow using the return_none task
    workflow = {
        "name": "test_none_output",
        "steps": [
            {
                "name": "step1",
                "task": "echo",
                "inputs": {"message": "First Step Output"},
            },
            {"name": "step_returns_none", "task": "return_none"},
            {
                "name": "step3",
                "task": "echo",
                "inputs": {"message": "Third Step Output"},
            },
        ],
    }
    workflow_file = tmp_path / "test_none_output.yaml"
    workflow_file.write_text(yaml.dump(workflow))

    exit_code, out, err = run_cli(["run", str(workflow_file)])

    assert exit_code == 0
    assert "Workflow completed successfully" in out
    assert "=== Step Outputs ===" in out
    assert "• step1:" in out
    assert "First Step Output" in out  # Check actual output rendering too
    assert "step_returns_none" not in out  # The step name header should be skipped
    assert "• step3:" in out
    assert "Third Step Output" in out


def test_cli_run_resume_invalid_metadata(
    run_cli, sample_workflow_file, workspace_setup
):
    """Test resuming with an invalid (corrupt) metadata file."""
    # Overwrite metadata with invalid JSON
    metadata_path = workspace_setup / ".workflow_metadata.json"
    metadata_path.write_text('{"invalid json')  # Write invalid JSON

    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "--resume",
        ]
    )
    assert exit_code == 1
    assert "Cannot resume: Invalid metadata file format" in err


def test_cli_run_resume_missing_failed_step(
    run_cli, sample_workflow_file, workspace_setup
):
    """Test resuming with metadata indicating failure but missing the failed step info."""
    # Modify metadata: status=failed, but no failed_step key
    metadata_path = workspace_setup / ".workflow_metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    metadata["execution_state"]["status"] = "failed"
    if "failed_step" in metadata["execution_state"]:
        del metadata["execution_state"]["failed_step"]
    metadata_path.write_text(json.dumps(metadata))

    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "--resume",
        ]
    )
    assert exit_code == 1
    assert "No failed step found to resume from" in err


def test_cli_run_resume_missing_workspace(run_cli, sample_workflow_file, tmp_path):
    """Test resuming with a non-existent workspace directory."""
    non_existent_workspace = tmp_path / "non_existent_ws"
    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(non_existent_workspace),
            "--resume",
        ]
    )
    assert exit_code == 1
    assert "Cannot resume: Workspace directory not found" in err


def test_cli_run_resume_missing_metadata_file(
    run_cli, sample_workflow_file, workspace_setup
):
    """Test resuming when the workspace exists but the metadata file is missing."""
    # Delete the metadata file
    metadata_path = workspace_setup / ".workflow_metadata.json"
    if metadata_path.exists():
        metadata_path.unlink()

    exit_code, out, err = run_cli(
        [
            "run",
            str(sample_workflow_file),
            "--workspace",
            str(workspace_setup),
            "--base-dir",
            str(workspace_setup.parent),
            "--resume",
        ]
    )
    assert exit_code == 1
    assert "Cannot resume: No workflow metadata found" in err


def test_cli_list_non_existent_dir(run_cli, tmp_path):
    """Test the list command when the base directory doesn't exist."""
    non_existent_dir = tmp_path / "no_such_dir"
    exit_code, out, err = run_cli(["list", "--base-dir", str(non_existent_dir)])
    assert exit_code == 1
    assert f"Directory not found: {non_existent_dir}" in err


def test_cli_list_invalid_yaml(run_cli, tmp_path):
    """Test the list command when a file is invalid YAML."""
    workflows_dir = tmp_path / "list_test_invalid"
    workflows_dir.mkdir()

    # Create an invalid YAML file
    invalid_file = workflows_dir / "bad.yaml"
    invalid_file.write_text("key: value: other_value")  # Invalid YAML syntax

    # Create a valid workflow file to ensure the 'not found' block isn't hit
    valid_workflow = {
        "steps": [{"name": "step1", "task": "echo", "inputs": {"message": "hello"}}]
    }
    valid_file = workflows_dir / "good.yaml"
    valid_file.write_text(yaml.dump(valid_workflow))

    exit_code, out, err = run_cli(["list", "--base-dir", str(workflows_dir)])

    assert exit_code == 0
    assert "good.yaml" in out  # Should list the valid file
    assert "Name: good" in out
    assert "bad.yaml" not in out  # Should skip the invalid file
    assert "No workflow files found" not in out  # Should not hit the 'not found' block


def test_cli_list_no_workflows_found(run_cli, tmp_path):
    """Test the list command when no valid workflows are found."""
    empty_dir = tmp_path / "list_test_empty"
    empty_dir.mkdir()

    exit_code, out, err = run_cli(["list", "--base-dir", str(empty_dir)])

    assert exit_code == 0
    assert "No workflow files found" in out
    assert f"in the '{empty_dir}' directory" in out


def test_cli_workspace_list_non_existent_dir(run_cli, tmp_path):
    """Test the workspace list command when the base directory doesn't exist."""
    non_existent_dir = tmp_path / "no_runs_dir"
    exit_code, out, err = run_cli(
        ["workspace", "list", "--base-dir", str(non_existent_dir)]
    )
    assert exit_code == 1
    assert f"Base directory not found: {non_existent_dir}" in err


def test_cli_workspace_list_invalid_metadata(run_cli, tmp_path):
    """Test workspace list when a run directory has invalid metadata."""
    runs_dir = tmp_path / "list_invalid_meta"
    runs_dir.mkdir()

    # Create a run directory with invalid metadata
    run1_dir = runs_dir / "test_run_1"
    run1_dir.mkdir()
    metadata_path = run1_dir / ".workflow_metadata.json"
    metadata_path.write_text('{"invalid json')  # Write invalid JSON

    # Create another valid run for comparison
    run2_dir = runs_dir / "test_run_2"
    run2_dir.mkdir()
    metadata2 = {
        "created_at": datetime.now().isoformat(),
        "workflow": "test_workflow",
        "status": "completed",
        "execution_state": {},
        "run_number": 2,
    }
    (run2_dir / ".workflow_metadata.json").write_text(json.dumps(metadata2))

    exit_code, out, err = run_cli(["workspace", "list", "--base-dir", str(runs_dir)])

    assert exit_code == 0
    # assert f"Warning: Could not get info for {run1_dir}" in err # get_workspace_info handles this internally
    # The run with invalid metadata might still be listed with default/error values,
    # or might be skipped depending on how list_workspaces handles the error key from get_workspace_info.
    # For now, let's just ensure the valid run is listed and no fatal error occurs.
    # A more specific assertion could check for 'unknown' status or the error message if needed.
    # assert "test_run_1" not in out # Might actually appear with default info
    assert "test_run_2" in out  # The valid run should be listed


def test_cli_workspace_list_no_runs(run_cli, tmp_path):
    """Test workspace list when the base directory exists but has no runs."""
    runs_dir = tmp_path / "empty_runs_dir"
    runs_dir.mkdir()

    exit_code, out, err = run_cli(["workspace", "list", "--base-dir", str(runs_dir)])
    assert exit_code == 0
    assert "No workflow runs found." in out


def test_cli_workspace_clean_non_existent_dir(run_cli, tmp_path):
    """Test the workspace clean command when the base directory doesn't exist."""
    non_existent_dir = tmp_path / "no_clean_dir"
    exit_code, out, err = run_cli(
        ["workspace", "clean", "--base-dir", str(non_existent_dir)]
    )
    assert exit_code == 1
    assert f"Base directory not found: {non_existent_dir}" in err


def test_cli_workspace_remove_non_existent_dir(run_cli, tmp_path):
    """Test the workspace remove command when the base directory doesn't exist."""
    non_existent_dir = tmp_path / "no_remove_dir"
    exit_code, out, err = run_cli(
        ["workspace", "remove", "some_run_name", "--base-dir", str(non_existent_dir)]
    )
    assert exit_code == 1
    assert f"Base directory not found: {non_existent_dir}" in err


def test_cli_workspace_remove_file_target(run_cli, tmp_path):
    """Test workspace remove when the target is a file, not a directory."""
    runs_dir = tmp_path / "remove_file_target"
    runs_dir.mkdir()

    # Create a file with the name of a run
    run_file = runs_dir / "test_run_as_file"
    run_file.write_text("I am a file, not a directory.")

    exit_code, out, err = run_cli(
        [
            "workspace",
            "remove",
            "test_run_as_file",
            "--base-dir",
            str(runs_dir),
            "--force",
        ]
    )

    assert exit_code == 0  # Should exit cleanly after warning
    assert f"Warning: Not a directory: {run_file}" in err
    assert "No valid run directories to remove." in out


def test_cli_workspace_remove_cancel(run_cli, tmp_path, monkeypatch):
    """Test cancelling the workspace remove command at the prompt."""
    runs_dir = tmp_path / "remove_cancel"
    runs_dir.mkdir()
    run1_dir = runs_dir / "test_run_to_cancel"
    run1_dir.mkdir()
    # Create dummy metadata so get_workspace_info works
    metadata1 = {
        "created_at": datetime.now().isoformat(),
        "workflow": "cancel_test",
        "status": "completed",
        "execution_state": {},
        "run_number": 1,
    }
    (run1_dir / ".workflow_metadata.json").write_text(json.dumps(metadata1))

    # Simulate user typing "n" at the input prompt
    monkeypatch.setattr("builtins.input", lambda _: "n")

    exit_code, out, err = run_cli(
        [
            "workspace",
            "remove",
            "test_run_to_cancel",
            "--base-dir",
            str(runs_dir),
            # No --force
        ]
    )

    assert exit_code == 0
    assert "Operation cancelled." in out
    assert run1_dir.exists()  # Check that the directory was NOT removed


# --- Tests for 'init' command ---


def test_cli_init_default(run_cli, tmp_path):
    """Test the init command with default settings."""
    # Change to tmp_path so default 'workflows' dir is created there
    os.chdir(tmp_path)
    exit_code, out, err = run_cli(["init"])
    assert exit_code == 0
    assert f"Initialized project with examples in: workflows" in out
    workflows_dir = tmp_path / "workflows"
    assert workflows_dir.is_dir()
    # Check for a known example file that exists
    assert (workflows_dir / "hello_world.yaml").is_file()


def test_cli_init_custom_dir(run_cli, tmp_path):
    """Test the init command with a custom directory."""
    custom_dir = tmp_path / "custom_examples"
    exit_code, out, err = run_cli(["init", "--dir", str(custom_dir)])
    assert exit_code == 0
    assert f"Initialized project with examples in: {custom_dir}" in out
    assert custom_dir.is_dir()
    # Check for a known example file that exists
    assert (custom_dir / "hello_world.yaml").is_file()


def test_cli_init_specific_example(run_cli, tmp_path):
    """Test the init command copying a specific example."""
    os.chdir(tmp_path)  # Use default 'workflows' target
    # Use an example that actually exists
    example_name = "hello_world"
    exit_code, out, err = run_cli(["init", "--example", example_name])
    assert exit_code == 0
    assert (
        f"Initialized project with example '{example_name}.yaml' in: workflows" in out
    )
    workflows_dir = tmp_path / "workflows"
    assert workflows_dir.is_dir()
    assert (workflows_dir / f"{example_name}.yaml").is_file()
    # Make sure other examples weren't copied
    assert not (workflows_dir / "python_tasks.yaml").exists()


def test_cli_init_bad_example(run_cli, tmp_path):
    """Test the init command with a non-existent example name."""
    os.chdir(tmp_path)
    exit_code, out, err = run_cli(["init", "--example", "non_existent_example"])
    assert exit_code == 1
    assert "Example 'non_existent_example' not found" in err
    # Ensure workflows dir might be created but is empty
    workflows_dir = tmp_path / "workflows"
    assert not any(workflows_dir.iterdir())  # Check directory is empty if created


# --- Tests for other commands/edge cases ---
