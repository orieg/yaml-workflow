import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from yaml_workflow.cli import main
from yaml_workflow.engine import WorkflowEngine


# Helper to capture stdout/stderr
@contextmanager
def capture_output():
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
def example_workflows_dir():
    """Get the path to the example workflows directory."""
    return Path(__file__).parent.parent / "src" / "yaml_workflow" / "examples"


@pytest.fixture
def workspace_dir(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


def test_basic_hello_world(run_cli, example_workflows_dir, workspace_dir):
    """Test the basic hello world example workflow."""
    workflow_file = example_workflows_dir / "hello_world.yaml"

    # Run workflow with default name
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
        ]
    )

    assert exit_code == 0, f"Workflow failed with error: {err}"

    # Check if greeting.txt was created
    greeting_file = workspace_dir / "greeting.txt"
    assert greeting_file.exists(), "greeting.txt was not created"

    # Verify greeting content
    greeting_content = greeting_file.read_text()
    assert "Hello, World!" in greeting_content
    assert f"run #1" in greeting_content.lower()
    assert "Hello World" in greeting_content  # workflow name
    assert str(workspace_dir) in greeting_content

    # Check shell output
    assert "Workflow run information:" in out
    assert "Current directory:" in out

    # Run workflow with custom name
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "name=Alice",
        ]
    )

    assert exit_code == 0, f"Workflow failed with error: {err}"
    greeting_content = (workspace_dir / "greeting.txt").read_text()
    assert "Hello, Alice!" in greeting_content


def test_advanced_hello_world_success(run_cli, example_workflows_dir, workspace_dir):
    """Test the advanced hello world example workflow with valid input."""
    workflow_file = example_workflows_dir / "advanced_hello_world.yaml"

    # Run workflow with valid name
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "name=Alice",
        ]
    )

    assert exit_code == 0, f"Workflow failed with error: {err}"

    # Check validation result
    validation_file = workspace_dir / "output" / "validation_result.txt"
    assert validation_file.exists()
    assert "Valid: Alice" in validation_file.read_text()

    # Check JSON greeting
    greeting_json = workspace_dir / "output" / "greeting.json"
    assert greeting_json.exists()
    with open(greeting_json) as f:
        greeting_data = json.load(f)
        assert greeting_data["greeting"] == "Hello, Alice!"
        assert "timestamp" in greeting_data
        assert "run_number" in greeting_data

    # Check YAML greetings
    greetings_yaml = workspace_dir / "output" / "greetings.yaml"
    assert greetings_yaml.exists()
    with open(greetings_yaml) as f:
        greetings_data = yaml.safe_load(f)
        assert greetings_data["English"] == "Hello, Alice!"
        assert greetings_data["Spanish"] == "¡Hola, Alice!"
        assert len(greetings_data) >= 6  # At least 6 languages

    # Check final output
    assert "Workflow completed successfully!" in out
    assert "Check the output files for detailed results:" in out


def test_advanced_hello_world_validation_errors(
    run_cli, example_workflows_dir, workspace_dir
):
    """Test the advanced hello world example workflow with invalid inputs."""
    workflow_file = example_workflows_dir / "advanced_hello_world.yaml"

    # Test case 1: Empty name
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "name=",
        ]
    )

    assert exit_code == 0  # Workflow should complete but with validation error
    validation_file = workspace_dir / "output" / "validation_result.txt"
    assert validation_file.exists()
    assert "Error: Name parameter is required" in validation_file.read_text()
    assert "Check error_report.txt for details" in out

    # Test case 2: Name too short
    workspace_dir_2 = workspace_dir.parent / "workspace2"
    workspace_dir_2.mkdir()
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir_2),
            "--base-dir",
            str(workspace_dir.parent),
            "name=A",
        ]
    )

    assert exit_code == 0
    validation_file = workspace_dir_2 / "output" / "validation_result.txt"
    assert (
        "Error: Name must be at least 2 characters long" in validation_file.read_text()
    )

    # Test case 3: Name too long (51 characters)
    workspace_dir_3 = workspace_dir.parent / "workspace3"
    workspace_dir_3.mkdir()
    long_name = "A" * 51
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir_3),
            "--base-dir",
            str(workspace_dir.parent),
            f"name={long_name}",
        ]
    )

    assert exit_code == 0
    validation_file = workspace_dir_3 / "output" / "validation_result.txt"
    assert "Error: Name must not exceed 50 characters" in validation_file.read_text()

    # Verify error report creation
    for ws in [workspace_dir, workspace_dir_2, workspace_dir_3]:
        error_report = ws / "output" / "error_report.txt"
        assert error_report.exists()
        report_content = error_report.read_text()
        assert "Workflow encountered an error:" in report_content
        assert "Input validation failed" in report_content
        assert "Requirements:" in report_content


def test_advanced_hello_world_conditional_execution(
    run_cli, example_workflows_dir, workspace_dir
):
    """Test that steps are conditionally executed based on validation results."""
    workflow_file = example_workflows_dir / "advanced_hello_world.yaml"

    # Test with invalid input - should not create greeting files
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "name=A",  # Invalid name (too short)
        ]
    )

    assert exit_code == 0

    # Check that validation failed
    validation_file = workspace_dir / "output" / "validation_result.txt"
    assert validation_file.exists()
    assert (
        "Error: Name must be at least 2 characters long" in validation_file.read_text()
    )

    # Verify greeting files were not created
    greeting_json = workspace_dir / "output" / "greeting.json"
    greetings_yaml = workspace_dir / "output" / "greetings.yaml"
    assert not greeting_json.exists()
    assert not greetings_yaml.exists()

    # Verify error report was created instead
    error_report = workspace_dir / "output" / "error_report.txt"
    assert error_report.exists()


def test_resume_workflow(run_cli, example_workflows_dir, workspace_dir):
    """Test the resume workflow example."""
    workflow_file = example_workflows_dir / "test_resume.yaml"

    # First run - should fail at check_required_param step since required_param is not provided
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
        ]
    )

    assert (
        exit_code != 0
    ), "Workflow should fail on first run due to missing required_param"
    assert "Error: required_param is required" in err

    print("\n=== First run output ===")
    print("Exit code:", exit_code)
    print("Stdout:", out)
    print("Stderr:", err)

    # Create output directory since first run failed before creating it
    output_dir = workspace_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Print metadata file content
    metadata_file = workspace_dir / ".workflow_metadata.json"
    print("\n=== Current metadata file ===")
    with open(metadata_file) as f:
        print(json.dumps(json.load(f), indent=2))

    # Resume the workflow with required_param
    resume_args = [
        "run",
        str(workflow_file),
        "required_param=test_value",  # Parameter MUST come before --resume
        "--workspace",
        str(workspace_dir),
        "--base-dir",
        str(workspace_dir.parent),
        "--resume",
    ]
    print("\n=== Resume command ===")
    print("Args:", resume_args)

    exit_code, out, err = run_cli(resume_args)

    print("\n=== Resume attempt output ===")
    print("Exit code:", exit_code)
    print("Stdout:", out)
    print("Stderr:", err)

    assert exit_code == 0, f"Workflow should complete on resume. Error output: {err}"

    # Check that result file was created and has correct content
    result_file = workspace_dir / "output" / "result.txt"
    assert result_file.exists(), "result.txt should be created"
    assert result_file.read_text().strip() == "test_value"

    # Try to resume completed workflow - should fail
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "--resume",
        ]
    )

    assert exit_code != 0, "Resuming completed workflow should fail"
    assert "Cannot resume: workflow is not in failed state" in err
