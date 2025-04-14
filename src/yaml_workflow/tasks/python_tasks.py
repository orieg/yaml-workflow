"""
Python task implementations for executing Python functions.
"""

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from . import register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result

logger = logging.getLogger(__name__)


def execute_code(code: str, inputs: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """
    Execute Python code string with given inputs and context.

    Args:
        code: Python code to execute
        inputs: Input variables for the code
        context: Workflow context

    Returns:
        Any: Result of code execution

    Raises:
        Exception: If code execution fails
    """
    # Create a clean namespace for code execution
    namespace = {
        # Add builtins that are safe to use
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "round": round,
        # Add standard library modules that are safe to use
        "json": __import__("json"),
        "datetime": __import__("datetime"),
        "math": __import__("math"),
        "random": __import__("random"),
        "uuid": __import__("uuid"),
        "base64": __import__("base64"),
        "hashlib": __import__("hashlib"),
        "re": __import__("re"),
        "csv": __import__("csv"),
        "io": __import__("io"),
        "pathlib": __import__("pathlib"),
        # Add inputs and context
        **inputs,
        "context": context,
    }

    # Execute the code
    exec(code + "\nresult = None", namespace)

    # Get the result
    result = namespace.get("result")
    if result is None:
        # If no result was set, try to get the last expression's value
        lines = code.strip().split("\n")
        if lines:
            last_line = lines[-1].strip()
            if last_line and not last_line.startswith(("#", '"', "'")):
                # Re-execute with just the last line assigned to result
                exec(code + f"\nresult = {last_line}", namespace)
                result = namespace.get("result")

    return result


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
        raise


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
    """
    try:
        logger = get_task_logger(workspace, step.get("name", "python"))
        workspace_path = Path(workspace) if isinstance(workspace, str) else workspace
        log_task_execution(logger, step, context, workspace_path)

        # Check for code execution mode
        if "code" in step:
            code = step["code"]
            inputs = step.get("inputs", {})
            try:
                result = execute_code(code, inputs, context)
                return {"result": result}
            except Exception as e:
                log_task_error(logger, e)
                raise ValueError(f"Code execution failed: {str(e)}")

        # Operation mode
        inputs = step.get("inputs", {})
        operation = inputs.get("operation")

        if not operation:
            raise ValueError(
                "Either code or operation must be specified for Python task"
            )

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
                raise

        else:
            msg = f"Unknown operation: {operation}"
            log_task_error(logger, ValueError(msg))  # Pass an actual exception
            raise ValueError(msg)

    except Exception as e:
        log_task_error(logger, e)  # Pass the actual exception
        raise
