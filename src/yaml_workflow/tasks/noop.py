"""
No-operation task for testing and demonstration.

This task simply returns its inputs and some metadata about the task execution.
"""

from pathlib import Path
from typing import Any, Dict

from . import TaskConfig, register_task
from .base import get_task_logger, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error


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
        TaskExecutionError: If should_fail is True (via handle_task_error)
    """
    task_name = str(config.name or "noop_task")
    task_type = str(config.type or "noop")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)

        processed = config.process_inputs()

        # Demonstrate error handling if should_fail is True
        if processed.get("should_fail", False):
            error = Exception("Task failed as requested")
            context = ErrorContext(
                step_name=task_name,
                task_type=task_type,
                error=error,
                task_config=config.step,
                template_context=config._context,
            )
            handle_task_error(context)
            # handle_task_error always raises, so this is unreachable
            return {}  # Add return for type checker

        # Return processed inputs and some metadata to demonstrate output handling
        result = {
            "processed_inputs": processed,
            "task_name": task_name,
            "task_type": config.type,
            "available_variables": config.get_available_variables(),
        }
        log_task_result(logger, result)
        return result

    except Exception as e:
        # Catch any other unexpected errors during setup/input processing
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable
