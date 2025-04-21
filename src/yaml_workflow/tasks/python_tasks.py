"""
Python task implementations for executing Python functions.
"""

import asyncio
import importlib
import inspect
import io
import logging
import os
import pprint
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

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
        assert divisor_raw is not None  # Add assertion for type checker

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


def _load_function(module_name: str, function_name: str) -> Callable:
    """Load a function from a module."""
    try:
        module = importlib.import_module(module_name)
        if not hasattr(module, function_name):
            raise AttributeError(
                f"Function '{function_name}' not found in module '{module_name}'"
            )
        function = getattr(module, function_name)
        if not callable(function):
            raise TypeError(
                f"'{function_name}' in module '{module_name}' is not callable"
            )
        return function  # type: ignore
    except ImportError:
        raise ModuleNotFoundError(f"Module '{module_name}' not found")
    # AttributeError is caught and re-raised with more context
    # Other exceptions like TypeError are caught by the main handler


def _execute_python_function(func: Callable, config: TaskConfig) -> Any:
    """Execute the loaded Python function with processed inputs."""
    processed = config._processed_inputs
    sig = inspect.signature(func)
    params = sig.parameters

    # Prepare arguments from processed inputs
    input_args = processed.get("args", [])
    input_kwargs = processed.get("kwargs", {})

    # Validate input types
    if not isinstance(input_args, list):
        raise TypeError("Input 'args' must be a list.")
    if not isinstance(input_kwargs, dict):
        raise TypeError("Input 'kwargs' must be a dictionary.")

    # Attempt to bind arguments using inspect.bind
    # This handles positional, keyword, defaults, *args, **kwargs, etc.
    try:
        bound_args = sig.bind(*input_args, **input_kwargs)
        bound_args.apply_defaults()  # Apply defaults for unbound optional parameters

        # Now call the function with the bound arguments
        logger.debug(f"Calling {func.__name__} with bound args: {bound_args.arguments}")
        if inspect.iscoroutinefunction(func):
            # Execute async function
            logger.debug(f"Executing async function {func.__name__}")
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                func(*bound_args.args, **bound_args.kwargs)
            )
            if not asyncio.get_event_loop().is_running():
                loop.close()
        else:
            # Execute sync function
            logger.debug(f"Executing sync function {func.__name__}")
            result = func(*bound_args.args, **bound_args.kwargs)

        logger.debug(f"Function returned: {result}")
        return result

    except TypeError as e:
        # Let TypeError from binding propagate up
        # Include function name in the error for clarity
        raise TypeError(f"Error binding arguments for {func.__name__}: {e}") from e
    except Exception as e:
        # Catch other errors during function execution
        logger.error(f"Error executing function {func.__name__}: {e}", exc_info=True)
        # Wrap in a generic exception or re-raise depending on desired handling
        raise Exception(f"Error during execution of {func.__name__}: {e}") from e


def _find_script(script_path: str, workspace: Path) -> Path:
    """Find a script path, checking workspace and PATH."""
    path = Path(script_path)
    if path.is_absolute():
        if not path.exists():
            raise FileNotFoundError(f"Absolute script path not found: {path}")
        return path

    # Check relative to workspace
    workspace_path = workspace / path
    if workspace_path.exists():
        return workspace_path

    # Check in system PATH
    script_name = path.name
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for path_dir in path_dirs:
        full_path = Path(path_dir) / script_name
        if full_path.exists() and os.access(full_path, os.X_OK):
            return full_path

    raise FileNotFoundError(f"Script '{script_path}' not found in workspace or PATH")


def _execute_script(
    script_path: Path,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Tuple[int, str, str]:
    """Execute a script using subprocess."""
    command: List[str] = [sys.executable, str(script_path)]
    if args:
        command.extend(args)

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise CalledProcessError automatically
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        # Should be caught by _find_script, but handle defensively
        raise FileNotFoundError(
            f"Python executable or script not found: {command[0]} / {script_path}"
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Script execution timed out after {timeout} seconds")


def _execute_module(
    module_name: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout: Optional[float] = None,
    workspace: Optional[Path] = None,  # Add workspace path
) -> Tuple[int, str, str]:
    """Execute a module using python -m."""
    command: List[str] = [sys.executable, "-m", module_name]
    if args:
        command.extend(args)

    # Prepare environment to include workspace in PYTHONPATH
    env = os.environ.copy()
    python_path = env.get("PYTHONPATH", "")
    if workspace:
        # Prepend workspace to PYTHONPATH
        workspace_str = str(workspace.resolve())
        if python_path:
            env["PYTHONPATH"] = f"{workspace_str}{os.pathsep}{python_path}"
        else:
            env["PYTHONPATH"] = workspace_str

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=env,  # Pass modified environment
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Module execution timed out after {timeout} seconds")


def _execute_code(
    code: str, config: TaskConfig, result_variable: Optional[str] = None
) -> Any:
    """Execute arbitrary Python code string."""
    # Prepare execution context, including processed inputs
    exec_context = {
        "config": config,
        "context": config._context,
        "args": config._context.get("args", {}),
        "env": config._context.get("env", {}),
        "steps": config._context.get("steps", {}),
        "batch": config._context.get("batch", {}),
    }
    # Add processed inputs directly to the execution context
    exec_context.update(config._processed_inputs)

    # Redirect stdout/stderr to capture prints within the code
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, {}, exec_context)

        # Log captured output
        captured_stdout = stdout_capture.getvalue()
        captured_stderr = stderr_capture.getvalue()
        if captured_stdout:
            logger.info(f"Captured stdout from python_code:\n{captured_stdout}")
        if captured_stderr:
            logger.warning(f"Captured stderr from python_code:\n{captured_stderr}")

        # Extract result if specified
        if result_variable:
            if result_variable not in exec_context:
                raise NameError(
                    f"Result variable '{result_variable}' not found after code execution."
                )
            return exec_context[result_variable]
        else:
            # Default: return None if no result_variable specified
            return None

    except Exception as e:
        # Include captured stderr in the exception if available
        captured_stderr = stderr_capture.getvalue()
        if captured_stderr:
            # Fix: Correctly use the enhanced_error object
            enhanced_error = type(e)(f"{e}\nCaptured stderr:\n{captured_stderr}")
            raise TaskExecutionError(
                step_name=str(config.name),
                original_error=enhanced_error,  # Pass the enhanced error
            ) from e
        else:
            raise  # Re-raise original exception if no stderr


@register_task()
def python_function(config: TaskConfig) -> Dict[str, Any]:
    """Execute a Python function from a specified module."""
    task_name = str(config.name or "python_function_task")
    task_type = str(config.type or "python_function")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)
        processed = config.process_inputs()
        config._processed_inputs = processed  # Store for helpers

        # Get module/function from processed inputs
        module_name = processed.get("module")
        function_name = processed.get("function")

        if not module_name or not isinstance(module_name, str):
            raise ValueError("Input 'module' (string) is required.")
        if not function_name or not isinstance(function_name, str):
            raise ValueError("Input 'function' (string) is required.")

        # Load and execute
        func = _load_function(module_name, function_name)
        result_value = _execute_python_function(func, config)

        # Log the result (as a dict for consistency in logs)
        log_task_result(logger, result={"result": result_value})
        # Return the raw result_value, engine will wrap it
        return result_value

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


