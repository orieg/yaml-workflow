"""
File operation tasks for working with files and directories.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import Template, StrictUndefined, UndefinedError

from ..workspace import resolve_path
from ..exceptions import TemplateError
from . import register_task, TaskConfig
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result


def ensure_directory(file_path: Path) -> None:
    """
    Ensure the directory exists for the given file path.

    Args:
        file_path: Path to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


# Direct file operations


def write_file_direct(
    file_path: str, content: str, workspace: Path, encoding: str = "utf-8"
) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file
        content: Content to write
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)

    Returns:
        str: Path to written file

    Raises:
        TemplateError: If template resolution fails
        IOError: If file cannot be written
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        ensure_directory(resolved_path)
        with open(resolved_path, "wb") as f:
            f.write(content.encode(encoding))
        return str(resolved_path)
    except IOError as e:
        raise TemplateError(f"Failed to write file '{file_path}': {str(e)}")


def read_file_direct(file_path: str, workspace: Path, encoding: str = "utf-8") -> str:
    """Read content from a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)

    Returns:
        str: File content

    Raises:
        TemplateError: If file cannot be read or decoded
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        with open(resolved_path, "rb") as f:
            return f.read().decode(encoding)
    except (IOError, UnicodeDecodeError) as e:
        raise TemplateError(f"Failed to read file '{file_path}': {str(e)}")


def append_file_direct(
    file_path: str, content: str, workspace: Path, encoding: str = "utf-8"
) -> str:
    """Append content to a file.

    Args:
        file_path: Path to the file
        content: Content to append
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)

    Returns:
        str: Path to the file

    Raises:
        TemplateError: If file cannot be appended to
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        ensure_directory(resolved_path)
        with open(resolved_path, "a", encoding=encoding) as f:
            f.write(content)
        return str(resolved_path)
    except IOError as e:
        raise TemplateError(f"Failed to append to file '{file_path}': {str(e)}")


def copy_file_direct(source: str, destination: str, workspace: Path) -> str:
    """Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        workspace: Workspace directory

    Returns:
        str: Path to destination file

    Raises:
        TemplateError: If file cannot be copied
    """
    try:
        source_path = resolve_path(workspace, source)
        dest_path = resolve_path(workspace, destination)
        ensure_directory(dest_path)
        shutil.copy2(source_path, dest_path)
        return str(dest_path)
    except (IOError, shutil.Error) as e:
        raise TemplateError(f"Failed to copy file from '{source}' to '{destination}': {str(e)}")


def move_file_direct(source: str, destination: str, workspace: Path) -> str:
    """Move a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        workspace: Workspace directory

    Returns:
        str: Path to destination file

    Raises:
        TemplateError: If file cannot be moved
    """
    try:
        source_path = resolve_path(workspace, source)
        dest_path = resolve_path(workspace, destination)
        ensure_directory(dest_path)
        shutil.move(str(source_path), str(dest_path))
        return str(dest_path)
    except (IOError, shutil.Error) as e:
        raise TemplateError(f"Failed to move file from '{source}' to '{destination}': {str(e)}")


def delete_file_direct(file_path: str, workspace: Path) -> str:
    """Delete a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory

    Returns:
        str: Path to deleted file

    Raises:
        TemplateError: If file cannot be deleted
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        if resolved_path.exists():
            resolved_path.unlink()
        return str(resolved_path)
    except IOError as e:
        raise TemplateError(f"Failed to delete file '{file_path}': {str(e)}")


# Task handlers


@register_task("write_file")
def write_file_task(config: TaskConfig) -> str:
    """Task handler for writing files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        # Process inputs with template resolution
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")
        content = processed.get("content")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("file_path parameter is required")
        if content is None:
            raise ValueError("content parameter is required")

        result = write_file_direct(file_path, content, config.workspace, encoding)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_file")
def read_file_task(config: TaskConfig) -> str:
    """Task handler for reading files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("file_path parameter is required")

        result = read_file_direct(file_path, config.workspace, encoding)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("append_file")
def append_file_task(config: TaskConfig) -> str:
    """Task handler for appending to files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")
        content = processed.get("content")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("file_path parameter is required")
        if content is None:
            raise ValueError("content parameter is required")

        result = append_file_direct(file_path, content, config.workspace, encoding)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("copy_file")
