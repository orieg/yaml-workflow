"""
File operation tasks for working with files and directories.
"""

import os
import json
import yaml
from typing import Any, Dict, List, Union

def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read contents of a text file.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding. Defaults to utf-8.
    
    Returns:
        str: Contents of the file
    """
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()

def write_file(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """
    Write content to a text file.
    
    Args:
        file_path: Path where to write the file
        content: Content to write
        encoding: File encoding. Defaults to utf-8.
    
    Returns:
        str: Path to the written file
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)
    return file_path

def read_json(file_path: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        Union[Dict[str, Any], List[Any]]: Parsed JSON data
    """
    with open(file_path, "r") as f:
        return json.load(f)

def write_json(file_path: str, data: Union[Dict[str, Any], List[Any]], indent: int = 2) -> str:
    """
    Write data to a JSON file.
    
    Args:
        file_path: Path where to write the JSON file
        data: Data to write
        indent: Number of spaces for indentation. Defaults to 2.
    
    Returns:
        str: Path to the written file
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=indent)
    return file_path

def read_yaml(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a YAML file.
    
    Args:
        file_path: Path to the YAML file
    
    Returns:
        Dict[str, Any]: Parsed YAML data
    """
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def write_yaml(file_path: str, data: Dict[str, Any]) -> str:
    """
    Write data to a YAML file.
    
    Args:
        file_path: Path where to write the YAML file
        data: Data to write
    
    Returns:
        str: Path to the written file
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return file_path 