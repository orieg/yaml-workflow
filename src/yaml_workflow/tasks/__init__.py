"""
Task modules for the YAML Workflow Engine.

This package contains various task modules that can be used in workflows.
Each module provides specific functionality that can be referenced in workflow YAML files.
"""

import inspect
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from ..types import TaskHandler
from .config import TaskConfig

# Type variables for task function signatures
R = TypeVar("R")

# Registry of task handlers
_task_registry: Dict[str, TaskHandler] = {}


def register_task(
    name: Optional[str] = None,
) -> Callable[..., Callable[[TaskConfig], R]]:
    """Decorator to register a function as a workflow task."""

    def task_wrapper(func: Callable[..., R]) -> Callable[[TaskConfig], R]:
        task_name = name or func.__name__

        @wraps(func)
        def wrapper(config: TaskConfig) -> R:
            # Get function parameters
            sig = inspect.signature(func)
            params = sig.parameters

            # Check if the function expects only the TaskConfig object
            if (
                list(params.keys()) == ["config"]
                and params["config"].annotation is TaskConfig
            ):
                # Case 1: Call directly with config
                return func(config)
            else:
                # Case 2: Process inputs and potentially pass config explicitly
                processed = config.process_inputs()
                kwargs = {}
                func_params = inspect.signature(func).parameters
                needs_config_arg = "config" in func_params

                for name, param in func_params.items():
                    if (
                        name == "config"
                    ):  # Always skip putting config in kwargs from inputs
                        continue
                    if name in processed:
                        kwargs[name] = processed[name]
                    elif param.default is not inspect.Parameter.empty:
                        kwargs[name] = param.default
                    else:
                        # Raise error only if a non-config required parameter is missing
                        raise ValueError(f"Missing required parameter: {name}")

                # Call the original function, adding config if needed
                if needs_config_arg:
                    # Ensure we don't somehow add config twice if it was also in inputs
                    if "config" in kwargs:
                        del kwargs["config"]  # Should not happen due to loop skip
                    return func(config=config, **kwargs)  # Pass config explicitly
                else:
                    return func(**kwargs)  # Original call without explicit config

        _task_registry[task_name] = wrapper
        return wrapper

    return task_wrapper


def get_task_handler(name: str) -> Optional[TaskHandler]:
    """Get a task handler by name.

    Args:
        name: Task name

    Returns:
        Optional[TaskHandler]: Task handler if found
    """
    handler = _task_registry.get(name)
    # print(f"--- get_task_handler requested: '{name}', found: {handler} ---") # DEBUG
    logging.debug(f"Retrieved handler for task '{name}': {handler}")
    return handler


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

# Explicit registration calls (ensure these tasks don't use @register_task internally)
# If a task like `shell_task` already uses `@register_task()`, this explicit call is redundant.
# register_task("shell")(shell_task)
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

# Removed redundant register_task calls for basic_tasks (echo, fail, etc.)
# They are now registered by decorators within basic_tasks.py via the import above.

__all__ = [
    "TaskConfig",
    "TaskHandler",
    "register_task",
    "get_task_handler",
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
