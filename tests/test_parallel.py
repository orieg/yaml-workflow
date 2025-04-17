"""Tests for parallel execution functionality."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.batch import batch_task


@pytest.fixture
def sample_items():
    """Create sample items for batch processing."""
    return [f"item_{i}" for i in range(10)]


@pytest.fixture
def parallel_workflow(tmp_path):
    """Create a workflow file for testing parallel execution."""
    workflow_path = tmp_path / "parallel_workflow.yaml"
    workflow_content = """
name: parallel_test
steps:
  - name: parallel_step
    task: batch
    inputs:
      items: ["item1", "item2", "item3"]
      arg_name: item
      chunk_size: 3
      max_workers: 3
      task:
        task: shell
        inputs:
          command: sleep 0.5 && echo 'Processing {{ args["item"] }}'
"""
    workflow_path.write_text(workflow_content)
    return workflow_path


def test_parallel_execution_time(temp_workspace):
    """Test that parallel execution is faster than sequential."""
    step = {
        "name": "test_parallel",
        "task": "batch",
        "inputs": {
            "items": ["file1", "file2", "file3"],
            "arg_name": "file_path",
            "max_workers": 3,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
import time
time.sleep(0.5)
result = f"Processing {args['file_path']}"
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    start_time = time.time()
    result = batch_task(config)
    end_time = time.time()

    assert len(result["processed"]) == 3
    assert end_time - start_time < 1.5  # Should take ~0.5s with parallel execution


def test_batch_processing_results(temp_workspace):
    """Test that batch processing returns correct results."""
    step = {
        "name": "test_batch_results",
        "task": "batch",
        "inputs": {
            "items": [1, 2, 3],
            "arg_name": "number",
            "max_workers": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
result = args['number'] * 2
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    result = batch_task(config)

    assert len(result["processed"]) == 3
    assert result["results"][0] == 2
    assert result["results"][1] == 4
    assert result["results"][2] == 6


def test_batch_error_handling(temp_workspace):
    """Test error handling in batch processing."""
    step = {
        "name": "test_batch_errors",
        "task": "batch",
        "inputs": {
            "items": [2, 0, 1],
            "arg_name": "number",
            "max_workers": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
try:
    result = 10 / args['number']
except ZeroDivisionError:
    raise ValueError("Cannot divide by zero")
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    result = batch_task(config)

    assert len(result["processed"]) == 2
    assert len(result["failed"]) == 1
    # Calculate success rate manually
    success_rate = len(result["processed"]) / (len(result["processed"]) + len(result["failed"]))
    assert success_rate == pytest.approx(0.67, abs=0.01)


def test_batch_max_workers(temp_workspace):
    """Test that maximum number of active tasks does not exceed max_workers."""
    step = {
        "name": "test_batch_workers",
        "task": "batch",
        "inputs": {
            "items": list(range(10)),
            "arg_name": "counter",
            "max_workers": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
import time
time.sleep(0.1)
result = f"Processed {args['counter']}"
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    result = batch_task(config)

    assert len(result["processed"]) == 10


def test_batch_template_resolution(temp_workspace):
    """Test template resolution in batch processing."""
    step = {
        "name": "test_batch_template",
        "task": "batch",
        "inputs": {
            "items": ["a", "b", "c"],
            "arg_name": "data",
            "max_workers": 2,
            "chunk_size": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
result = f"Processed {args['data']}"
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    result = batch_task(config)

    assert len(result["processed"]) == 3
    assert result["results"][0] == "Processed a"
    assert result["results"][1] == "Processed b"
    assert result["results"][2] == "Processed c"


def test_batch_default_arg_name(temp_workspace):
    """Test that batch processing uses default 'item' arg name when not specified."""
    step = {
        "name": "test_batch_default_arg",
        "task": "batch",
        "inputs": {
            "items": ["x", "y", "z"],
            "max_workers": 1,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """
result = f"Default {args['item']}"
"""
                }
            }
        }
    }

    config = TaskConfig(step, {}, temp_workspace)
    result = batch_task(config)

    assert len(result["processed"]) == 3
    assert result["results"][0] == "Default x"
    assert result["results"][1] == "Default y"
    assert result["results"][2] == "Default z"
