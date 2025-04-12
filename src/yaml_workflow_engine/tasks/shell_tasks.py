"""
Shell operation tasks for executing commands and managing processes.
"""

import os
import subprocess
from typing import Dict, List, Optional, Tuple, Union

def run_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    timeout: Optional[float] = None
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
        timeout=timeout
    )
    
    return result.returncode, result.stdout, result.stderr

def check_command(
    command: Union[str, List[str]],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
    timeout: Optional[float] = None
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
        check=True
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