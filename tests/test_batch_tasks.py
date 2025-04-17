from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json

import pytest

from yaml_workflow.tasks.batch_processor import BatchProcessor, process_batch
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.batch_context import BatchContext


@pytest.fixture
def sample_items():
    """Generate sample items for testing."""
    return [f"item_{i}" for i in range(10)]


@pytest.fixture
def task_config(temp_workspace):
    """Create a task config for testing."""
    return TaskConfig(
        {
            "name": "test_batch",
            "task": "batch",
            "inputs": {
                "items": [f"item_{i}" for i in range(3)],
                "processing_task": {
                    "task": "shell",
                    "command": "echo 'Processing {{ item }}'"
                }
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        temp_workspace
    )


def test_batch_context_initialization(task_config):
    """Test BatchContext initialization."""
    context = BatchContext(task_config)
    assert context.name == "test_batch"
    assert context.workspace == task_config.workspace
    assert context._context == task_config._context


def test_batch_context_item_context(task_config):
    """Test creation of item-specific context."""
    context = BatchContext(task_config)
    item_context = context.create_item_context("test_item", 0)
    
    assert item_context["batch"]["item"] == "test_item"
    assert item_context["batch"]["index"] == 0
    assert item_context["batch"]["name"] == "test_batch"
    assert "args" in item_context
    assert "env" in item_context
    assert "steps" in item_context


def test_batch_context_error_handling(task_config):
    """Test error context generation."""
    context = BatchContext(task_config)
    error = ValueError("Test error")
    error_context = context.get_error_context(error)
    
    assert error_context["error"] == str(error)
    assert "available_variables" in error_context
    assert "namespaces" in error_context


def test_basic_batch_processing(temp_workspace, sample_items):
    """Test basic batch processing with TaskConfig."""
    config = TaskConfig(
        {
            "name": "test_basic",
            "task": "batch",
            "inputs": {
                "items": sample_items,
                "processing_task": {
                    "task": "shell",
                    "command": "echo 'Processing {{ item }}'"
                }
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        temp_workspace
    )
    
    result = process_batch(config)
    assert len(result["processed_items"]) > 0
    assert len(result["failed_items"]) == 0


def test_batch_with_custom_processor(temp_workspace):
    """Test batch processing with custom processor using TaskConfig."""
    numbers = list(range(1, 11))
    config = TaskConfig(
        {
            "name": "test_custom",
            "task": "batch",
            "inputs": {
                "items": numbers,
                "processing_task": {
                    "task": "python",
                    "function": "process_item",
                    "inputs": {"operation": "multiply", "factor": 2}
                }
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        temp_workspace
    )
    
    result = process_batch(config)
    assert len(result["processed_items"]) > 0
    assert all(isinstance(item, int) for item in result["processed_items"])


def test_batch_with_error_handling(temp_workspace):
    """Test batch processing error handling with namespaces."""
    items = ["good1", "error1", "good2", "error2", "good3"]
    config = TaskConfig(
        {
            "name": "test_errors",
            "task": "batch",
            "inputs": {
                "items": items,
                "continue_on_error": True,
                "processing_task": {
                    "task": "python",
                    "function": "process_item",
                    "inputs": {
                        "operation": "custom",
                        "handler": lambda x: (
                            x if "error" not in x else ValueError(f"Error processing {x}")
                        )
                    }
                }
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        temp_workspace
    )
    
    result = process_batch(config)
    assert len(result["processed_items"]) == 3
    assert len(result["failed_items"]) == 2
    assert all("error" not in item for item in result["processed_items"])


def test_batch_with_state_persistence(temp_workspace, sample_items):
    """Test batch processing with state persistence and namespaces."""
    config = TaskConfig(
        {
            "name": "test_state",
            "task": "batch",
            "inputs": {
                "items": sample_items,
                "resume_state": True,
                "processing_task": {
                    "task": "shell",
                    "command": "echo 'Processing {{ item }}'"
                }
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        temp_workspace
    )
    
    result = process_batch(config)
    assert len(result["processed_items"]) > 0
    
    # Verify state file exists and contains namespace information
    state_file = temp_workspace / ".batch_state" / "test_state_state.json"
    assert state_file.exists()
    state_data = json.loads(state_file.read_text())
    assert "namespaces" in state_data
    assert "batch" in state_data["namespaces"]


def test_batch_validation(temp_workspace):
    """Test batch processing validation with TaskConfig."""
    # Test invalid batch size
    with pytest.raises(ValueError):
        config = TaskConfig(
            {
                "name": "test_validation",
                "task": "batch",
                "inputs": {
                    "items": [1, 2, 3],
                    "chunk_size": 0,
                    "processing_task": {
                        "task": "shell",
                        "command": "echo {{ item }}"
                    }
                }
            },
            {"args": {}, "env": {}, "steps": {}},
            temp_workspace
        )
        process_batch(config)

    # Test invalid namespace access
    with pytest.raises(ValueError):
        config = TaskConfig(
            {
                "name": "test_validation",
                "task": "batch",
                "inputs": {
                    "items": [1, 2, 3],
                    "processing_task": {
                        "task": "shell",
                        "command": "echo {{ invalid_namespace.item }}"
                    }
                }
            },
            {"args": {}, "env": {}, "steps": {}},
            temp_workspace
        )
        process_batch(config)


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
