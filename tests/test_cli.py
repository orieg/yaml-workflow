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
from yaml_workflow.tasks import create_task_handler, register_task


@pytest.fixture(autouse=True)
def setup_tasks():
    """Register test task handlers."""

    @register_task("echo")
    def echo_task(step, context, workspace):
        """Echo task that supports template rendering."""
        message = step.get("inputs", {}).get("message", "")
        # Render template with context
        template = Template(message)
        rendered_message = template.render(**context)
        return rendered_message


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
            {"name": "step2", "task": "echo", "inputs": {"message": "Done!"}},
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
    assert "Done!" in out


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
