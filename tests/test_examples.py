import json
import os
import re
import subprocess
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
    assert (
        "'required_param' is undefined" in err
    ), "Error message should indicate undefined required_param"

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


def test_complex_flow_error_handling(run_cli, example_workflows_dir, workspace_dir):
    """Test the complex flow and error handling example workflow (success path)."""
    workflow_file = example_workflows_dir / "complex_flow_error_handling.yaml"

    # Run workflow with default parameters (flaky_mode=success)
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

    # Print logs for debugging if failed
    if exit_code != 0:
        print("=== STDOUT ===")
        print(out)
        print("=== STDERR ===")
        print(err)
        log_files = list(workspace_dir.rglob("*.log"))
        if log_files:
            print(f"=== LOG FILE ({log_files[0].name}) ===")
            print(log_files[0].read_text())

    assert exit_code == 0, f"Workflow failed unexpectedly: {err}"

    # Check for initial setup file
    input_data_file = workspace_dir / "output" / "input_data.txt"
    assert input_data_file.exists(), "output/input_data.txt was not created"
    assert "Initial data for DemoUser" in input_data_file.read_text()

    # Check for the main processing log
    processing_log_file = workspace_dir / "output" / "processing_log.txt"
    assert processing_log_file.exists(), "output/processing_log.txt was not created"

    # Verify content of the processing log for successful run
    log_content = processing_log_file.read_text()
    assert (
        "Flaky step succeeded." in log_content
    ), "Flaky step success message missing from log"
    assert (
        "Status from Core 1: Core 1 OK" in log_content
    ), "Core 1 status message missing from log"
    assert (
        "Flaky step result (if successful):" in log_content
    ), "Flaky step result prefix missing from log"
    assert "Flaky Success" in log_content, "Flaky step success output missing from log"
    assert (
        "Core 2 processed" in log_content
    ), "Core 2 processed message missing from log"

    # Ensure the error handler step was NOT executed (check stdout)
    assert (
        "ERROR HANDLED: Flaky step failed permanently." not in out
    ), "Error handler message unexpectedly found in stdout"

    # Ensure cleanup step ran
    assert "Performing cleanup..." in out, "Cleanup start message missing from stdout"
    assert "Cleanup finished." in out, "Cleanup finish message missing from stdout"


def test_complex_flow_error_handling_fail_path(run_cli, example_workflows_dir, workspace_dir):
    """Test the complex flow and error handling example workflow (failure path)."""
    workflow_file = example_workflows_dir / "complex_flow_error_handling.yaml"

    # Run workflow with flaky_mode=fail to trigger the error handling path
    exit_code, out, err = run_cli(
        [
            "run",
            str(workflow_file),
            "--workspace",
            str(workspace_dir),
            "--base-dir",
            str(workspace_dir.parent),
            "flaky_mode=fail",  # Correct parameter format
        ]
    )

    # Print logs for debugging if failed
    if exit_code != 0:
        print("=== STDOUT ===")
        print(out)
        print("=== STDERR ===")
        print(err)
        log_files = list(workspace_dir.rglob("*.log"))
        if log_files:
            print(f"=== LOG FILE ({log_files[0].name}) ===")
            print(log_files[0].read_text())

    assert exit_code == 0, f"Workflow should succeed via error handling: {err}"

    # Check for initial setup file (should still exist)
    input_data_file = workspace_dir / "output" / "input_data.txt"
    assert input_data_file.exists(), "output/input_data.txt was not created"

    # Check that the main processing log was NOT created, as process_core_2 should be skipped
    processing_log_file = workspace_dir / "output" / "processing_log.txt"
    assert not processing_log_file.exists(), "output/processing_log.txt SHOULD NOT be created in failure path"

    # Ensure the error handler step WAS executed (check stdout)
    assert (
        "ERROR HANDLED: Flaky step failed permanently." in out
    ), "Error handler message missing from stdout"

    # Ensure cleanup step ran (should run after error handler)
    assert "Performing cleanup..." in out, "Cleanup start message missing from stdout"
    assert "Cleanup finished." in out, "Cleanup finish message missing from stdout"