@register_task()
def python_script(config: TaskConfig) -> Dict[str, Any]:
    """Execute an external Python script."""
    task_name = str(config.name or "python_script_task")
    task_type = str(config.type or "python_script")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)
        processed = config.process_inputs()
        config._processed_inputs = processed

        script_path_in = processed.get("script_path")
        args = processed.get("args")  # Should be list or None
        cwd = processed.get("cwd")
        timeout = processed.get("timeout")

        if not script_path_in or not isinstance(script_path_in, str):
            raise ValueError("Input 'script_path' (string) is required.")
        if args is not None and not isinstance(args, list):
            raise ValueError("Input 'args' must be a list of strings.")
        if cwd is not None and not isinstance(cwd, str):
            raise ValueError("Input 'cwd' must be a string.")
        if timeout is not None:
            try:
                timeout = float(timeout)
            except ValueError:
                raise ValueError("Input 'timeout' must be a number.")

        script_path = _find_script(script_path_in, config.workspace)
        returncode, stdout, stderr = _execute_script(
            script_path=script_path, args=args, cwd=cwd, timeout=timeout
        )

        result = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

        # Optionally raise error on non-zero exit code
        check = processed.get("check", True)  # Default to True
        if check and returncode != 0:
            error_message = f"Script '{script_path}' failed with exit code {returncode}.\nStderr:\n{stderr}"
            # Fix: Wrap the failure reason in a standard error type
            raise TaskExecutionError(
                step_name=task_name, original_error=RuntimeError(error_message)
            )

        log_task_result(logger, result)
        return result

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


@register_task()
def python_module(config: TaskConfig) -> Dict[str, Any]:
    """Execute a Python module as a script."""
    task_name = str(config.name or "python_module_task")
    task_type = str(config.type or "python_module")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)
        processed = config.process_inputs()
        config._processed_inputs = processed

        module_name = processed.get("module")
        args = processed.get("args")
        cwd = processed.get("cwd")
        timeout = processed.get("timeout")

        if not module_name or not isinstance(module_name, str):
            raise ValueError("Input 'module' (string) is required.")
        if args is not None and not isinstance(args, list):
            raise ValueError("Input 'args' must be a list of strings.")
        if cwd is not None and not isinstance(cwd, str):
            raise ValueError("Input 'cwd' must be a string.")
        if timeout is not None:
            try:
                timeout = float(timeout)
            except ValueError:
                raise ValueError("Input 'timeout' must be a number.")

        returncode, stdout, stderr = _execute_module(
            module_name=module_name,
            args=args,
            cwd=cwd,
            timeout=timeout,
            workspace=config.workspace,  # Pass workspace path
        )

        result = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

        # Optionally raise error on non-zero exit code
        check = processed.get("check", True)
        if check and returncode != 0:
            error_message = f"Module '{module_name}' failed with exit code {returncode}.\nStderr:\n{stderr}"
            # Fix: Wrap the failure reason in a standard error type
            raise TaskExecutionError(
                step_name=task_name, original_error=RuntimeError(error_message)
            )

        log_task_result(logger, result)
        return result

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable


@register_task()
def python_code(config: TaskConfig) -> Dict[str, Any]:
    """Execute a snippet of Python code."""
    task_name = str(config.name or "python_code_task")
    task_type = str(config.type or "python_code")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)
        processed = config.process_inputs()
        config._processed_inputs = processed

        code = processed.get("code")
        result_variable = processed.get("result_variable")

        if not code or not isinstance(code, str):
            raise ValueError("Input 'code' (string) is required.")
        if result_variable is not None and not isinstance(result_variable, str):
            raise ValueError("Input 'result_variable' must be a string.")

        result_value = _execute_code(code, config, result_variable)

        result = {"result": result_value}
        log_task_result(logger, result)
        return result

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable
