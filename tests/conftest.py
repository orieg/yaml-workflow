import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from yaml_workflow.tasks import create_task_handler, register_task

# Add the src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))


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
    template: "Value is {{ input_value }}"
    output: output.txt

  - name: step2
    task: shell
    command: "echo 'Processing {{ input_value }}'"
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
from yaml_workflow.tasks import register_task, create_task_handler

def my_custom_task(message='Hello'):
    return {'result': f"{message} from custom task!"}

@register_task('my_custom_task')
def my_custom_task_handler(step, context, workspace):
    inputs = step.get('inputs', {})
    if 'message' not in inputs:
        raise ValueError("'message' is required in inputs")
    return my_custom_task(**inputs)
"""
    )

    return module_dir
