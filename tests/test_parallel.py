import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.tasks.batch_processor import BatchProcessor, process_batch


@pytest.fixture
def sample_items():
    """Create sample items for batch processing."""
    return [f"item_{i}" for i in range(10)]


@pytest.fixture
def parallel_workflow(temp_workspace):
    """Create a workflow file with parallel tasks."""
    workflow_content = """name: parallel_test
description: Test parallel execution

steps:
  - name: parallel_step
    task: batch_processor
    iterate_over:
      - item1
      - item2
      - item3
    max_workers: 3
    chunk_size: 3
    processing_task:
      task: shell
      command: "sleep 0.5 && echo 'Processing {{ item }}'"
"""
    workflow_file = temp_workspace / "parallel_workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


def test_parallel_execution_time(parallel_workflow):
    """Test that parallel execution is faster than sequential."""
    engine = WorkflowEngine(str(parallel_workflow))

    start_time = time.time()
    result = engine.run()
    end_time = time.time()

    # With 3 tasks of 0.5s each, parallel execution should take ~0.5s
    # while sequential would take ~1.5s
    execution_time = end_time - start_time
    assert execution_time < 1.0  # Allow some overhead
    assert result["status"] == "completed"


def test_batch_processing_results(temp_workspace):
    """Test that batch processing returns correct results."""
    step = {
        "name": "test_batch",
        "parallel": True,
        "iterate_over": [1, 2, 3],
        "parallel_settings": {"max_workers": 3, "chunk_size": 3},
        "processing_task": {
            "task": "python",
            "inputs": {"operation": "multiply", "factor": 2},
        },
    }

    result = process_batch(step, {}, temp_workspace)
    assert len(result["processed_items"]) == 3
    assert all(x == y * 2 for x, y in zip(result["processed_items"], [1, 2, 3]))


def test_batch_error_handling(temp_workspace):
    """Test error handling in batch processing."""
    step = {
        "name": "test_batch_errors",
        "parallel": True,
        "iterate_over": [1, 2, 0, 4],  # 0 will cause division error
        "parallel_settings": {"max_workers": 2, "chunk_size": 2},
        "processing_task": {
            "task": "python",
            "inputs": {"operation": "divide", "divisor": 10},
        },
    }

    result = process_batch(step, {}, temp_workspace)
    assert len(result["processed_items"]) == 3  # Should process 1, 2, and 4
    assert len(result["failed_items"]) == 1  # Should fail on 0


def test_batch_resume(temp_workspace):
    """Test batch processing with resume capability."""
    step = {
        "name": "test_resume",
        "parallel": True,
        "iterate_over": list(range(5)),
        "resume_state": True,
        "parallel_settings": {"max_workers": 2, "chunk_size": 2},
        "processing_task": {
            "task": "python",
            "inputs": {"operation": "multiply", "factor": 2},
        },
    }

    # First run
    result1 = process_batch(step, {}, temp_workspace)
    assert len(result1["processed_items"]) == 5
    assert all(x == y * 2 for x, y in zip(result1["processed_items"], range(5)))


def test_batch_max_workers(temp_workspace):
    """Test respecting max_workers setting."""
    active_tasks = 0
    max_active_tasks = 0

    def task_with_counter():
        nonlocal active_tasks, max_active_tasks
        active_tasks += 1
        max_active_tasks = max(max_active_tasks, active_tasks)
        time.sleep(0.1)
        active_tasks -= 1
        return True

    step = {
        "name": "test_max_workers",
        "parallel": True,
        "iterate_over": list(range(10)),
        "parallel_settings": {"max_workers": 2, "chunk_size": 2},
        "processing_task": {
            "task": "python",
            "inputs": {"operation": "custom", "handler": task_with_counter},
        },
    }

    result = process_batch(step, {}, temp_workspace)
    assert max_active_tasks <= 2
    assert len(result["processed_items"]) == 10
