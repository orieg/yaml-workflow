"""Type definitions for the workflow engine."""

from typing import Any, Callable

from .tasks.config import TaskConfig

# Type for task handlers
TaskHandler = Callable[[TaskConfig], Any]
