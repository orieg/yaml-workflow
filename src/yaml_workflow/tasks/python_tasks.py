"""
Python task implementations for executing Python functions.
"""

import inspect
import logging
import pprint
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error

logger = logging.getLogger(__name__)


def execute_code(code: str, config: TaskConfig) -> Any:
    """Execute Python code with TaskConfig support.

    Args:
        code: Python code to execute
        config: TaskConfig object for variable access

    Returns:
        The value of the 'result' variable after code execution

    Raises:
        TaskExecutionError: If code execution fails
    """
    local_vars = {
        "context": config._context,
        "args": config._context.get("args", {}),
        "env": config._context.get("env", {}),
        "steps": config._context.get("steps", {}),
        "batch": config._context.get("batch", {}),
    }
    # Update with inputs processed within the caller (python_task)
    # Do NOT call config.process_inputs() here as it was done by the caller
    local_vars.update(config._processed_inputs)

    try:
        exec(code, {}, local_vars)
        return local_vars.get("result", None)
    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=str(config.name),
            task_type=str(config.type),
            error=e,
            task_config=config.step,
            template_context=config._context,  # or potentially just local_vars?
        )
        handle_task_error(context)
        return None  # Unreachable


def process_template_value(
    value: Any, context: Dict[str, Any], task_config: TaskConfig
) -> Any:
    """Process a template value using the given context.

    Args:
        value: The value to process (can be a string template or any other type)
        context: The context for template resolution
        task_config: The TaskConfig object for error context

    Returns:
        The processed value with preserved type

    Raises:
        TaskExecutionError: If template resolution fails or if a variable is undefined
    """
    if not isinstance(value, str):
        return value

    try:
        if "{{" in value and "}}" in value:
            template = Template(value, undefined=StrictUndefined)
            try:
                result = template.render(context)
            except UndefinedError as e:
                # Use new handler, pass task_config for context
                err_context = ErrorContext(
                    step_name=str(task_config.name),
                    task_type=str(task_config.type),
                    error=e,
                    task_config=task_config.step,
                    template_context=context,
                )
                handle_task_error(err_context)
                return None  # Unreachable

            try:
                import ast

                return ast.literal_eval(result)
            except (ValueError, SyntaxError):
                return result
        return value
    except Exception as e:
        # Use new handler, pass task_config for context
        err_context = ErrorContext(
            step_name=str(task_config.name),
            task_type=str(task_config.type),
            error=e,
            task_config=task_config.step,
            template_context=context,
        )
        handle_task_error(err_context)
        return None  # Unreachable


def execute_function(code: str, config: TaskConfig) -> Any:
    """Execute a Python function with TaskConfig support.

    Args:
        code: Python code containing function definition
        config: TaskConfig object for variable access

    Returns:
        Function result

    Raises:
        TaskExecutionError: If function execution fails
    """
    try:
        local_vars: Dict[str, Any] = {}
        exec(code, {}, local_vars)

        if "process" not in local_vars or not callable(local_vars["process"]):
            raise ValueError("Function mode requires a 'process' function")

        # Inputs already processed by caller (python_task)
        processed = config._processed_inputs
        args = processed.get("args", [])
        kwargs = processed.get("kwargs", {})

        processed_args = []
        for arg in args:
            if isinstance(arg, str):
                try:
                    import ast

                    processed_args.append(ast.literal_eval(arg))
                except (ValueError, SyntaxError):
                    # If eval fails, raise an error instead of silently using the string
                    raise ValueError(
                        f"Failed to evaluate argument string as literal: {arg!r}"
                    )
            else:
                processed_args.append(arg)

        result = local_vars["process"](*processed_args, **kwargs)
        return result
    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=str(config.name),
            task_type=str(config.type),
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None  # Unreachable


def handle_multiply_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle multiply operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the multiplication result

    Raises:
        TaskExecutionError: If operation fails
    """
    try:
        processed = config._processed_inputs  # Use already processed inputs

        numbers = processed.get("numbers", [])
        if isinstance(numbers, str):
            try:
                import ast

                numbers = ast.literal_eval(numbers)
            except (ValueError, SyntaxError) as e:
                raise ValueError(
                    f"Invalid numbers format: {str(e)}"
                )  # Raise specific config error

        if "item" in processed:
            item = processed["item"]
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

        try:
            factor = float(processed.get("factor", 1))
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid factor: {str(e)}")

        if "item" in processed:
            results = [num * factor for num in numbers]
            if isinstance(processed["item"], (int, float)):
                return {"result": float(results[0])}
            return {"result": [float(r) for r in results]}

        multiply_result: float = 1.0
        for num in numbers:
            multiply_result *= float(num)
        multiply_result *= factor
        return {"result": multiply_result}

    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=str(config.name),
            task_type=str(config.type),
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


def handle_divide_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle divide operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the division result

    Raises:
        TaskExecutionError: If operation fails
    """
    try:
        processed = config._processed_inputs  # Use already processed inputs

        dividend = processed.get("dividend")
        if "item" in processed:
            dividend = processed["item"]
        if dividend is None:
            raise ValueError("dividend parameter is required for divide operation")

        # Check for divisor *before* getting with default
        if "divisor" not in processed:
            raise ValueError("divisor parameter is required for divide operation")
        divisor_raw = processed.get("divisor")  # Now we know it exists
        assert divisor_raw is not None # Add assertion for type checker

        try:
            dividend = float(dividend)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid dividend: {str(e)}")

        try:
            divisor = float(divisor_raw)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid divisor: {str(e)}")

        if divisor == 0:
            raise ValueError("Division by zero")

        result = dividend / divisor
        return {"result": float(result)}

    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=str(config.name),
            task_type=str(config.type),
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


