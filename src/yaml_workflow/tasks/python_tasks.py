"""
Python task implementations for executing Python functions.
"""

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from jinja2 import Template, StrictUndefined, UndefinedError

from ..exceptions import TemplateError
from . import register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result

logger = logging.getLogger(__name__)


def execute_code(code: str, inputs: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Execute Python code with given inputs and context.

    Args:
        code: Python code to execute
        inputs: Input variables for the code
        context: Context variables for the code

    Returns:
        The value of the 'result' variable after code execution, or None if not set

    Raises:
        TemplateError: If template resolution or code execution fails
    """
    # Create a new dictionary with a copy of the context to avoid modifying the original
    local_vars = {"context": context}
    local_vars.update(inputs)

    try:
        # Execute the code
        exec(code, {}, local_vars)
        # Only return the result if it was explicitly set in the code
        return local_vars.get("result", None)
    except Exception as e:
        raise TemplateError(f"Failed to execute Python code: {str(e)}")


def process_template_value(value: Any, context: Dict[str, Any]) -> Any:
    """Process a template value using the given context.

    Args:
        value: The value to process (can be a string template or any other type)
        context: The context for template resolution

    Returns:
        The processed value with preserved type

    Raises:
        TemplateError: If template resolution fails or if a variable is undefined
    """
    if not isinstance(value, str):
        return value

    try:
        # Check if the value is a template
        if "{{" in value and "}}" in value:
            # Process the template with StrictUndefined to catch undefined variables
            template = Template(value, undefined=StrictUndefined)
            try:
                result = template.render(context)
            except UndefinedError as e:
                raise TemplateError(f"Undefined variable in template: {str(e)}")
            
            # Try to evaluate the result as a Python literal
            try:
                import ast
                return ast.literal_eval(result)
            except (ValueError, SyntaxError):
                return result
        return value
    except Exception as e:
        if isinstance(e, TemplateError):
            raise
        raise TemplateError(f"Failed to process template: {str(e)}")


def execute_function(code: str, args: List[Any], kwargs: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Execute a Python function with given arguments.

    Args:
        code: Python code containing the function definition
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        context: The context for template resolution

    Returns:
        The result of the function call

    Raises:
        TemplateError: If function execution fails
    """
    try:
        # Create a new dictionary for local variables
        local_vars = {}
        
        # Execute the code to define the function
        exec(code, {}, local_vars)
        
        # Check if the process function exists
        if "process" not in local_vars or not callable(local_vars["process"]):
            raise ValueError("Function mode requires a 'process' function")
        
        # Process template variables in arguments
        processed_args = [process_template_value(arg, context) for arg in args]
        processed_kwargs = {
            k: process_template_value(v, context)
            for k, v in kwargs.items()
        }
        
        # Call the function with processed arguments
        result = local_vars["process"](*processed_args, **processed_kwargs)
        return result
    except Exception as e:
        if isinstance(e, TemplateError):
            raise
        raise TemplateError(f"Failed to execute function: {str(e)}")


@register_task("print_vars")
def print_vars_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Union[str, Path]
) -> Dict[str, Any]:
    """Print all available variables in the context.

    Args:
        step: The step configuration
        context: The execution context
        workspace: The workspace path

    Returns:
        Dict containing success status

    Raises:
        TemplateError: If task execution fails
    """
    try:
        logger = get_task_logger(workspace, step.get("name", "print_vars"))
        workspace_path = Path(workspace) if isinstance(workspace, str) else workspace
        log_task_execution(logger, step, context, workspace_path)

        print("\n=== Available Variables ===")
        print("\nContext:")
        for key, value in context.items():
            print(f"{key}: {type(value)} = {value}")

        print("\nStep:")
        for key, value in step.items():
            print(f"{key}: {type(value)} = {value}")

        print("\nWorkspace:", workspace)
        print("=== End Variables ===\n")

        return {"success": True}

    except Exception as e:
        log_task_error(logger, e)
        raise TemplateError(f"Failed to print variables: {str(e)}")


