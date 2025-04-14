from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from yaml_workflow.tasks.batch_processor import BatchProcessor, process_batch


@pytest.fixture
def sample_items():
    """Generate sample items for testing."""
    return [f"item_{i}" for i in range(10)]


def test_basic_batch_processing(temp_workspace, sample_items):
    """Test basic batch processing with default settings."""
    config = {
        "input": sample_items,
        "batch_size": 3,
        "task": {"type": "shell", "command": "echo 'Processing {{ item }}'"},
    }

    task = BatchProcessor(workspace=temp_workspace, name="test_basic")
    result = process_batch(
        {
            "name": "test_basic",
            "iterate_over": sample_items,
            "processing_task": {
                "task": "shell",
                "command": "echo 'Processing {{ item }}'",
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert len(result["failed_items"]) == 0


def test_batch_with_custom_processor(temp_workspace):
    """Test batch processing with custom item processor."""
    numbers = list(range(1, 11))

    task = BatchProcessor(workspace=temp_workspace, name="test_custom")
    result = process_batch(
        {
            "name": "test_custom",
            "iterate_over": numbers,
            "processing_task": {
                "task": "python",
                "function": "process_item",
                "inputs": {"operation": "multiply", "factor": 2},
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0


def test_batch_with_file_output(temp_workspace, sample_items):
    """Test batch processing with file output for each batch."""
    task = BatchProcessor(workspace=temp_workspace, name="test_output")
    result = process_batch(
        {
            "name": "test_output",
            "iterate_over": sample_items,
            "processing_task": {
                "task": "template",
                "template": "Batch items: {{ batch | join(', ') }}",
                "output": "batch_{{ batch_index }}.txt",
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert (temp_workspace / "batch_0.txt").exists()


def test_batch_with_error_handling(temp_workspace):
    """Test batch processing with error handling."""
    items = ["good1", "error1", "good2", "error2", "good3"]

    task = BatchProcessor(workspace=temp_workspace, name="test_errors")
    result = process_batch(
        {
            "name": "test_errors",
            "iterate_over": items,
            "continue_on_error": True,
            "processing_task": {
                "task": "python",
                "function": "process_item",
                "inputs": {
                    "operation": "custom",
                    "handler": lambda x: (
                        x if "error" not in x else ValueError(f"Error processing {x}")
                    ),
                },
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) == 3
    assert len(result["failed_items"]) == 2


def test_parallel_batch_processing(temp_workspace, sample_items):
    """Test parallel batch processing."""
    task = BatchProcessor(workspace=temp_workspace, name="test_parallel")
    result = process_batch(
        {
            "name": "test_parallel",
            "iterate_over": sample_items,
            "parallel": True,
            "parallel_settings": {"max_workers": 3, "chunk_size": 2},
            "processing_task": {
                "task": "shell",
                "command": "sleep 0.1 && echo 'Processing {{ item }}'",
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0


def test_batch_with_progress_tracking(temp_workspace, sample_items):
    """Test batch processing with progress tracking."""
    progress_updates = []

    def progress_callback(current, total):
        progress_updates.append((current, total))

    task = BatchProcessor(workspace=temp_workspace, name="test_progress")
    result = process_batch(
        {
            "name": "test_progress",
            "iterate_over": sample_items,
            "progress_callback": progress_callback,
            "processing_task": {
                "task": "shell",
                "command": "echo 'Processing {{ item }}'",
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert len(progress_updates) > 0


def test_batch_with_state_persistence(temp_workspace, sample_items):
    """Test batch processing with state persistence."""
    state_file = temp_workspace / ".batch_state" / "test_state_state.json"

    task = BatchProcessor(workspace=temp_workspace, name="test_state")
    result = process_batch(
        {
            "name": "test_state",
            "iterate_over": sample_items,
            "resume_state": True,
            "processing_task": {
                "task": "shell",
                "command": "echo 'Processing {{ item }}'",
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert state_file.exists()


def test_batch_with_custom_aggregator(temp_workspace):
    """Test batch processing with custom result aggregation."""
    numbers = list(range(1, 6))

    task = BatchProcessor(workspace=temp_workspace, name="test_aggregator")
    result = process_batch(
        {
            "name": "test_aggregator",
            "iterate_over": numbers,
            "processing_task": {
                "task": "python",
                "function": "process_item",
                "inputs": {"operation": "multiply", "factor": 2},
                "aggregator": lambda results: {
                    "sum": sum(results),
                    "count": len(results),
                },
            },
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert "aggregated_result" in result


def test_batch_with_dependencies(temp_workspace, sample_items):
    """Test batch processing with inter-batch dependencies."""
    task = BatchProcessor(workspace=temp_workspace, name="test_deps")
    result = process_batch(
        {
            "name": "test_deps",
            "iterate_over": sample_items,
            "processing_task": {
                "task": "template",
                "template": """{% if batch_index > 0 %}Previous batch: {{ previous_batch_result }}{% endif %}
Current items: {{ batch | join(', ') }}""",
                "output": "batch_{{ batch_index }}.txt",
            },
            "preserve_batch_results": True,
        },
        {},
        temp_workspace,
    )

    assert len(result["processed_items"]) > 0
    assert (temp_workspace / "batch_0.txt").exists()


def test_batch_validation(temp_workspace):
    """Test batch processing input validation."""
    # Test invalid batch size
    with pytest.raises(ValueError):
        task = BatchProcessor(workspace=temp_workspace, name="test_validation")
        process_batch(
            {
                "name": "test_validation",
                "iterate_over": [1, 2, 3],
                "chunk_size": 0,
                "processing_task": {"task": "shell", "command": "echo {{ item }}"},
            },
            {},
            temp_workspace,
        )

    # Test invalid input type
    with pytest.raises(TypeError):
        BatchProcessor(
            {
                "input": "not a list",
                "batch_size": 1,
                "task": {"type": "shell", "command": "echo {{ item }}"},
            }
        )