def copy_file_task(config: TaskConfig) -> str:
    """Task handler for copying files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        source = processed.get("source")
        destination = processed.get("destination")

        if not source:
            raise ValueError("source parameter is required")
        if not destination:
            raise ValueError("destination parameter is required")

        result = copy_file_direct(source, destination, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("move_file")
def move_file_task(config: TaskConfig) -> str:
    """Task handler for moving files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        source = processed.get("source")
        destination = processed.get("destination")

        if not source:
            raise ValueError("source parameter is required")
        if not destination:
            raise ValueError("destination parameter is required")

        result = move_file_direct(source, destination, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("delete_file")
def delete_file_task(config: TaskConfig) -> str:
    """Task handler for deleting files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")

        if not file_path:
            raise ValueError("file_path parameter is required")

        result = delete_file_direct(file_path, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_json")
def read_json_task(config: TaskConfig) -> Union[Dict[str, Any], List[Any]]:
    """Task handler for reading JSON files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")

        if not file_path:
            raise ValueError("file_path parameter is required")

        result = read_json(file_path, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("write_json")
def write_json_task(config: TaskConfig) -> str:
    """Task handler for writing JSON files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")
        data = processed.get("data")
        indent = processed.get("indent", 2)

        if not file_path:
            raise ValueError("file_path parameter is required")
        if data is None:
            raise ValueError("data parameter is required")

        result = write_json(file_path, data, indent, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_yaml")
def read_yaml_task(config: TaskConfig) -> Dict[str, Any]:
    """Task handler for reading YAML files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")

        if not file_path:
            raise ValueError("file_path parameter is required")

        result = read_yaml(file_path, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("write_yaml")
def write_yaml_task(config: TaskConfig) -> str:
    """Task handler for writing YAML files."""
    logger = get_task_logger(config.workspace, config.name)
    log_task_execution(logger, {"name": config.name, "type": config.type}, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        
        file_path = processed.get("file_path")
        data = processed.get("data")

        if not file_path:
            raise ValueError("file_path parameter is required")
        if data is None:
            raise ValueError("data parameter is required")

        result = write_yaml(file_path, data, config.workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


def process_templates(data: Any, context: Dict[str, Any]) -> Any:
    """Process template strings in data structure.

    Args:
        data: Data structure to process
        context: Template context

    Returns:
        Any: Processed data structure

    Raises:
        TemplateError: If template resolution fails
    """
    if isinstance(data, str):
        try:
            template = Template(data, undefined=StrictUndefined)
            return template.render(**context)
        except UndefinedError as e:
            available = {
                "args": list(context["args"].keys()) if "args" in context else [],
                "env": list(context["env"].keys()) if "env" in context else [],
                "steps": list(context["steps"].keys()) if "steps" in context else [],
            }
            raise TemplateError(
                f"Failed to resolve variable in template '{data}': {str(e)}. "
                f"Available variables: {available}"
            )
    elif isinstance(data, dict):
        return {k: process_templates(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_templates(v, context) for v in data]
    return data


def read_json(
    file_path: str, workspace: Optional[Path] = None
) -> Union[Dict[str, Any], List[Any]]:
    """Read JSON data from a file.

    Args:
        file_path: Path to the file
        workspace: Optional workspace directory

    Returns:
        Union[Dict[str, Any], List[Any]]: JSON data

    Raises:
        TemplateError: If file cannot be read or parsed
    """
    try:
        if workspace:
            file_path = str(resolve_path(workspace, file_path))

        with open(file_path, "r") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        if isinstance(e, json.JSONDecodeError):
            raise TemplateError(f"Invalid JSON in file '{file_path}': {str(e)}")
        raise TemplateError(f"Failed to read JSON file '{file_path}': {str(e)}")


def write_json(
    file_path: str,
    data: Union[Dict[str, Any], List[Any]],
    indent: int = 2,
    workspace: Optional[Path] = None,
) -> str:
    """Write JSON data to a file.

    Args:
        file_path: Path to the file
        data: Data to write
        indent: Indentation level (default: 2)
        workspace: Optional workspace directory

    Returns:
        str: Path to written file

    Raises:
        TemplateError: If file cannot be written
    """
    try:
        if workspace:
            file_path = str(resolve_path(workspace, file_path))
            ensure_directory(Path(file_path))

        with open(file_path, "w") as f:
            json.dump(data, f, indent=indent)
        return file_path
    except (IOError, TypeError) as e:
        raise TemplateError(f"Failed to write JSON file '{file_path}': {str(e)}")


def read_yaml(file_path: str, workspace: Optional[Path] = None) -> Dict[str, Any]:
    """Read YAML data from a file.

    Args:
        file_path: Path to the file
        workspace: Optional workspace directory

    Returns:
        Dict[str, Any]: YAML data

    Raises:
        TemplateError: If file cannot be read or parsed
    """
    try:
        if workspace:
            file_path = str(resolve_path(workspace, file_path))

        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    except (IOError, yaml.YAMLError) as e:
        if isinstance(e, yaml.YAMLError):
            raise TemplateError(f"Invalid YAML in file '{file_path}': {str(e)}")
        raise TemplateError(f"Failed to read YAML file '{file_path}': {str(e)}")


def write_yaml(
    file_path: str, data: Dict[str, Any], workspace: Optional[Path] = None
) -> str:
    """Write YAML data to a file.

    Args:
        file_path: Path to the file
        data: Data to write
        workspace: Optional workspace directory

    Returns:
        str: Path to written file

    Raises:
        TemplateError: If file cannot be written
    """
    try:
        if workspace:
            file_path = str(resolve_path(workspace, file_path))
            ensure_directory(Path(file_path))

        with open(file_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        return file_path
    except (IOError, yaml.YAMLError) as e:
        raise TemplateError(f"Failed to write YAML file '{file_path}': {str(e)}")