def handle_custom_operation(config: TaskConfig) -> Dict[str, Any]:
    """Handle custom operation with TaskConfig support.

    Args:
        config: TaskConfig object containing operation parameters

    Returns:
        Dict containing the custom operation result

    Raises:
        TaskExecutionError: If operation fails
    """
    try:
        processed = config._processed_inputs  # Use already processed inputs
        # Example: Add numbers
        if config.type == "add_numbers":  # Assuming type is passed or inferred
            num1 = float(processed.get("num1", 0))
            num2 = float(processed.get("num2", 0))
            return {"result": num1 + num2}
        else:
            raise NotImplementedError(
                f"Custom operation '{config.type}' not implemented"
            )

    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=str(config.name),
            task_type=str(config.type),
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


@register_task()
def print_vars_task(config: TaskConfig) -> dict:
    """Prints selected variables from the context for debugging."""
    inputs = config.process_inputs()
    context = config._context
    message = inputs.get("message", "Current Context Variables:")

    print(f"\n--- {message} ---")  # Prints directly to runner's stdout

    # Select variables to print (add more as needed)
    print("Workflow Variables:")
    print("==================")
    # Use direct context access via config.context
    print(f"args: {context.get('args')}")
    print(f"workflow_name: {context.get('workflow_name')}")
    print(f"workspace: {context.get('workspace')}")
    print(f"output: {context.get('output')}")
    print(f"run_number: {context.get('run_number')}")
    print(f"timestamp: {context.get('timestamp')}")

    # Safely access nested step results
    print("\nStep Results:")
    print("=============")
    steps_context = context.get("steps", {})
    if steps_context:
        # Use pprint for potentially large/nested step results
        pprint.pprint(steps_context, indent=2)
        # for name, step_info in steps_context.items():
        #     if step_info.get("skipped"):
        #         print(f"  - {name}: (skipped)")
        #     else:
        #         # Truncate long results for clarity
        #         result_repr = repr(step_info.get('result', 'N/A'))
        #         if len(result_repr) > 100:
        #             result_repr = result_repr[:100] + "..."
        #         print(f"  - {name}: {result_repr}")
    else:
        print("  (No step results yet)")

    print("--------------------\n")
    sys.stdout.flush()  # Flush after printing
    return {"success": True}  # Indicate task success


@register_task(name="print_message")  # Explicitly register with desired name
def print_message_task(config: TaskConfig) -> dict:
    """Prints a templated message to the console."""
    inputs = config.process_inputs()  # Render inputs using context
    context = config._context
    message = inputs.get("message", "")

    if not message:
        logger.warning("print_message task called with no message.")
        # Even if empty, consider it success, just print nothing
        # return {"success": False, "error": "No message provided"}

    # The message is already rendered by process_inputs, just print it
    print(message)  # Prints directly to runner's stdout
    sys.stdout.flush()  # Flush after printing
    return {"success": True, "printed_length": len(message)}


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
        TaskExecutionError: If the task fails for any reason.

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
    task_name = str(config.name or "python_task")
    task_type = str(config.type or "python")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)

        # Process inputs first to handle any templates
        processed = config.process_inputs()
        config._processed_inputs = processed  # Store for use in helpers

        # --- Input Validation ---
        has_code = "code" in processed
        has_operation = "operation" in processed

        # Allow code and operation ONLY if operation is 'function'
        if has_code and has_operation and processed.get("operation") != "function":
            raise ValueError(
                "Cannot specify both 'code' and 'operation' unless operation is 'function'"
            )
        # Still require at least one
        if not has_code and not has_operation:
            raise ValueError(
                "Either 'code' or 'operation' must be specified for Python task"
            )

        operation = processed.get("operation")

        result = None
        operation_result = None  # Initialize operation_result

        if "code" in processed:
            if "operation" not in processed:
                code_result = execute_code(processed["code"], config)
                # Create the result dict for code-only execution
                operation_result = {"result": code_result}
            elif processed["operation"] == "function":
                if not has_code:
                    raise ValueError(
                        "'code' parameter is required for function operation"
                    )
                # Capture the result from execute_function
                func_result = execute_function(processed["code"], config)
                operation_result = {"result": func_result}
            elif operation == "multiply":
                operation_result = handle_multiply_operation(config)
            elif operation == "divide":
                operation_result = handle_divide_operation(config)
            elif operation == "custom":
                operation_result = handle_custom_operation(config)
            else:
                # This path should technically be unreachable due to earlier checks
                # but raising here for safety.
                raise ValueError(f"Unknown or unhandled operation: {operation}")
        else:
            if operation == "multiply":
                operation_result = handle_multiply_operation(config)
            elif operation == "divide":
                operation_result = handle_divide_operation(config)
            elif operation == "custom":
                operation_result = handle_custom_operation(config)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        # Return the dictionary produced by the operation handlers or code execution
        if operation_result is None:
            # This case should ideally not be hit if validation is correct,
            # but provide a default empty dict for safety.
            logger.warning(
                "Operation result was unexpectedly None for step %s", task_name
            )
            operation_result = {}

        log_task_result(logger, operation_result)
        return operation_result

    except Exception as e:
        # Centralized error handling for python_task specific errors (e.g., config validation)
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable
