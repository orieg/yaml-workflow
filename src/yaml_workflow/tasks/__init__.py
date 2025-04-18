"""
Task modules for the YAML Workflow Engine.

This package contains various task modules that can be used in workflows.
Each module provides specific functionality that can be referenced in workflow YAML files.
"""

import inspect
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from ..types import TaskHandler
from .config import TaskConfig

# Type variables for task function signatures
R = TypeVar("R")

# Registry of task handlers
_task_registry: Dict[str, TaskHandler] = {}


def register_task(name: str) -> Callable[[TaskHandler], TaskHandler]:
    """Register a task handler.

    Args:
        name: Task name

    Returns:
        Decorator function
    """

    def decorator(handler: TaskHandler) -> TaskHandler:
        _task_registry[name] = handler
        return handler

    return decorator


def get_task_handler(name: str) -> Optional[TaskHandler]:
    """Get a task handler by name.

    Args:
        name: Task name

    Returns:
        Optional[TaskHandler]: Task handler if found
    """
    return _task_registry.get(name)


def create_task_handler(func: Callable[..., R]) -> TaskHandler:
    """
    Create a task handler from a function.

    This function wraps a regular function to make it compatible with the task system.
    The wrapped function will receive its arguments from the task inputs.

    Args:
        func: Function to wrap

    Returns:
        TaskHandler: Task handler function
    """

    @wraps(func)
    def wrapper(config: TaskConfig) -> R:
        # Get function parameters
        sig = inspect.signature(func)
        params = sig.parameters

        # Process inputs with template support
        processed = config.process_inputs()

        # Extract arguments for the function
        kwargs = {}
        for name, param in params.items():
            if name in processed:
                kwargs[name] = processed[name]
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
            else:
                raise ValueError(f"Missing required parameter: {name}")

        # Call the function with extracted arguments
        return func(**kwargs)

    return wrapper


from .basic_tasks import (
    add_numbers,
    create_greeting,
    echo,
    fail,
    hello_world,
    join_strings,
)
from .batch import batch_task
from .file_tasks import (
    append_file_task,
    read_file_task,
    read_json_task,
    read_yaml_task,
    write_file_task,
    write_json_task,
    write_yaml_task,
)
from .python_tasks import print_vars_task

# Import task handlers to ensure they are registered
from .shell_tasks import shell_task
from .template_tasks import render_template

# Register built-in tasks
register_task("shell")(shell_task)
register_task("write_file")(write_file_task)
register_task("read_file")(read_file_task)
register_task("append_file")(append_file_task)
register_task("write_json")(write_json_task)
register_task("read_json")(read_json_task)
register_task("write_yaml")(write_yaml_task)
register_task("read_yaml")(read_yaml_task)
register_task("print_vars")(print_vars_task)
register_task("template")(render_template)
register_task("batch")(batch_task)
register_task("echo")(create_task_handler(echo))
register_task("fail")(create_task_handler(fail))
register_task("hello_world")(create_task_handler(hello_world))
register_task("add_numbers")(create_task_handler(add_numbers))
register_task("join_strings")(create_task_handler(join_strings))
register_task("create_greeting")(create_task_handler(create_greeting))

__all__ = [
    "TaskConfig",
    "TaskHandler",
    "register_task",
    "get_task_handler",
    "create_task_handler",
    "shell_task",
    "write_file_task",
    "read_file_task",
    "append_file_task",
    "write_json_task",
    "read_json_task",
    "write_yaml_task",
    "read_yaml_task",
    "print_vars_task",
    "render_template",
    "batch_task",
    "echo",
    "fail",
    "hello_world",
    "add_numbers",
    "join_strings",
    "create_greeting",
]
