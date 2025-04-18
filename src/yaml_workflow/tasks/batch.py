"""
Batch processing task for handling multiple items in parallel.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

from ..exceptions import TaskExecutionError
from . import TaskConfig, get_task_handler, register_task
from .error_handling import ErrorContext, handle_task_error


def process_item(
    item: Any,
    task_config: Dict[str, Any],
    context: Dict[str, Any],
    workspace: Path,
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
    try:
        task_type = task_config.get("task")
        if not task_type:
            # Raise ValueError for config issue before task execution attempt
            raise ValueError(
                "Task type is required within the batch task configuration"
            )

        handler = get_task_handler(task_type)
        if not handler:
            # Raise ValueError for config issue before task execution attempt
            raise ValueError(
                f"Unknown task type specified in batch task config: {task_type}"
            )

        # Create task config with item in inputs using specified arg name
        step = {
            # Use a more informative name including original step name if available
            "name": f"batch_item_{item}_in_{task_config.get('name', 'batch')}",
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
        # Remove unwrapping logic - return the full result dict from the handler
        # if isinstance(result, dict) and len(result) == 1 and "result" in result:
        #     return result["result"]
        return result
    except Exception as e:
        # Centralized error handling for exceptions during item processing
        err_context = ErrorContext(
            # Use the specific item step name generated above
            step_name=step["name"],
            task_type=str(task_type),  # Ensure type is str
            error=e,
            # Pass the sub-task config, not the main batch config
            task_config=step,
            # Include the item context used for this specific item
            template_context=item_context,
        )
        handle_task_error(err_context)
        # handle_task_error always raises, so return is unreachable but satisfies type checker
        return None


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
    task_name = config.name or "batch_task"
    task_type = config.type or "batch"

    try:
        # Process inputs with template resolution
        processed = config.process_inputs()

        # Get required parameters
        items = processed.get("items")
        if items is None:
            raise ValueError("'items' parameter is required for batch task")

        # Ensure items is a list
        if not isinstance(items, list):
            raise ValueError("'items' must resolve to a list after template processing")

        task_config = processed.get("task")
        if not task_config:
            raise ValueError(
                "'task' configuration is required within batch task inputs"
            )

        # Get optional parameters with defaults
        chunk_size = int(processed.get("chunk_size", 10))
        if chunk_size <= 0:
            raise ValueError("'chunk_size' must be greater than 0")

        max_workers = int(
            processed.get("max_workers", min(chunk_size, os.cpu_count() or 1))
        )
        if max_workers <= 0:
            raise ValueError("'max_workers' must be greater than 0")

        # Handle case where items list is empty after processing
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

        # Get argument name to use for items, defaulting to "item"
        arg_name = processed.get("arg_name", "item")

        # Initialize state
        state: Dict[str, Any] = {
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
        ordered_results: List[Tuple[int, Any]] = []
        ordered_processed: List[Tuple[int, Any]] = []
        ordered_failed: List[Tuple[int, Dict[str, Any]]] = []

        # Process items in chunks
        for chunk_index, chunk_start in enumerate(range(0, len(items), chunk_size)):
            chunk = cast(List[Any], items[chunk_start : chunk_start + chunk_size])

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}

                # Submit tasks for chunk
                for item_index, item in enumerate(chunk):
                    # Pass the sub-task config, not the main batch config inputs
                    sub_task_config_for_item = task_config
                    future = executor.submit(
                        process_item,
                        item,  # item: Any
                        sub_task_config_for_item,  # task_config: Dict[str, Any]
                        config._context,  # context: Dict[str, Any]
                        config.workspace,  # workspace: Path
                        arg_name,  # arg_name: str
                        chunk_index,  # chunk_index: int
                        chunk_start + item_index,  # item_index: int
                        len(items),  # total: int
                        chunk_size,  # chunk_size: int
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
                        # Capture the error from process_item (already wrapped if needed)
                        error_info = {"item": item, "error": str(e)}
                        # If it's a TaskExecutionError, add more details if possible
                        if isinstance(e, TaskExecutionError):
                            error_info["step_name"] = e.step_name
                            if e.task_config:
                                error_info["task_config"] = e.task_config
                        ordered_failed.append((index, error_info))
                        state["stats"]["failed"] += 1

        # Sort results by index and extract values
        state["processed"] = [item for _, item in sorted(ordered_processed)]
        state["results"] = [result for _, result in sorted(ordered_results)]
        state["failed"] = [error for _, error in sorted(ordered_failed)]

        # Add completion statistics
        state["stats"]["end_time"] = datetime.now().isoformat()
        total_items = state["stats"]["total"]
        processed_items = state["stats"]["processed"]
        state["stats"]["success_rate"] = (
            (processed_items / total_items) * 100.0
            if total_items > 0
            else 100.0  # Avoid division by zero if total is 0
        )

        return state

    except Exception as e:
        # Centralized error handling for exceptions during batch setup/config
        err_context = ErrorContext(
            step_name=str(task_name),
            task_type=str(task_type),
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(err_context)
        # handle_task_error always raises, so return is unreachable but satisfies type checker
        return {}
