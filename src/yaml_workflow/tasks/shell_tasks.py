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
        available = {
            "args": list(context["args"].keys()) if "args" in context else [],
            "env": list(context["env"].keys()) if "env" in context else [],
            "steps": list(context["steps"].keys()) if "steps" in context else []
        }
        raise TemplateError(f"{str(e)}. Available variables: {available}")
    except Exception as e:
        raise TemplateError(f"Failed to process shell command: {str(e)}")


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
    try:
        # Process inputs with template support
        try:
            processed = config.process_inputs()
        except TemplateError as e:
            raise TaskExecutionError(
                f"Template error in shell task: {str(e)}",
                original_error=e
            )
        
        # Get command (required)
        if "command" not in processed:
            raise TaskExecutionError(
                "No command provided",
                original_error=ValueError("No command provided")
            )
        command = processed["command"]
        
        # Handle working directory
        cwd = config.workspace
        if "working_dir" in processed:
            cwd = config.workspace / processed["working_dir"]
            if not cwd.exists():
                cwd.mkdir(parents=True)
        
        # Handle environment variables
        env = os.environ.copy()
        if "env" in processed:
            env.update(processed["env"])
        
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
                check=True  # This will raise CalledProcessError on non-zero exit
            )
            
            # Return structured result
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
                "working_dir": str(cwd)
            }
            
        except subprocess.CalledProcessError as e:
            raise TaskExecutionError(
                f"Command failed with exit code {e.returncode}. "
                f"stdout: {e.stdout}, stderr: {e.stderr}",
                original_error=e
            )
        except subprocess.TimeoutExpired as e:
            raise TaskExecutionError(
                f"Command timed out after {timeout} seconds. "
                f"stdout: {e.stdout}, stderr: {e.stderr}",
                original_error=e
            )
            
    except TaskExecutionError:
        raise
    except Exception as e:
        raise TaskExecutionError(
            f"Shell task failed: {str(e)}",
            original_error=e
        )