@register_task("python")
def python_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Union[str, Path]
) -> Dict[str, Any]:
    """Execute a Python task with the given operation and inputs.

    The task supports two modes:
    1. Operation mode: Execute predefined operations (multiply, divide, custom)
    2. Code mode: Execute arbitrary Python code

    Args:
        step: The step configuration containing the operation/code and inputs
        context: The execution context
        workspace: The workspace path

    Returns:
        Dict containing the result of the operation/code

    Raises:
        TemplateError: If task execution fails
    """
    try:
        logger = get_task_logger(workspace, step.get("name", "python"))
        workspace_path = Path(workspace) if isinstance(workspace, str) else workspace
        log_task_execution(logger, step, context, workspace_path)

        # Check for code execution mode
        if "code" in step:
            code = step["code"]
            inputs = step.get("inputs", {})
            result = execute_code(code, inputs, context)
            return {"result": result}

        # Operation mode
        inputs = step.get("inputs", {})
        operation = inputs.get("operation")

        if not operation:
            raise ValueError("Either code or operation must be specified for Python task")

        if operation == "multiply":
            # Get numbers from inputs or context
            numbers = inputs.get("numbers", [])
            if "item" in inputs:
                item = inputs["item"]
                if isinstance(item, (int, float)):
                    numbers = [float(item)]
                elif isinstance(item, list):
                    numbers = [float(x) for x in item]
                else:
                    raise ValueError(
                        f"Item must be a number or list of numbers, got {type(item)}"
                    )
            if not numbers:
                raise ValueError("Numbers must be a non-empty list")

            # Get factor from inputs
            factor = float(inputs.get("factor", 1))

            # If we're processing a batch item, multiply it by the factor
            if "item" in inputs:
                results = [num * factor for num in numbers]
                # Return single value if input was single value
                if isinstance(inputs["item"], (int, float)):
                    return {"result": float(results[0])}  # Ensure float type
                return {"result": [float(r) for r in results]}  # Ensure float type

            # Otherwise multiply all numbers together and then by the factor
            multiply_result: float = 1.0  # Explicitly declare as float
            for num in numbers:
                multiply_result *= float(num)
            multiply_result *= factor
            return {"result": multiply_result}

        elif operation == "divide":
            # Get dividend from inputs or context
            dividend = inputs.get("dividend")
            if "item" in inputs:
                dividend = inputs["item"]
            if dividend is None:
                raise ValueError("Dividend must be provided for divide operation")

            # Get divisor from inputs
            divisor = float(inputs.get("divisor", 1))
            if divisor == 0:
                raise ValueError("Division by zero")

            # Convert dividend to float and perform division
            try:
                dividend = float(dividend)
                if dividend == 0:
                    raise ValueError("Cannot divide zero by a number")
                division_result = dividend / divisor
                return {"result": division_result}
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid input for division: {e}")

        elif operation == "custom":
            handler = inputs.get("handler")
            if not handler or not callable(handler):
                raise ValueError("Custom handler must be a callable")

            # Prepare arguments
            args = inputs.get("args", [])
            kwargs = inputs.get("kwargs", {})

            # Check if handler accepts item parameter
            sig = inspect.signature(handler)
            accepts_item = len(sig.parameters) > 0

            # Pass item as first argument only if handler accepts parameters
            try:
                if "item" in inputs and accepts_item:
                    custom_result = handler(inputs["item"], *args, **kwargs)
                else:
                    custom_result = handler(*args, **kwargs)

                if isinstance(custom_result, Exception):
                    raise custom_result
                return {"result": custom_result}
            except Exception as e:
                log_task_error(logger, e)  # Pass the actual exception
                raise TemplateError(f"Custom handler failed: {str(e)}")

        elif operation == "function":
            # Get function code and arguments
            if "code" not in inputs:
                raise ValueError("Function mode requires 'code' parameter")
            
            code = inputs["code"]
            args = inputs.get("args", [])
            kwargs = inputs.get("kwargs", {})
            
            # Execute the function with context for template resolution
            result = execute_function(code, args, kwargs, context)
            return {"result": result}

        else:
            raise ValueError(f"Unknown operation: {operation}")

    except ValueError as e:
        raise TemplateError(str(e))
    except Exception as e:
        if not isinstance(e, TemplateError):
            raise TemplateError(f"Python task failed: {str(e)}")
        raise
