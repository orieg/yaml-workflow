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
        TemplateError: If template resolution fails
    """
    try:
        template = Template(command, undefined=StrictUndefined)
        return template.render(**context)
    except UndefinedError as e:
        # Extract the undefined variable name from the error message
        var_name = str(e).split("'")[1] if "'" in str(e) else "unknown"

        # Get available variables by namespace
        available = {
            "args": list(context.get("args", {}).keys()),
            "env": list(context.get("env", {}).keys()),
            "steps": list(context.get("steps", {}).keys()),
            "batch": (
                list(context.get("batch", {}).keys()) if "batch" in context else []
            ),
        }

        # Build a helpful error message
        msg = f"Undefined variable '{var_name}' in shell command template. "
        msg += "Available variables by namespace:\n"
        for ns, vars in available.items():
            msg += f"  {ns}: {', '.join(vars) if vars else '(empty)'}\n"

        raise TemplateError(msg)
    except Exception as e:
        raise TemplateError(f"Failed to process shell command template: {str(e)}")


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
    task_name = str(config.name) if config.name is not None else "unnamed_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        # Process inputs with template support
        try:
            processed = config.process_inputs()
        except TemplateError as e:
            raise TaskExecutionError(
                f"Failed to resolve template in shell task inputs: {str(e)}",
                original_error=e,
            )

        # Get command (required)
        if "command" not in processed:
            missing_cmd_error = ValueError("command parameter is required")
            raise TaskExecutionError(
                "No command provided for shell task",
                original_error=missing_cmd_error,
            )
        command = processed["command"]

        # Handle working directory
        cwd = config.workspace
        if "working_dir" in processed:
            working_dir = processed["working_dir"]
            if not os.path.isabs(working_dir):
                cwd = config.workspace / working_dir
            else:
                cwd = Path(working_dir)

        # Get environment variables
        env = get_environment()
        if "env" in processed:
            env.update(processed["env"])

        # Get shell mode - default to True for better script compatibility
        shell = processed.get("shell", True)

        # Get timeout
        timeout = processed.get("timeout", None)

        # Process command template
        try:
            command = process_command(command, config._context)
        except TemplateError as e:
            raise TaskExecutionError(
                f"Failed to process shell command template: {str(e)}",
                original_error=e,
            )

        # Run command
        try:
            returncode, stdout, stderr = run_command(
                command, cwd=str(cwd), env=env, shell=shell, timeout=timeout
            )
        except subprocess.TimeoutExpired as e:
            raise TaskExecutionError(
                f"Command timed out after {timeout} seconds",
                original_error=e,
            )
        except subprocess.CalledProcessError as e:
            raise TaskExecutionError(
                f"Command failed with exit code {e.returncode}",
                original_error=e,
            )
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to execute command: {str(e)}",
                original_error=e,
            )

        # Check return code
        if returncode != 0:
            cmd_error = subprocess.CalledProcessError(
                returncode, command, stdout, stderr
            )
            raise TaskExecutionError(
                f"Command failed with exit code {returncode}",
                original_error=cmd_error,
            )

        # Log task completion
        log_task_result(
            logger,
            {
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
                "command": command,
            },
        )

        # Return results with both returncode and exit_code for backward compatibility
        return {
            "returncode": returncode,
            "exit_code": returncode,  # Alias for backward compatibility
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
        }

    except TaskExecutionError as e:
        log_task_error(logger, e)
        raise

    except Exception as e:
        log_task_error(logger, e)
        raise TaskExecutionError(
            f"Unexpected error in shell task: {str(e)}",
            original_error=e,
        )
