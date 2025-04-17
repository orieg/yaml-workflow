"""
Task modules for the YAML Workflow Engine.

This package contains various task modules that can be used in workflows.
Each module provides specific functionality that can be referenced in workflow YAML files.
"""

import re
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, ParamSpec, TypeVar, cast

from jinja2 import StrictUndefined, UndefinedError

from ..exceptions import TemplateError
from ..template import TemplateEngine

# Type variables for task function signatures
P = ParamSpec("P")
R = TypeVar("R")

# Type for task handlers
TaskHandler = Callable[[Dict[str, Any], Dict[str, Any], Path], Any]
ConfigTaskHandler = Callable[["TaskConfig"], Dict[str, Any]]

# Registry of task handlers
_task_handlers: Dict[str, TaskHandler | ConfigTaskHandler] = {}


class TaskConfig:
    """Configuration class for task handlers with namespace support."""

    def __init__(self, step: Dict[str, Any], context: Dict[str, Any], workspace: Path):
        """
        Initialize task configuration.

        Args:
            step: Step configuration from workflow
            context: Execution context with namespaces
            workspace: Workspace path
        """
        self.name = step.get("name")
        self.type = step.get("task")
        self.inputs = step.get("inputs", {})
        self._context = context
        self.workspace = workspace
        self._processed_inputs: Dict[str, Any] = {}
        self._template_engine = TemplateEngine()

    def get_variable(self, name: str, namespace: Optional[str] = None) -> Any:
        """
        Get a variable with namespace support.

        Args:
            name: Variable name
            namespace: Optional namespace (args, env, steps)

        Returns:
            Any: Variable value if found
        """
        if namespace:
            return self._context.get(namespace, {}).get(name)
        return self._context.get(name)

    def get_available_variables(self) -> Dict[str, List[str]]:
        """
        Get available variables by namespace.

        Returns:
            Dict[str, List[str]]: Available variables in each namespace
        """
        return {
            "args": list(self._context.get("args", {}).keys()),
            "env": list(self._context.get("env", {}).keys()),
            "steps": list(self._context.get("steps", {}).keys()),
            "root": [
                k for k in self._context.keys() if k not in ["args", "env", "steps"]
            ],
        }

    def process_inputs(self) -> Dict[str, Any]:
        """
        Process task inputs with template resolution.

        Recursively processes all string values in the inputs dictionary,
        including nested dictionaries and lists.

        Returns:
            Dict[str, Any]: Processed inputs with resolved templates
        """
        if not self._processed_inputs:
            # Create a flattened context for template processing
            template_context = {
                "args": self._context.get("args", {}),
                "env": self._context.get("env", {}),
                "steps": self._context.get("steps", {}),
                **{
                    k: v
                    for k, v in self._context.items()
                    if k not in ["args", "env", "steps"]
                },
            }

            self._processed_inputs = self._process_value(self.inputs, template_context)
        return self._processed_inputs

    def _process_value(self, value: Any, template_context: Dict[str, Any]) -> Any:
        """
        Recursively process a value with template resolution.

        Args:
            value: Value to process
            template_context: Template context for variable resolution

        Returns:
            Any: Processed value with resolved templates
        """
        if isinstance(value, str):
            try:
                result = self._template_engine.process_template(value, template_context)
                # Try to convert string results back to their original type
                if result == "True":
                    return True
                elif result == "False":
                    return False
                try:
                    # First try to evaluate as a Python literal (for lists, dicts, etc.)
                    import ast

                    try:
                        return ast.literal_eval(result)
                    except (ValueError, SyntaxError):
                        # If not a valid Python literal, try numeric conversion
                        if "." in result:
                            return float(result)
                        return int(result)
                except (ValueError, TypeError, SyntaxError):
                    return result
            except UndefinedError as e:
                error_msg = str(e)
                namespace = self._get_undefined_namespace(error_msg)
                available = self.get_available_variables()
                raise TemplateError(
                    f"Template error: Undefined variable in namespace '{namespace}'. "
                    f"Error: {error_msg}. Available variables in '{namespace}' namespace: {available[namespace]}"
                )
        elif isinstance(value, dict):
            return {
                k: self._process_value(v, template_context) for k, v in value.items()
            }
        elif isinstance(value, list):
            return [self._process_value(item, template_context) for item in value]
        return value

    def _get_undefined_namespace(self, error_msg: str) -> str:
        """
        Extract namespace from undefined variable error.

        Args:
            error_msg: Error message from UndefinedError

        Returns:
            str: Namespace name or 'root' if not found
        """
        # Check for direct variable access pattern (e.g., args.undefined)
        for namespace in ["args", "env", "steps"]:
            if f"{namespace}." in error_msg:
                return namespace

        # Check for dictionary access pattern (e.g., 'dict object' has no attribute 'undefined')
        # Extract the undefined attribute name from the error message
        match = re.search(r"no attribute '(\w+)'", error_msg)
        if match:
            undefined_attr = match.group(1)
            # Find which namespace was trying to access this attribute
            for namespace in ["args", "env", "steps"]:
                if namespace in self._context:
                    template_str = next(
                        (
                            v
                            for v in self.inputs.values()
                            if isinstance(v, str)
                            and f"{namespace}.{undefined_attr}" in v
                        ),
                        "",
                    )
                    if template_str:
                        return namespace

        return "root"


def register_task(name: str) -> Callable[[TaskHandler | ConfigTaskHandler], TaskHandler | ConfigTaskHandler]:
    """
    Decorator to register a task handler.

    Args:
        name: Name of the task type

    Returns:
        Callable: Decorator function that can handle both traditional and TaskConfig-based handlers
    """

    def decorator(func: TaskHandler | ConfigTaskHandler) -> TaskHandler | ConfigTaskHandler:
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
    1. Creates a TaskConfig instance for namespace support
    2. Processes inputs with template resolution
    3. Handles workspace paths if needed

    Args:
        func: The function to wrap as a task handler

    Returns:
        TaskHandler: Wrapped task handler
    """

    @wraps(func)
    def wrapper(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> R:
        config = TaskConfig(step, context, workspace)
        processed_inputs = config.process_inputs()
        return func(**processed_inputs)

    return cast(TaskHandler, wrapper)


# Import task modules
from . import basic_tasks, batch, file_tasks, python_tasks, shell_tasks, template_tasks

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

# Register batch task (using new implementation)
register_task("batch")(batch.batch_task)
