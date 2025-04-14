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

    Args:
        step: The step configuration containing the operation and inputs
        context: The execution context
        workspace: The workspace path

    Returns:
        Dict containing the result of the operation
    """
    try:
        logger = get_task_logger(workspace, step.get("name", "python"))
        workspace_path = Path(workspace) if isinstance(workspace, str) else workspace
        log_task_execution(logger, step, context, workspace_path)

        inputs = step.get("inputs", {})
        operation = inputs.get("operation")

        if not operation:
            raise ValueError("Operation must be specified for Python task")

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
            result: float = 1.0  # Explicitly declare as float
            for num in numbers:
                result *= float(num)
            result *= factor
            return {"result": result}

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
                result = dividend / divisor
                return {"result": result}
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
                    result = handler(inputs["item"], *args, **kwargs)
                else:
                    result = handler(*args, **kwargs)

                if isinstance(result, Exception):
                    raise result
                return {"result": result}
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
