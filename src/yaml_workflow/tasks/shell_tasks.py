"""
Shell operation tasks for executing commands and managing processes.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    timeout: Optional[float] = None,
) -> Tuple[int, str, str]:
    """
    Run a shell command and return its output.

    Args:
        command: Command to run (string or list of arguments)
        cwd: Working directory for the command
        env: Environment variables to set
        shell: Whether to run command through shell
        timeout: Timeout in seconds

    Returns:
        Tuple[int, str, str]: Return code, stdout, and stderr
    """
    if isinstance(command, str) and not shell:
        command = command.split()

    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        shell=shell,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return result.returncode, result.stdout, result.stderr


def check_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    timeout: Optional[float] = None,
) -> str:
    """
    Run a command and raise an error if it fails.

    Args:
        command: Command to run (string or list of arguments)
        cwd: Working directory for the command
        env: Environment variables to set
        shell: Whether to run command through shell
        timeout: Timeout in seconds

    Returns:
        str: Command output (stdout)

    Raises:
        subprocess.CalledProcessError: If command returns non-zero exit code
    """
    if isinstance(command, str) and not shell:
        command = command.split()

    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        shell=shell,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )

    return result.stdout


def get_environment() -> Dict[str, str]:
    """
    Get current environment variables.

    Returns:
        Dict[str, str]: Dictionary of environment variables
    """
    return dict(os.environ)


def set_environment(env_vars: Dict[str, str]) -> Dict[str, str]:
    """
    Set environment variables.

    Args:
        env_vars: Dictionary of environment variables to set

    Returns:
        Dict[str, str]: Updated environment variables
    """
    os.environ.update(env_vars)
    return dict(os.environ)


def process_command(command: str, context: Dict[str, Any]) -> str:
    """
    Process a shell command template with the given context.

    Args:
        command: Shell command template
        context: Template context

    Returns:
        str: Processed shell command

    Raises:
        TaskExecutionError: If template resolution fails (via handle_task_error)
    """
    try:
        template = Template(command, undefined=StrictUndefined)
        return template.render(**context)
    except UndefinedError as e:
        task_name = context.get("step_name", "shell_template")
        task_type = context.get("task_type", "shell")
        var_name = str(e).split("'")[1] if "'" in str(e) else "unknown"

        available = {
            "args": list(context.get("args", {}).keys()),
            "env": list(context.get("env", {}).keys()),
            "steps": list(context.get("steps", {}).keys()),
            "batch": (
                list(context.get("batch", {}).keys()) if "batch" in context else []
            ),
        }

        msg = f"Undefined variable '{var_name}' in shell command template. "
        msg += "Available variables by namespace:\n"
        for ns, vars in available.items():
            msg += f"  {ns}: {', '.join(vars) if vars else '(empty)'}\n"

        template_error = TemplateError(msg)
        err_context = ErrorContext(
            step_name=str(task_name),
            task_type=str(task_type),
            error=template_error,
            task_config=context.get("task_config"),
            template_context=context,
        )
        handle_task_error(err_context)
        return ""  # Unreachable
    except Exception as e:  # Catch other template processing errors
        task_name = context.get("step_name", "shell_template")
        task_type = context.get("task_type", "shell")
        handle_task_error(
            ErrorContext(
                step_name=str(task_name),
                task_type=str(task_type),
                error=e,
                task_config=context.get("task_config"),
                template_context=context,
            )
        )
        return ""  # Unreachable


@register_task("shell")
def shell_task(config: TaskConfig) -> Dict[str, Any]:
    """
    Run a shell command with namespace support.

    Args:
        config: Task configuration with namespace support

    Returns:
        Dict[str, Any]: Command execution results

    Raises:
        TaskExecutionError: If command execution fails or template resolution fails
    """
    task_name = str(config.name or "shell_task")
    task_type = str(config.type or "shell")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)

        processed = config.process_inputs()
        config._processed_inputs = processed

        if "command" not in processed:
            missing_cmd_error = ValueError("command parameter is required")
            raise missing_cmd_error
        command = processed["command"]

        cwd = config.workspace
        if "working_dir" in processed:
            working_dir = processed["working_dir"]
            if not os.path.isabs(working_dir):
                cwd = config.workspace / working_dir
            else:
                cwd = Path(working_dir)

        env = get_environment()
        if "env" in processed:
            env.update(processed["env"])

        shell = processed.get("shell", True)

        # Get timeout
        timeout = processed.get("timeout", None)

        # Process command template ONLY if it's a string
        if isinstance(command, str):
            # Pass necessary context for error reporting within process_command
            command_context = {
                **config._context,
                "step_name": task_name,
                "task_type": task_type,
                "task_config": config.step,
            }
            command = process_command(command, command_context)
        elif not isinstance(command, list):
            # Raise error if command is neither string nor list
            invalid_type_error = TypeError(
                f"Invalid command type: {type(command).__name__}. Expected string or list."
            )
            raise TaskExecutionError(
                step_name=task_name, original_error=invalid_type_error
            )

        # Run command
        returncode, stdout, stderr = run_command(
            command, cwd=str(cwd), env=env, shell=shell, timeout=timeout
        )

        if returncode != 0:
            error_message = f"Command failed with exit code {returncode}"
            if stderr:
                error_message += f"\nStderr:\n{stderr}"
            cmd_error = subprocess.CalledProcessError(
                returncode, cmd=command, output=stdout, stderr=stderr
            )
            raise cmd_error

        result = {"return_code": returncode, "stdout": stdout, "stderr": stderr}
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
