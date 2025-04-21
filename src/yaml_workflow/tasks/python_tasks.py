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

        # Extract result
        if result_variable:
            if result_variable not in exec_context:
                raise NameError(
                    f"Result variable '{result_variable}' not found after code execution."
                )
            return exec_context[result_variable]
        elif "result" in exec_context:
            # Default: return 'result' variable if it exists
            return exec_context["result"]
        else:
            # Default: return None if no result_variable specified and no 'result' variable exists
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

        # Log the raw result value before returning
        log_task_result(logger, {"result_value_from_code": result_value})
        return result_value  # Return the raw value, engine will wrap it

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
