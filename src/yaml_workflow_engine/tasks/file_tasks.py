"""
File operation tasks for working with files and directories.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..workspace import resolve_path
from .base import get_task_logger, log_task_execution, log_task_result, log_task_error
from . import register_task

def ensure_directory(file_path: Path) -> None:
    """
    Ensure the directory exists for the given file path.
    
    Args:
        file_path: Path to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

@register_task("read_file")
def read_file_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> str:
    """
    Task handler for reading files.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        str: File content
    """
    logger = get_task_logger(workspace, step.get("name", "read_file"))
    log_task_execution(logger, step, context, workspace)
    
    try:
        params = step.get("params", {})
        file_path = params.get("file_path")
        encoding = params.get("encoding", "utf-8")
        
        if not file_path:
            raise ValueError("file_path parameter is required")
        
        if params.get("format") == "json":
            result = read_json(file_path, workspace)
        elif params.get("format") == "yaml":
            result = read_yaml(file_path, workspace)
        else:
            result = read_file(file_path, encoding, workspace)
            
        log_task_result(logger, result)
        return result
        
    except Exception as e:
        log_task_error(logger, e)
        raise

@register_task("write_file")
def write_file_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> str:
    """
    Task handler for writing files.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        str: Path to written file
    """
    logger = get_task_logger(workspace, step.get("name", "write_file"))
    log_task_execution(logger, step, context, workspace)
    
    try:
        params = step.get("params", {})
        file_path = params.get("file_path")
        content = params.get("content")
        encoding = params.get("encoding", "utf-8")
        
        if not file_path:
            raise ValueError("file_path parameter is required")
        if content is None:
            raise ValueError("content parameter is required")
        
        if params.get("format") == "json":
            result = write_json(file_path, content, params.get("indent", 2), workspace)
        elif params.get("format") == "yaml":
            result = write_yaml(file_path, content, workspace)
        else:
            if not isinstance(content, str):
                content = str(content)
            result = write_file(file_path, content, encoding, workspace)
            
        log_task_result(logger, result)
        return result
        
    except Exception as e:
        log_task_error(logger, e)
        raise

@register_task("read_json")
def read_json_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Union[Dict[str, Any], List[Any]]:
    """
    Task handler for reading a JSON file.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        Union[Dict[str, Any], List[Any]]: Parsed JSON data
    """
    params = step.get("params", {})
    file_path = params.get("file_path")
    
    if not file_path:
        raise ValueError("file_path parameter is required")
    
    return read_json(file_path, workspace)

@register_task("write_json")
def write_json_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> str:
    """
    Task handler for writing a JSON file.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        str: Path to written file
    """
    params = step.get("params", {})
    file_path = params.get("file_path")
    data = params.get("data")
    indent = params.get("indent", 2)
    
    if not file_path:
        raise ValueError("file_path parameter is required")
    if data is None:
        raise ValueError("data parameter is required")
    
    return write_json(file_path, data, indent, workspace)

@register_task("read_yaml")
def read_yaml_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    """
    Task handler for reading a YAML file.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        Dict[str, Any]: Parsed YAML data
    """
    params = step.get("params", {})
    file_path = params.get("file_path")
    
    if not file_path:
        raise ValueError("file_path parameter is required")
    
    return read_yaml(file_path, workspace)

@register_task("write_yaml")
def write_yaml_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> str:
    """
    Task handler for writing a YAML file.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        str: Path to written file
    """
    params = step.get("params", {})
    file_path = params.get("file_path")
    data = params.get("data")
    
    if not file_path:
        raise ValueError("file_path parameter is required")
    if data is None:
        raise ValueError("data parameter is required")
    
    return write_yaml(file_path, data, workspace)

# Helper functions
def read_file(
    file_path: str,
    encoding: str = "utf-8",
    workspace: Optional[Path] = None
) -> str:
    """
    Read content from a text file.
    
    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: File content
        
    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    with path.open("r", encoding=encoding) as f:
        return f.read()

def write_file(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    workspace: Optional[Path] = None
) -> str:
    """
    Write content to a text file.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding (default: utf-8)
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Path to written file
        
    Raises:
        IOError: If file cannot be written
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
        
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    ensure_directory(path)
    
    with path.open("w", encoding=encoding) as f:
        f.write(content)
    return str(path)

def read_json(
    file_path: str,
    workspace: Optional[Path] = None
) -> Union[Dict[str, Any], List[Any]]:
    """
    Read content from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        workspace: Optional workspace directory for relative paths
    
    Returns:
        Union[Dict[str, Any], List[Any]]: Parsed JSON content
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    with path.open("r") as f:
        return json.load(f)

def write_json(
    file_path: str,
    data: Union[Dict[str, Any], List[Any]],
    indent: int = 2,
    workspace: Optional[Path] = None
) -> str:
    """
    Write content to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: Data to write
        indent: JSON indentation (default: 2)
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Path to written file
        
    Raises:
        TypeError: If data cannot be serialized to JSON
        IOError: If file cannot be written
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
        
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    ensure_directory(path)
    
    with path.open("w") as f:
        json.dump(data, f, indent=indent)
    return str(path)

def read_yaml(
    file_path: str,
    workspace: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Read content from a YAML file.
    
    Args:
        file_path: Path to the YAML file
        workspace: Optional workspace directory for relative paths
    
    Returns:
        Dict[str, Any]: Parsed YAML content
        
    Raises:
        FileNotFoundError: If file does not exist
        yaml.YAMLError: If file contains invalid YAML
    """
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    with path.open("r") as f:
        return yaml.safe_load(f)

def write_yaml(
    file_path: str,
    data: Dict[str, Any],
    workspace: Optional[Path] = None
) -> str:
    """
    Write content to a YAML file.
    
    Args:
        file_path: Path to the YAML file
        data: Data to write
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Path to written file
        
    Raises:
        yaml.YAMLError: If data cannot be serialized to YAML
        IOError: If file cannot be written
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
        
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    ensure_directory(path)
    
    with path.open("w") as f:
        yaml.dump(data, f)
    return str(path) 