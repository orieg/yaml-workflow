"""
Centralized error handling utilities for tasks.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..exceptions import TaskExecutionError
from .base import get_task_logger, log_task_error


@dataclass
class ErrorContext:
    """Data class to hold context information about a task error."""

    step_name: str
    task_type: str
    error: Exception
    retry_count: int = 0
    task_config: Optional[Dict[str, Any]] = None
    template_context: Optional[Dict[str, Any]] = None


def handle_task_error(context: ErrorContext) -> None:
    """Centralized error handling logic for tasks.

    Logs the error and re-raises it, wrapping non-TaskExecutionErrors.

    Args:
        context: An ErrorContext object containing details about the error.

    Raises:
        TaskExecutionError: Always raises a TaskExecutionError, either the
                           original one or a newly created wrapper.
    """
    # Attempt to get workspace from task_config, default to '.' if missing
    workspace = "."
    if context.task_config and isinstance(
        context.task_config.get("workspace"), (str, Path)
    ):
        workspace = context.task_config["workspace"]
    elif context.task_config:
        # Log a warning if workspace exists but is not the expected type or is None
        logging.warning(
            f"Invalid or missing 'workspace' in task_config for step '{context.step_name}'. Defaulting to '.'"
        )

    logger = get_task_logger(workspace, context.step_name)
    log_task_error(logger, context.error)

    if isinstance(context.error, TaskExecutionError):
        # If it's already a TaskExecutionError, just re-raise it.
        # Its original_error should have been set correctly when it was created.
        raise context.error
    else:
        # Wrap the original standard error in a TaskExecutionError
        raise TaskExecutionError(
            step_name=context.step_name,
            original_error=context.error,
            # Pass task_config if available, otherwise None
            task_config=context.task_config,
        )
