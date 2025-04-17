"""
Shell operation tasks for executing commands and managing processes.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from jinja2 import Template, StrictUndefined, UndefinedError

from ..exceptions import TemplateError, TaskExecutionError
from . import register_task, TaskConfig
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
            "batch": list(context.get("batch", {}).keys()) if "batch" in context else []
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
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        # Process inputs with template support
        try:
            processed = config.process_inputs()
        except TemplateError as e:
            raise TaskExecutionError(
                f"Failed to resolve template in shell task inputs: {str(e)}",
                original_error=e
            )
        
        # Get command (required)
        if "command" not in processed:
            raise TaskExecutionError(
                "No command provided for shell task",
                original_error=ValueError("command parameter is required")
            )
        command = processed["command"]
        
        # Handle working directory
        cwd = config.workspace
        if "working_dir" in processed:
            try:
                cwd = config.workspace / processed["working_dir"]
                if not cwd.exists():
                    cwd.mkdir(parents=True)
            except Exception as e:
                raise TaskExecutionError(
                    f"Failed to create working directory '{processed['working_dir']}': {str(e)}",
                    original_error=e
                )
        
        # Handle environment variables
        env = os.environ.copy()
        if "env" in processed:
            try:
                env.update(processed["env"])
            except Exception as e:
                raise TaskExecutionError(
                    f"Failed to set environment variables: {str(e)}",
                    original_error=e
                )
        
        # Get timeout if specified
        timeout = processed.get("timeout")
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            # Prepare result dictionary
            task_result = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
                "working_dir": str(cwd),
            }
            
            # Check for command failure
            if result.returncode != 0:
                error_msg = f"Command failed with exit code {result.returncode}: {command}\n"
                if result.stdout:
                    error_msg += f"stdout:\n{result.stdout}\n"
                if result.stderr:
                    error_msg += f"stderr:\n{result.stderr}"
                
                log_task_error(logger, error_msg)
                raise TaskExecutionError(
                    error_msg,
                    original_error=subprocess.CalledProcessError(
                        result.returncode,
                        command,
                        output=result.stdout,
                        stderr=result.stderr
                    )
                )
            
            log_task_result(logger, task_result)
            return task_result
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Command timed out after {timeout} seconds: {command}"
            log_task_error(logger, error_msg)
            raise TaskExecutionError(error_msg, original_error=e)
        except Exception as e:
            error_msg = f"Failed to execute shell command: {str(e)}"
            log_task_error(logger, error_msg)
            raise TaskExecutionError(error_msg, original_error=e)
            
    except Exception as e:
        if not isinstance(e, TaskExecutionError):
            error_msg = f"Shell task failed: {str(e)}"
            log_task_error(logger, error_msg)
            raise TaskExecutionError(error_msg, original_error=e)
        raise
