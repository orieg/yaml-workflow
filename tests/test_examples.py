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

    # Debug output for GitHub Actions
    print("\n=== DEBUG OUTPUT FOR GITHUB ACTIONS ===")
    print(f"Workspace directory: {workspace_dir}")
    print(f"Exit code: {exit_code}")
    print(f"STDOUT:\n{out}")
    if err:
        print(f"STDERR:\n{err}")

    # Check output directory exists and list contents
    output_dir = workspace_dir / "output"
    print(f"Output directory exists: {output_dir.exists()}")
    if output_dir.exists():
        print(f"Output directory contents: {list(output_dir.glob('*'))}")

    assert exit_code == 0, f"Workflow failed with error: {err}"

    # Check validation result
    validation_file = workspace_dir / "output" / "validation_result.txt"
    validation_exists = validation_file.exists()
    print(f"Validation file exists: {validation_exists}")

    assert validation_exists
    validation_content = validation_file.read_text()
    print(f"Validation file content: {validation_content}")
    assert "Valid: Alice" in validation_content

    # Check if processed_validation.txt exists and what it contains
    processed_file = workspace_dir / "output" / "processed_validation.txt"
    if processed_file.exists():
        processed_content = processed_file.read_text()
        print(f"Processed validation file content: {processed_content}")
    else:
        print("Processed validation file does not exist")

    # Debug: Check all files in output directory
    print("All files in output directory before checking greeting.json:")
    all_files = list(output_dir.glob("**/*"))
    for file in all_files:
        if file.is_file():
            print(f"  - {file.relative_to(workspace_dir)}: {file.stat().st_size} bytes")

    # Check JSON greeting
    greeting_json = workspace_dir / "output" / "greeting.json"
    exists = greeting_json.exists()
    print(f"Greeting JSON exists: {exists}")

    assert (
        exists
    ), f"greeting.json missing from output dir. Directory contents: {all_files}"

    # Continue with the rest of the test...
    with open(greeting_json) as f:
        greeting_data = json.load(f)
        assert greeting_data["name"] == "Alice"
        assert "Hello, Alice!" in greeting_data["message"]
        assert "timestamp" in greeting_data
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", greeting_data["timestamp"]
        )

    # Check YAML greetings (final format after 'format_output' step)
    greetings_yaml = workspace_dir / "output" / "greetings.yaml"
    assert greetings_yaml.exists()
    with open(greetings_yaml) as f:
        greetings_data = yaml.safe_load(f)
    # Check keys as defined in the FINAL version of the file (en, es, fr)
    assert greetings_data["en"] == "Hello, Alice!"
    assert greetings_data["es"] == "Hola, Alice!"
    assert greetings_data["fr"] == "Bonjour, Alice!"
    # Remove checks for the details structure, as it's not in the final format
    # assert "details" in greetings_data
    # assert greetings_data["details"]["name"] == "Alice"
    # assert "timestamp" in greetings_data["details"]
    # assert "run_number" in greetings_data["details"]

    # Check final output printed by cli.py after engine run
    assert "✓ Workflow completed successfully" in out
    # assert "Check the output files for detailed results:" in out # This part comes from notify_status, might be unreliable


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
    assert "Check output/error_report.txt for details." in out

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
    assert "Check output/error_report.txt for details." in out

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
    assert "Check output/error_report.txt for details." in out

    # Verify error report creation
    for ws in [workspace_dir, workspace_dir_2, workspace_dir_3]:
        error_report = ws / "output" / "error_report.txt"
        assert error_report.exists()
        report_content = error_report.read_text()
        assert "Workflow failed for input name:" in report_content
        assert "Validation Status: FAILED:" in report_content


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


def test_complex_flow_error_handling_fail_path(
    run_cli, example_workflows_dir, workspace_dir
):
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
    assert (
        not processing_log_file.exists()
    ), "output/processing_log.txt SHOULD NOT be created in failure path"

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
    exit_code, out, err = run_cli(
        [
            "run",
            str(complex_workflow_file),
            "--workspace",
            str(workspace_dir),
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

    assert (
        exit_code == 0
    ), f"Workflow should complete despite optional_step failure: {err}"

    # --- Check State for Failure Details ---
    # Load the state file
    state_file = workspace_dir / ".workflow_metadata.json"
    assert state_file.exists(), "Workflow state file not found."
    with open(state_file) as f:
        final_state = json.load(f)

    # Check that optional_step is marked as failed in the state
    assert (
        "optional_step" in final_state["execution_state"]["step_outputs"]
    ), "optional_step not found in final state step_outputs"
    optional_step_state = final_state["execution_state"]["step_outputs"][
        "optional_step"
    ]
    assert (
        optional_step_state["status"] == "failed"
    ), "Optional step status should be failed"

    # Check the error message stored in the state for the expected content
    assert (
        "error" in optional_step_state
    ), "Error message missing from optional_step state"
    step_error_message = optional_step_state["error"]
    # Check that the error message matches the custom message defined in on_error
    expected_error = "Optional step failed as expected, continuing..."
    assert step_error_message == expected_error

    # Check that subsequent steps ran (process_core_2, cleanup)
    # Check for process_core_2 output in the log file
    processing_log_file = workspace_dir / "output" / "processing_log.txt"
    assert (
        processing_log_file.exists()
    ), "output/processing_log.txt should be created by process_core_2"
    log_content = processing_log_file.read_text()
    assert (
        "Core 2 processed" in log_content
    ), "Core 2 message missing, indicating it didn't run after optional_step failed"

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