def test_complex_flow_core_only_flow(run_cli, example_workflows_dir, workspace_dir):
    """Test the complex flow and error handling example workflow (core_only flow)."""
    complex_workflow_file = example_workflows_dir / "complex_flow_error_handling.yaml"

    # Run workflow with core_only flow and default flaky_mode (success)
    exit_code, out, err = run_cli(
        [
            "run",
            str(complex_workflow_file),
            "--flow",
            "core_only",
            "--workspace",
            str(workspace_dir),
            # No other params needed, rely on defaults in YAML
            # f"workspace={workspace_dir}", # Remove this
            # Keep default flaky_mode (success)
        ],
    )

    # Print logs for debugging if failed
    if exit_code != 0:
        print("=== STDOUT ===")
        print(out)
        print("=== STDERR ===")
        print(err)
        log_files = list(workspace_dir.rglob("*.log"))
        if log_files:
            print(f"=== LOG FILE ({log_files[0].name}) ===")
            print(log_files[0].read_text())

    assert exit_code == 0, f"Workflow failed unexpectedly: {err}"

    # Check for initial setup file
    input_data_file = workspace_dir / "output" / "input_data.txt"
    assert input_data_file.exists(), "output/input_data.txt was not created"
    assert "Initial data for DemoUser" in input_data_file.read_text()

    # Check for the main processing log
    processing_log_file = workspace_dir / "output" / "processing_log.txt"
    assert processing_log_file.exists(), "output/processing_log.txt was not created"

    # Verify content of the processing log for successful run
    log_content = processing_log_file.read_text()
    assert (
        "Flaky step succeeded." in log_content
    ), "Flaky step success message missing from log"
    assert (
        "Status from Core 1: Core 1 OK" in log_content
    ), "Core 1 status message missing from log"
    assert (
        "Flaky step result (if successful):" in log_content
    ), "Flaky step result prefix missing from log"
    assert "Flaky Success" in log_content, "Flaky step success output missing from log"

    # Ensure the error handler step was NOT executed (check stdout)
    assert (
        "ERROR HANDLED: Flaky step failed permanently." not in out
    ), "Error handler message unexpectedly found in stdout"

    # Ensure cleanup step ran
    assert "Performing cleanup..." in out, "Cleanup start message missing from stdout"
    assert "Cleanup finished." in out, "Cleanup finish message missing from stdout"


def test_complex_flow_continue_on_error(run_cli, example_workflows_dir, workspace_dir):
    """Test the complex workflow with on_error: continue for optional_step."""
    complex_workflow_file = example_workflows_dir / "complex_flow_error_handling.yaml"

    # Run workflow with default flow (full_run) which includes optional_step
    # Keep default flaky_mode (success)
    exit_code, out, err = run_cli(
        [
            "run",
            str(complex_workflow_file),
            "--workspace",
            str(workspace_dir),
            # Default flow is used
        ],
    )

    # Print logs for debugging if failed
    if exit_code != 0:
        print("=== STDOUT ===")
        print(out)
        print("=== STDERR ===")
        print(err)
        log_files = list(workspace_dir.rglob("*.log"))
        if log_files:
            print(f"=== LOG FILE ({log_files[0].name}) ===")
            print(log_files[0].read_text())

    assert exit_code == 0, f"Workflow should complete despite optional_step failure: {err}"

    # Check that optional_step attempted to run and failed (check stderr)
    assert "Attempting optional step..." in out # Check stdout for attempt message
    # Check stderr for the specific error from `cat non_existent_file.txt`
    # The exact message might vary slightly by OS/shell, but should contain key parts
    assert "non_existent_file.txt: No such file or directory" in err 
    # assert "Optional step failed as expected, continuing..." in err # Removed: Custom message not logged to stderr on 'continue'

    # Check that subsequent steps ran (process_core_2, cleanup)
    # Check for process_core_2 output in the log file
    processing_log_file = workspace_dir / "output" / "processing_log.txt"
    assert processing_log_file.exists(), "output/processing_log.txt should be created by process_core_2"
    log_content = processing_log_file.read_text()
    assert "Core 2 processed" in log_content, "Core 2 message missing, indicating it didn't run after optional_step failed"

    # Check cleanup step ran (from stdout)
    assert "Performing cleanup..." in out, "Cleanup start message missing from stdout"
    assert "Cleanup finished." in out, "Cleanup finish message missing from stdout"


# Get the root directory of the project based on the location of this file
EXAMPLES_DIR = Path(__file__).parent.parent / "src" / "yaml_workflow" / "examples"
ADVANCED_HELLO_WORLD_YAML = EXAMPLES_DIR / "advanced_hello_world.yaml"


@pytest.mark.last
def test_advanced_hello_world_example():
    """
    Runs the advanced_hello_world.yaml example using the CLI command.
    Checks for successful execution (exit code 0).
    """
    # Ensure the example file exists
    assert (
        ADVANCED_HELLO_WORLD_YAML.is_file()
    ), f"Example file not found: {ADVANCED_HELLO_WORLD_YAML}"

    # Run the workflow command
    # Using sys.executable ensures we use the same Python interpreter (and venv) where pytest is running
    command = [
        sys.executable,
        "-m",
        "yaml_workflow",
        "run",
        str(ADVANCED_HELLO_WORLD_YAML),
    ]

    # Execute the command
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=Path.cwd(),  # Run from project root
    )

    # Print output for debugging if the test fails
    if result.returncode != 0:
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)

    # Assert that the command executed successfully
    assert (
        result.returncode == 0
    ), f"Workflow execution failed with exit code {result.returncode}"

    # Optional: Add checks for specific output files or content here
    # Example:
    # output_json = Path.cwd() / "runs" / "Advanced_Hello_World_run_..." / "output" / "greeting.json"
    # assert output_json.exists()
    # Add more checks as needed
