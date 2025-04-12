"""
File operation tasks for working with files and directories.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..workspace import resolve_path

def ensure_directory(file_path: Path) -> None:
    """
    Ensure the directory exists for the given file path.
    
    Args:
        file_path: Path to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

def read_file(
    file_path: str,
    encoding: str = "utf-8",
    workspace: Optional[Path] = None
) -> str:
    """
    Read contents of a text file.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding. Defaults to utf-8.
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Contents of the file
        
    Raises:
        FileNotFoundError: If the file does not exist
        IOError: If there's an error reading the file
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
        file_path: Path where to write the file (relative or absolute)
        content: Content to write
        encoding: File encoding. Defaults to utf-8.
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Absolute path to the written file
        
    Raises:
        IOError: If there's an error writing the file
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
    Read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        workspace: Optional workspace directory for relative paths
    
    Returns:
        Union[Dict[str, Any], List[Any]]: Parsed JSON data
        
    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file is not valid JSON
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
    Write data to a JSON file.
    
    Args:
        file_path: Path where to write the JSON file
        data: Data to write
        indent: Number of spaces for indentation. Defaults to 2.
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Absolute path to the written file
        
    Raises:
        ValueError: If file_path is empty or data is not JSON serializable
        IOError: If there's an error writing the file
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
    Read and parse a YAML file.
    
    Args:
        file_path: Path to the YAML file
        workspace: Optional workspace directory for relative paths
    
    Returns:
        Dict[str, Any]: Parsed YAML data
        
    Raises:
        FileNotFoundError: If the file does not exist
        yaml.YAMLError: If the file is not valid YAML
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
    Write data to a YAML file.
    
    Args:
        file_path: Path where to write the YAML file
        data: Data to write
        workspace: Optional workspace directory for relative paths
    
    Returns:
        str: Absolute path to the written file
        
    Raises:
        ValueError: If file_path is empty or data is not YAML serializable
        IOError: If there's an error writing the file
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")
        
    path = resolve_path(workspace, file_path) if workspace else Path(file_path)
    ensure_directory(path)
    
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return str(path) 