"""
Python task implementations for executing Python functions.
"""

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result

logger = logging.getLogger(__name__)


def execute_code(code: str, config: TaskConfig) -> Any:
    """Execute Python code with TaskConfig support.

    Args:
        code: Python code to execute
        config: TaskConfig object for variable access

    Returns:
        The value of the 'result' variable after code execution

    Raises:
        TemplateError: If code execution fails
    """
    # Create a new dictionary with a copy of the context to avoid modifying the original
    local_vars = {
        "context": config._context,
        "args": config._context.get("args", {}),
        "env": config._context.get("env", {}),
        "steps": config._context.get("steps", {}),
        "batch": config._context.get("batch", {}),
    }
    local_vars.update(config.process_inputs())

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


def execute_function(code: str, config: TaskConfig) -> Any:
    """Execute a Python function with TaskConfig support.

    Args:
        code: Python code containing function definition
        config: TaskConfig object for variable access

    Returns:
        Function result

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

        # Get processed inputs
        processed = config.process_inputs()
        args = processed.get("args", [])
        kwargs = processed.get("kwargs", {})

        # Convert string arguments to Python objects if needed
        processed_args = []
        for arg in args:
            if isinstance(arg, str):
                try:
                    import ast

                    processed_args.append(ast.literal_eval(arg))
                except (ValueError, SyntaxError):
                    processed_args.append(arg)
            else:
                processed_args.append(arg)

        # Call the function with processed arguments
        result = local_vars["process"](*processed_args, **kwargs)
        return result
    except Exception as e:
        if isinstance(e, TemplateError):
            raise
        raise TemplateError(f"Failed to execute function: {str(e)}")


def handle_multiply_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle multiply operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the multiplication result

    Raises:
        TemplateError: If operation fails
    """
    processed = config.process_inputs()

    # Get numbers from inputs or context
    numbers = processed.get("numbers", [])
    if isinstance(numbers, str):
        try:
            import ast

            numbers = ast.literal_eval(numbers)
        except (ValueError, SyntaxError) as e:
            raise TemplateError(f"Invalid numbers format: {str(e)}")

    if "item" in processed:
        item = processed["item"]
        if isinstance(item, (int, float)):
            numbers = [float(item)]
        elif isinstance(item, list):
            numbers = [float(x) for x in item]
        else:
            raise TemplateError(
                f"Item must be a number or list of numbers, got {type(item)}"
            )
    if not numbers:
        raise TemplateError("Numbers must be a non-empty list")

    # Get factor from inputs
    try:
        factor = float(processed.get("factor", 1))
    except (TypeError, ValueError) as e:
        raise TemplateError(f"Invalid factor: {str(e)}")

    try:
        # If we're processing a batch item, multiply it by the factor
        if "item" in processed:
            results = [num * factor for num in numbers]
            # Return single value if input was single value
            if isinstance(processed["item"], (int, float)):
                return {"result": float(results[0])}  # Ensure float type
            return {"result": [float(r) for r in results]}  # Ensure float type

        # Otherwise multiply all numbers together and then by the factor
        multiply_result: float = 1.0  # Explicitly declare as float
        for num in numbers:
            multiply_result *= float(num)
        multiply_result *= factor
        return {"result": multiply_result}
    except (TypeError, ValueError) as e:
        raise TemplateError(f"Failed to multiply numbers: {str(e)}")


def handle_divide_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle divide operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the division result

    Raises:
        TemplateError: If operation fails
    """
    processed = config.process_inputs()

    # Get dividend from inputs or context
    dividend = processed.get("dividend")
    if "item" in processed:
        dividend = processed["item"]
    if dividend is None:
        raise TemplateError("Dividend must be provided for divide operation")

    # Get divisor from inputs
    divisor = float(processed.get("divisor", 1))
    if divisor == 0:
        raise TemplateError("Division by zero")

    try:
        # Convert dividend to float and perform division
        dividend = float(dividend)
        if dividend == 0:
            raise TemplateError("Cannot divide zero by a number")
        division_result = dividend / divisor
        return {"result": division_result}
    except (TypeError, ValueError) as e:
        raise TemplateError(f"Invalid input for division: {str(e)}")


def handle_custom_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle custom operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the custom operation result

    Raises:
        TemplateError: If operation fails
    """
    processed = config.process_inputs()
    handler = processed.get("handler")

    if not handler or not callable(handler):
        raise TemplateError("Custom handler must be a callable")

    try:
        # Prepare arguments
        args = processed.get("args", [])
        kwargs = processed.get("kwargs", {})

        # Check if handler accepts item parameter
        sig = inspect.signature(handler)
        accepts_item = len(sig.parameters) > 0

        # Pass item as first argument only if handler accepts parameters
        if "item" in processed and accepts_item:
            custom_result = handler(processed["item"], *args, **kwargs)
        else:
            custom_result = handler(*args, **kwargs)

        if isinstance(custom_result, Exception):
            raise custom_result
        return {"result": custom_result}
    except Exception as e:
        if isinstance(e, TemplateError):
            raise
        raise TemplateError(f"Custom handler failed: {str(e)}")


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
def python_task(config: TaskConfig) -> Dict[str, Any]:
    """Execute a Python task with the given operation and inputs.

    The task supports two modes:
    1. Operation mode: Execute predefined operations (multiply, divide, custom)
    2. Code mode: Execute arbitrary Python code

    Args:
        config: TaskConfig object containing task configuration

    Returns:
        Dict containing the result of the operation/code and task metadata

    Raises:
        TemplateError: If task execution fails

    Example YAML usage:
        ```yaml
        steps:
          - name: multiply_numbers
            task: python
            inputs:
              operation: multiply
              numbers: [2, 3, 4]
              factor: 2

          - name: execute_code
            task: python
            inputs:
              code: |
                x = 10
                y = 20
                result = x + y

          - name: function_mode
            task: python
            inputs:
              operation: function
              code: |
                def process(x, y):
                    return x + y
              args: ["{{ args.x }}", "{{ args.y }}"]
        ```
    """
    try:
        logger = get_task_logger(config.workspace, config.name)
        log_task_execution(
            logger,
            {"name": config.name, "type": config.type},
            config._context,
            config.workspace,
        )

        # Process inputs first to handle any templates
        processed = config.process_inputs()

        # Initialize result
        result = None

        # Check for code execution mode
        if "code" in processed:
            if "operation" not in processed:
                result = execute_code(processed["code"], config)
            elif processed["operation"] == "function":
                result = execute_function(processed["code"], config)
        else:
            # Operation mode
            operation = processed.get("operation")
            if not operation:
                raise TemplateError(
                    "Either code or operation must be specified for Python task"
                )

            # Handle different operations
            if operation == "multiply":
                operation_result = handle_multiply_operation(config)
                result = operation_result["result"]
            elif operation == "divide":
                operation_result = handle_divide_operation(config)
                result = operation_result["result"]
            elif operation == "custom":
                operation_result = handle_custom_operation(config)
                result = operation_result["result"]
            else:
                raise TemplateError(f"Unknown operation: {operation}")

        # Return result with task metadata (following noop task pattern)
        return {
            "result": result,
            "task_name": config.name,
            "task_type": config.type,
            "processed_inputs": processed,
            "available_variables": config.get_available_variables(),
        }

    except Exception as e:
        log_task_error(logger, e)
        if isinstance(e, TemplateError):
            raise
        raise TemplateError(f"Python task failed: {str(e)}")
