"""
Task modules for the YAML Workflow Engine.

This package contains various task modules that can be used in workflows.
Each module provides specific functionality that can be referenced in workflow YAML files.
"""

from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar, cast

from jinja2 import Template, UndefinedError

# Type variables for task function signatures
P = ParamSpec("P")
R = TypeVar("R")

# Type for task handlers
TaskHandler = Callable[[Dict[str, Any], Dict[str, Any], Path], Any]

# Registry of task handlers
_task_handlers: Dict[str, TaskHandler] = {}


def register_task(name: str) -> Callable[[TaskHandler], TaskHandler]:
    """
    Decorator to register a task handler.

    Args:
        name: Name of the task type

    Returns:
        Callable: Decorator function
    """

    def decorator(func: TaskHandler) -> TaskHandler:
        _task_handlers[name] = func
        return func

    return decorator


def get_task_handler(task_type: str) -> Optional[TaskHandler]:
    """
    Get a task handler by type.

    Args:
        task_type: Type of task

    Returns:
        Optional[TaskHandler]: Task handler function if found, None otherwise
    """
    return _task_handlers.get(task_type)


def create_task_handler(func: Callable[..., R]) -> TaskHandler:
    """
    Create a task handler that wraps a basic function.

    This wrapper:
    1. Extracts parameters from the step's inputs
    2. Resolves template variables in string inputs using Jinja2
    3. Handles workspace paths if needed

    Args:
        func: The function to wrap as a task handler

    Returns:
        TaskHandler: Wrapped task handler
    """

    @wraps(func)
    def wrapper(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> R:
        # Get inputs, defaulting to empty dict if not present
        inputs = step.get("inputs", {})

        # Process each input value
        processed_inputs = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                # Resolve template variables in strings using Jinja2
                try:
                    template = Template(value)
                    processed_inputs[key] = template.render(**context)
                except UndefinedError as e:
                    raise KeyError(f"Missing template variable in '{value}': {str(e)}")
            else:
                processed_inputs[key] = value

        # Call the function with processed inputs
        return func(**processed_inputs)

    return cast(TaskHandler, wrapper)


# Import task modules
from . import (
    basic_tasks,
    batch_processor,
    file_tasks,
    python_tasks,
    shell_tasks,
    template_tasks,
)

# Register basic tasks
register_task("echo")(create_task_handler(basic_tasks.echo))
register_task("fail")(create_task_handler(basic_tasks.fail))
register_task("hello_world")(create_task_handler(basic_tasks.hello_world))
register_task("add_numbers")(create_task_handler(basic_tasks.add_numbers))
register_task("join_strings")(create_task_handler(basic_tasks.join_strings))
register_task("create_greeting")(create_task_handler(basic_tasks.create_greeting))

# Register file tasks
register_task("write_file")(file_tasks.write_file_task)
register_task("read_file")(file_tasks.read_file_task)
register_task("append_file")(file_tasks.append_file_task)
register_task("copy_file")(file_tasks.copy_file_task)
register_task("move_file")(file_tasks.move_file_task)
register_task("delete_file")(file_tasks.delete_file_task)

# Register shell tasks
register_task("shell")(shell_tasks.shell_task)

# Register template tasks
register_task("template")(template_tasks.render_template)

# Register Python tasks
register_task("python")(python_tasks.python_task)

# Register batch processor
register_task("batch")(batch_processor.process_batch)
