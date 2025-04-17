"""
Batch processing task for handling multiple items in parallel.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List

from ..exceptions import TaskExecutionError
from . import TaskConfig, get_task_handler, register_task


def process_item(
    item: Any,
    task_config: Dict[str, Any],
    context: Dict[str, Any],
    workspace: str,
    arg_name: str,
    chunk_index: int = 0,
    item_index: int = 0,
    total: int = 0,
    chunk_size: int = 0,
) -> Any:
    """
    Process a single batch item using its task configuration.

    Args:
        item: The item to process
        task_config: Task configuration
        context: Task context
        workspace: Workspace path
        arg_name: Name of the argument to use for the item
        chunk_index: Index of the current chunk
        item_index: Index of the item in the overall batch
        total: Total number of items in batch
        chunk_size: Size of each chunk

    Returns:
        Any: Result of processing the item

    Raises:
        TaskExecutionError: If item processing fails
        ValueError: If task type is invalid
    """
    task_type = task_config.get("task")
    if not task_type:
        raise ValueError("Task type is required")

    handler = get_task_handler(task_type)
    if not handler:
        raise ValueError(f"Unknown task type: {task_type}")

    try:
        # Create task config with item in inputs using specified arg name
        step = {
            "name": f"batch_item_{item}",
            "task": task_type,
            "inputs": {**task_config.get("inputs", {}), arg_name: item},
        }

        # Create task config with item in args namespace using specified arg name
        # and batch-specific variables in batch namespace
        item_context = {
            **context,
            "args": {**context.get("args", {}), arg_name: item},
            "batch": {
                "item": item,
                "chunk_index": chunk_index,
                "index": item_index,
                "total": total,
                "chunk_size": chunk_size,
            },
        }

        config = TaskConfig(step, item_context, workspace)
        result = handler(config)
        # If result is a dict with a single 'result' key, unwrap it
        if isinstance(result, dict) and len(result) == 1 and "result" in result:
            return result["result"]
        return result
    except Exception as e:
        raise TaskExecutionError(step_name=f"batch_item_{item}", original_error=e)


@register_task("batch")
def batch_task(config: TaskConfig) -> Dict[str, Any]:
    """
    Process a batch of items using specified task configuration.

    This task processes a list of items in parallel chunks using the specified
    task configuration. Each item is passed to the task as an argument.

    Args:
        config: TaskConfig object containing:
            - items: List of items to process
            - task: Task configuration for processing each item
            - arg_name: Name of the argument to use for each item (default: "item")
            - chunk_size: Optional size of chunks (default: 10)
            - max_workers: Optional maximum worker threads

    Returns:
        Dict containing:
            - processed: List of successfully processed items
            - failed: List of failed items with errors
            - results: List of processing results
            - stats: Processing statistics

    Example YAML usage:
        ```yaml
        steps:
          - name: process_data
            task: batch
            inputs:
              items: [5, 7, 12]
              arg_name: x  # Name items will be passed as
              chunk_size: 2
              max_workers: 2
              task:
                task: python
                inputs:
                  operation: multiply
                  factor: 2
        ```
    """
    # Process inputs with template resolution
    processed = config.process_inputs()

    # Get required parameters
    items = processed.get("items")
    if items is None:
        raise ValueError("items parameter is required")

    # Ensure items is a list
    if not isinstance(items, list):
        raise ValueError("items must be a list after template resolution")

    if not items:
        return {
            "processed": [],
            "failed": [],
            "results": [],
            "stats": {
                "total": 0,
                "processed": 0,
                "failed": 0,
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "success_rate": 100.0,
            },
        }

    task_config = processed.get("task")
    if not task_config:
        raise ValueError("task configuration is required")

    # Get optional parameters with defaults
    chunk_size = int(processed.get("chunk_size", 10))
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    max_workers = int(
        processed.get("max_workers", min(chunk_size, os.cpu_count() or 1))
    )
    if max_workers <= 0:
        raise ValueError("max_workers must be greater than 0")

    # Get argument name to use for items, defaulting to "item"
    arg_name = processed.get("arg_name", "item")

    # Initialize state
    state = {
        "processed": [],
        "failed": [],
        "results": [],
        "stats": {
            "total": len(items),
            "processed": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat(),
        },
    }

    # Store results with their indices for ordering
    ordered_results = []
    ordered_processed = []
    ordered_failed = []

    # Process items in chunks
    for chunk_index, chunk_start in enumerate(range(0, len(items), chunk_size)):
        chunk = items[chunk_start : chunk_start + chunk_size]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            # Submit tasks for chunk
            for item_index, item in enumerate(chunk):
                future = executor.submit(
                    process_item,
                    item,
                    task_config,
                    config._context,
                    config.workspace,
                    arg_name,
                    chunk_index,
                    chunk_start + item_index,
                    len(items),  # total
                    chunk_size,  # chunk_size
                )
                futures[future] = (item, chunk_start + item_index)

            # Process completed futures
            for future in as_completed(futures):
                item, index = futures[future]
                try:
                    result = future.result()
                    ordered_processed.append((index, item))
                    ordered_results.append((index, result))
                    state["stats"]["processed"] += 1
                except Exception as e:
                    ordered_failed.append((index, {"item": item, "error": str(e)}))
                    state["stats"]["failed"] += 1

    # Sort results by index and extract values
    state["processed"] = [item for _, item in sorted(ordered_processed)]
    state["results"] = [result for _, result in sorted(ordered_results)]
    state["failed"] = [error for _, error in sorted(ordered_failed)]

    # Add completion statistics
    state["stats"]["end_time"] = datetime.now().isoformat()
    state["stats"]["success_rate"] = (
        state["stats"]["processed"] / state["stats"]["total"]
    ) * 100.0

    return state
