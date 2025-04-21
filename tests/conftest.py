import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from yaml_workflow.tasks import TaskConfig, register_task

# Add the src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Define paths relative to the test file location
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
EXAMPLES_DIR = PROJECT_ROOT / "src" / "yaml_workflow" / "examples"


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield Path(temp_dir)
        os.chdir(old_cwd)


@pytest.fixture
def sample_workflow_file(temp_workspace):
    """Create a sample workflow file for testing."""
    content = """
name: test_workflow
description: A test workflow

params:
  input_value:
    description: Test input
    type: string
    default: test

steps:
  - name: step1
    task: template
    inputs:
      template: "Value is {{ args.input_value }}"
      output_file: output.txt

  - name: step2
    task: shell
    inputs:
      command: "echo 'Processing {{ args.input_value }}' > shell_output.txt"
"""
    workflow_file = temp_workspace / "workflow.yaml"
    workflow_file.write_text(content)
    return workflow_file


@pytest.fixture
def sample_batch_workflow(temp_workspace):
    """Create a sample batch processing workflow."""
    content = """
name: batch_workflow
description: A batch processing workflow

params:
  batch_size:
    description: Number of items per batch
    type: integer
    default: 2

steps:
  - name: generate_items
    task: python
    code: |
      items = [f"item_{i}" for i in range(10)]
      return {"items": items}

  - name: process_batch
    task: batch
    input: "{{ steps.generate_items.output.items }}"
    batch_size: "{{ batch_size }}"
    task:
      type: shell
      command: "echo 'Processing {{ item }}'"
"""
    workflow_file = temp_workspace / "batch_workflow.yaml"
    workflow_file.write_text(content)
    return workflow_file


@pytest.fixture
def sample_parallel_workflow(temp_workspace):
    """Create a sample parallel execution workflow."""
    content = """
name: parallel_workflow
description: A parallel execution workflow

settings:
  max_workers: 3

steps:
  - name: parallel_tasks
    task: parallel
    tasks:
      - name: task1
        task: shell
        command: "sleep 1 && echo 'Task 1'"
      - name: task2
        task: shell
        command: "sleep 1 && echo 'Task 2'"
      - name: task3
        task: shell
        command: "sleep 1 && echo 'Task 3'"
"""
    workflow_file = temp_workspace / "parallel_workflow.yaml"
    workflow_file.write_text(content)
    return workflow_file


@pytest.fixture
def custom_task_module(temp_workspace):
    """Create a sample custom task module."""
    module_dir = temp_workspace / "custom_tasks"
    module_dir.mkdir()

    init_file = module_dir / "__init__.py"
    init_file.write_text("")

    task_file = module_dir / "my_task.py"
    task_file.write_text(
        """
from yaml_workflow.tasks import TaskConfig, register_task

@register_task('my_custom_task')
def my_custom_task_handler(config: TaskConfig) -> dict:
    processed = config.process_inputs()
    message = processed.get('message', 'Hello')
    if not message:
        raise ValueError("'message' is required in inputs")
    return {'result': f"{message} from custom task!"}
"""
    )

    return module_dir


@pytest.fixture(scope="session")
def example_workflows_dir():
    return EXAMPLES_DIR


@pytest.fixture(scope="function")
def workspace_dir(tmp_path_factory):
    # Use tmp_path_factory for function-scoped temporary directories
    return tmp_path_factory.mktemp("workspace")


@pytest.fixture(scope="session")
def run_cli():
    """Fixture to run the CLI command, capturing output via temp files."""

    def _run_cli(args):
        command = [sys.executable, "-m", "yaml_workflow.cli"] + args
        print(f"\n---> Running CLI command: {' '.join(command)}")

        # Create temporary files for stdout and stderr
        with (
            tempfile.NamedTemporaryFile(
                mode="w+", delete=False, encoding="utf-8"
            ) as stdout_file,
            tempfile.NamedTemporaryFile(
                mode="w+", delete=False, encoding="utf-8"
            ) as stderr_file,
        ):
            stdout_path = Path(stdout_file.name)
            stderr_path = Path(stderr_file.name)

            # Run the subprocess, redirecting output to the files
            result = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,  # Still useful for env vars like PYTHONIOENCODING
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            # Read the captured output from the files
            stdout_content = stdout_path.read_text(encoding="utf-8")
            stderr_content = stderr_path.read_text(encoding="utf-8")

        # Clean up temporary files
        stdout_path.unlink()
        stderr_path.unlink()

        # Print captured content for debugging
        print(f"<--- CLI Exit Code: {result.returncode}")
        print(f"<--- Captured STDOUT (from file):\n---\n{stdout_content}\n---")
        print(f"<--- Captured STDERR (from file):\n---\n{stderr_content}\n---")

        return result.returncode, stdout_content, stderr_content

    return _run_cli


@pytest.fixture(scope="session")
def project_config():
    config_path = PROJECT_ROOT / "pyproject.toml"
    if not config_path.exists():
        pytest.fail("pyproject.toml not found at project root")
    return config_path


@pytest.fixture(scope="session")
def workflow_config():
    config_path = PROJECT_ROOT / ".workflow_config.yaml"
    if not config_path.exists():
        # Create a default config if it doesn't exist
        default_config = {
            "logging": {"level": "INFO"},
            "default_workspace_base": "runs",
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f)
        print("Created default .workflow_config.yaml")
    return config_path
