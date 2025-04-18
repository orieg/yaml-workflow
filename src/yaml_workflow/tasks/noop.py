"""
No-operation task for testing and demonstration.

This task simply returns its inputs and some metadata about the task execution.
"""

from pathlib import Path
from typing import Any, Dict

from ..exceptions import TaskExecutionError
from . import TaskConfig, register_task


@register_task("noop")
def noop_task(config: TaskConfig) -> Dict[str, Any]:
    """
    No-operation task that returns its inputs and metadata.

    This task is useful for testing and demonstrating the workflow engine's
    features without performing any actual operations.

    Args:
        config: Task configuration with:
            - should_fail: Optional boolean to simulate task failure

    Returns:
        Dict[str, Any]: Task inputs and metadata

    Raises:
        TaskExecutionError: If should_fail is True
    """
    processed = config.process_inputs()

    # Get task name, defaulting to "noop" if not provided
    task_name = config.name if config.name is not None else "noop"

    # Demonstrate error handling if should_fail is True
    if processed.get("should_fail", False):
        raise TaskExecutionError(
            step_name=task_name, original_error=Exception("Task failed as requested")
        )

    # Return processed inputs and some metadata to demonstrate output handling
    return {
        "processed_inputs": processed,
        "task_name": task_name,
        "task_type": config.type,
        "available_variables": config.get_available_variables(),
    }
