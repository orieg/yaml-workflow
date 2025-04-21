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
            sig = inspect.signature(func)
            params = sig.parameters

            # Simplified Check: Handle tasks taking only TaskConfig first
            if (
                list(params.keys()) == ["config"]
                and params["config"].annotation is TaskConfig
            ):
                return func(config)

            processed = config.process_inputs()
            kwargs = {}
            pos_args = []
            extra_kwargs: Dict[str, Any] = {}  # For **kwargs
            unmapped_inputs = (
                processed.copy()
            )  # Track inputs not mapped to named params

            # Identify special parameter names (*args, **kwargs, config, context)
            var_arg_name: Optional[str] = None
            kw_arg_name: Optional[str] = None
            config_param_name: Optional[str] = None
            context_param_name: Optional[str] = None

            for name, param in params.items():
                if param.annotation is TaskConfig:
                    config_param_name = name
                elif name == "context" and param.annotation in (
                    Dict[str, Any],
                    dict,
                    Any,
                ):
                    context_param_name = name
                elif param.kind == param.VAR_POSITIONAL:
                    var_arg_name = name
                elif param.kind == param.VAR_KEYWORD:
                    kw_arg_name = name

            # Map processed inputs to function arguments
            for name, param in params.items():
                if name == config_param_name or name == context_param_name:
                    continue  # Skip special params for now
                if name == var_arg_name or name == kw_arg_name:
                    continue  # Skip *args/**kwargs for now

                if name in processed:
                    kwargs[name] = processed[name]
                    del unmapped_inputs[name]  # Mark as mapped
                elif param.default is inspect.Parameter.empty:
                    # Check if required named param is missing from inputs
                    raise ValueError(f"Missing required parameter: {name}")
                # else: use default value (implicitly handled by function call)

            # Handle remaining unmapped inputs
            if var_arg_name and var_arg_name in processed:
                # If *args name exists as an input key (e.g., join_strings(strings=...))
                arg_input = processed[var_arg_name]
                pos_args = (
                    list(arg_input)
                    if isinstance(arg_input, (list, tuple))
                    else [arg_input]
                )
                if var_arg_name in unmapped_inputs:
                    del unmapped_inputs[var_arg_name]
            elif var_arg_name:
                # If *args exists but no input key matches, maybe map remaining unmapped inputs?
                # This is ambiguous. Let's require explicit mapping for now.
                # If len(unmapped_inputs) == 1 and var_arg_name:
                #      pos_args = list(unmapped_inputs.values())[0]
                #      if not isinstance(pos_args, list): pos_args = [pos_args]
                #      unmapped_inputs.clear()
                pass  # Requires explicit input name for *args mapping

            # Assign remaining unmapped inputs to **kwargs if available
            if kw_arg_name and unmapped_inputs:
                kwargs[kw_arg_name] = unmapped_inputs
            elif unmapped_inputs and not var_arg_name:
                # If unmapped inputs remain and there's no **kwargs or *args to catch them,
                # it might indicate an issue (e.g., typo in YAML input name).
                # However, the function call itself will raise TypeError if unexpected args are passed.
                # Let the function call handle the final validation for unexpected kwargs.
                pass

            # Inject config and context if needed
            if config_param_name:
                kwargs[config_param_name] = config
            if context_param_name:
                # Access the protected context member
                kwargs[context_param_name] = (
                    config._context
                )  # Pass the full context dict

            # Call the function
            try:
                return func(*pos_args, **kwargs)
            except TypeError as e:
                arg_summary = f"pos_args={pos_args}, kwargs={list(kwargs.keys())}"
                logging.error(
                    f"TypeError calling task '{task_name}': {e}. Call info: {arg_summary}"
                )
                raise

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
from .file_utils import list_files
from .python_tasks import print_vars_task
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
