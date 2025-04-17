"""Tests for the batch task implementation."""

import pytest
from pathlib import Path
from typing import Dict, Any, List

from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.batch import batch_task
from yaml_workflow.exceptions import TaskExecutionError, TemplateError


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Create a temporary workspace for testing."""
    return tmp_path


@pytest.fixture
def basic_context() -> Dict[str, Any]:
    """Create a basic context with namespaces."""
    return {
        "args": {
            "test_arg": "value1",
            "debug": True,
            "items": ["apple", "banana", "cherry"],
            "count": 3
        },
        "env": {"test_env": "value2"},
        "steps": {"previous_step": {"output": "value3"}},
        "root_var": "value4"
    }


@pytest.fixture
def sample_items() -> List[str]:
    """Generate sample items for testing."""
    return [f"item_{i}" for i in range(10)]


def test_batch_basic(workspace, basic_context, sample_items):
    """Test basic batch task functionality."""
    step = {
        "name": "test_batch",
        "task": "batch",
        "inputs": {
            "items": sample_items,
            "task": {
                "task": "python",
                "inputs": {
                    "code": "result = f'Processing {item}'"
                }
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)
    
    assert len(result["processed"]) == len(sample_items)
    assert len(result["failed"]) == 0
    assert len(result["results"]) == len(sample_items)
    assert result["stats"]["total"] == len(sample_items)
    assert result["stats"]["processed"] == len(sample_items)
    assert result["stats"]["failed"] == 0
    assert result["stats"]["success_rate"] == 100.0


def test_batch_with_failures(workspace, basic_context):
    """Test batch processing with some failing items."""
    items = ["success1", "fail1", "success2", "fail2"]
    step = {
        "name": "test_batch_failures",
        "task": "batch",
        "inputs": {
            "items": items,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """if "fail" in item:
    raise ValueError(f"Failed to process {item}")
result = f"Processed {item}"\
"""
                }
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)
    
    assert len(result["processed"]) == 2
    assert len(result["failed"]) == 2
    assert result["stats"]["processed"] == 2
    assert result["stats"]["failed"] == 2
    assert result["stats"]["success_rate"] == 50.0


def test_batch_chunk_processing(workspace, basic_context, sample_items):
    """Test batch processing with specific chunk size."""
    step = {
        "name": "test_batch_chunks",
        "task": "batch",
        "inputs": {
            "items": sample_items,
            "chunk_size": 3,
            "max_workers": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """result = f'Processing {item} in chunk {batch["chunk_index"]}'\
"""
                }
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)
    
    assert len(result["processed"]) == len(sample_items)
    assert result["stats"]["processed"] == len(sample_items)


def test_batch_template_resolution(workspace, basic_context):
    """Test template resolution in batch processing."""
    # Extend context with more test data
    basic_context["args"]["prefix"] = "fruit"
    basic_context["args"]["condition"] = True
    basic_context["args"]["multiplier"] = 2
    basic_context["args"]["items"] = ["apple", "banana", "cherry"]

    step = {
        "name": "test_batch_template",
        "task": "batch",
        "inputs": {
            # Test list template resolution with filter
            "items": '{{ args["items"] | map("upper") | list }}',
            "chunk_size": '{{ args["multiplier"] }}',  # Template in configuration
            "task": {
                "task": "python",
                "inputs": {
                    # Test nested template resolution and conditional logic
                    "code": """
# Access the original item through the batch context
original = batch["item"].lower()  # Convert back to lowercase to match input
index = batch["index"]

result = {
    'item': batch["item"],  # Use the uppercase version from batch context
    'prefix': '{{ args["prefix"] }}',
    'conditional': '{{ "yes" if args["condition"] else "no" }}',
    'original': original
}"""
                }
            }
        }
    }

    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)

    # Verify batch processing results
    assert len(result["processed"]) == 3, "Should process all items"
    assert len(result["failed"]) == 0, "Should have no failed items"
    assert result["stats"]["success_rate"] == 100.0, "Should have 100% success rate"

    # Verify individual item processing
    expected_items = ["APPLE", "BANANA", "CHERRY"]
    for i, item in enumerate(result["processed"]):
        result_data = result["results"][i]  # Access the raw result data
        assert result_data["item"] == expected_items[i], f"Item {i} should be uppercase"
        assert result_data["prefix"] == "fruit", "Prefix should be set correctly"
        assert result_data["conditional"] == "yes", "Conditional should evaluate to yes"
        assert result_data["original"] == basic_context["args"]["items"][i], "Original item should match input"


def test_batch_validation(workspace, basic_context):
    """Test batch task validation."""
    # Test missing items
    step = {
        "name": "test_batch_validation",
        "task": "batch",
        "inputs": {
            "task": {
                "task": "python",
                "inputs": {"code": "result = 'test'"}
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(ValueError, match="items parameter is required"):
        batch_task(config)
    
    # Test missing task config
    step = {
        "name": "test_batch_validation",
        "task": "batch",
        "inputs": {
            "items": ["item1", "item2"]
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(ValueError, match="task configuration is required"):
        batch_task(config)
    
    # Test invalid chunk size
    step = {
        "name": "test_batch_validation",
        "task": "batch",
        "inputs": {
            "items": ["item1", "item2"],
            "chunk_size": 0,
            "task": {
                "task": "python",
                "inputs": {"code": "result = 'test'"}
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
        batch_task(config)
    
    # Test invalid max_workers
    step = {
        "name": "test_batch_validation",
        "task": "batch",
        "inputs": {
            "items": ["item1", "item2"],
            "max_workers": 0,
            "task": {
                "task": "python",
                "inputs": {"code": "result = 'test'"}
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(ValueError, match="max_workers must be greater than 0"):
        batch_task(config)


def test_batch_context_variables(workspace, basic_context, sample_items):
    """Test batch context variables in item processing."""
    step = {
        "name": "test_batch_context",
        "task": "batch",
        "inputs": {
            "items": sample_items[:3],  # Use first 3 items
            "chunk_size": 2,
            "task": {
                "task": "python",
                "inputs": {
                    "code": """result = {
        'item': batch['item'],
        'index': batch['index'],
        'total': batch['total'],
        'chunk_index': batch['chunk_index'],
        'chunk_size': batch['chunk_size']
    }"""
                }
            }
        }
    }

    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)

    assert len(result["results"]) == 3
    for i, res in enumerate(result["results"]):
        assert res["item"] == sample_items[i]
        assert res["index"] == i
        assert res["total"] == 3
        assert res["chunk_index"] == (0 if i < 2 else 1)  # First chunk: 0,1; Second chunk: 2
        assert res["chunk_size"] == 2


def test_batch_empty_items(workspace, basic_context):
    """Test batch processing with empty items list."""
    step = {
        "name": "test_batch_empty",
        "task": "batch",
        "inputs": {
            "items": [],
            "task": {
                "task": "python",
                "inputs": {"code": "result = 'test'"}
            }
        }
    }
    
    config = TaskConfig(step, basic_context, workspace)
    result = batch_task(config)
    
    assert len(result["processed"]) == 0
    assert len(result["failed"]) == 0
    assert len(result["results"]) == 0
    assert result["stats"]["total"] == 0
    assert result["stats"]["processed"] == 0
    assert result["stats"]["failed"] == 0
    assert result["stats"]["success_rate"] == 100.0 