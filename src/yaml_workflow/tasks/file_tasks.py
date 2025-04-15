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
from . import register_task
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
def write_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for writing files."""
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
            result = write_file_direct(file_path, content, workspace, encoding)

        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_file")
def read_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for reading files.

    Returns:
        str: Raw file contents as a string
    """
    logger = get_task_logger(workspace, step.get("name", "read_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        params = step.get("params", {})
        file_path = params.get("file_path")
        encoding = params.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("file_path parameter is required")

        content = read_file_direct(file_path, workspace, encoding)
        # Log the raw content for debugging
        logger.debug(f"Read file content: {content}")
        log_task_result(logger, content)
        return content

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("append_file")
def append_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for appending to files."""
    logger = get_task_logger(workspace, step.get("name", "append_file"))
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

        result = append_file_direct(file_path, content, workspace, encoding)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("copy_file")
def copy_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for copying files."""
    logger = get_task_logger(workspace, step.get("name", "copy_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        params = step.get("params", {})
        source = params.get("source")
        destination = params.get("destination")

        if not source:
            raise ValueError("source parameter is required")
        if not destination:
            raise ValueError("destination parameter is required")

        result = copy_file_direct(source, destination, workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("move_file")
def move_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for moving files."""
    logger = get_task_logger(workspace, step.get("name", "move_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        params = step.get("params", {})
        source = params.get("source")
        destination = params.get("destination")

        if not source:
            raise ValueError("source parameter is required")
        if not destination:
            raise ValueError("destination parameter is required")

        result = move_file_direct(source, destination, workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("delete_file")
def delete_file_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """Task handler for deleting files."""
    logger = get_task_logger(workspace, step.get("name", "delete_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        params = step.get("params", {})
        file_path = params.get("file_path")

        if not file_path:
            raise ValueError("file_path parameter is required")

        result = delete_file_direct(file_path, workspace)
        log_task_result(logger, result)
        return result

    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_json")
def read_json_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Union[Dict[str, Any], List[Any]]:
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
def write_json_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
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

    # Process templates in data
    processed_data = process_templates(data, context)

    return write_json(file_path, processed_data, indent, workspace)


@register_task("read_yaml")
def read_yaml_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
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


def process_templates(data: Any, context: Dict[str, Any]) -> Any:
    """
    Process Jinja2 templates in data recursively.

    Args:
        data: Data to process
        context: Template context

    Returns:
        Any: Processed data

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
                "vars": {k: type(v).__name__ for k, v in context.items() 
                        if k not in ["args", "env", "steps"]}
            }
            raise TemplateError(
                f"Failed to resolve variable in template '{data}': {str(e)}. "
                f"Available variables: {available}"
            )
        except Exception as e:
            raise TemplateError(f"Failed to process template '{data}': {str(e)}")
    elif isinstance(data, dict):
        return {k: process_templates(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [process_templates(v, context) for v in data]
    return data


@register_task("write_yaml")
def write_yaml_task(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
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

    # Process templates in data
    processed_data = process_templates(data, context)

    return write_yaml(file_path, processed_data, workspace)


# Helper functions
def read_json(
    file_path: str, workspace: Optional[Path] = None
) -> Union[Dict[str, Any], List[Any]]:
    """
    Read content from a JSON file.

    Args:
        file_path: Path to the JSON file
        workspace: Optional workspace directory for relative paths

    Returns:
        Union[Dict[str, Any], List[Any]]: Parsed JSON content

    Raises:
        TemplateError: If file cannot be read or contains invalid JSON
    """
    try:
        path = resolve_path(workspace, file_path) if workspace else Path(file_path)
        with path.open("r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise TemplateError(f"Invalid JSON in file '{file_path}': {str(e)}")
    except IOError as e:
        raise TemplateError(f"Failed to read JSON file '{file_path}': {str(e)}")


def write_json(
    file_path: str,
    data: Union[Dict[str, Any], List[Any]],
    indent: int = 2,
    workspace: Optional[Path] = None,
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
        TemplateError: If data cannot be serialized or file cannot be written
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")

    try:
        path = resolve_path(workspace, file_path) if workspace else Path(file_path)
        ensure_directory(path)

        with path.open("w") as f:
            json.dump(data, f, indent=indent)
        return str(path)
    except TypeError as e:
        raise TemplateError(f"Failed to serialize data to JSON: {str(e)}")
    except IOError as e:
        raise TemplateError(f"Failed to write JSON file '{file_path}': {str(e)}")


def read_yaml(file_path: str, workspace: Optional[Path] = None) -> Dict[str, Any]:
    """
    Read content from a YAML file.

    Args:
        file_path: Path to the YAML file
        workspace: Optional workspace directory for relative paths

    Returns:
        Dict[str, Any]: Parsed YAML content

    Raises:
        TemplateError: If file cannot be read or contains invalid YAML
    """
    try:
        path = resolve_path(workspace, file_path) if workspace else Path(file_path)
        with path.open("r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TemplateError(f"Invalid YAML in file '{file_path}': {str(e)}")
    except IOError as e:
        raise TemplateError(f"Failed to read YAML file '{file_path}': {str(e)}")


def write_yaml(
    file_path: str, data: Dict[str, Any], workspace: Optional[Path] = None
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
        TemplateError: If data cannot be serialized or file cannot be written
    """
    if not file_path:
        raise ValueError("file_path cannot be empty")

    try:
        path = resolve_path(workspace, file_path) if workspace else Path(file_path)
        ensure_directory(path)

        with path.open("w") as f:
            yaml.dump(data, f)
        return str(path)
    except yaml.YAMLError as e:
        raise TemplateError(f"Failed to serialize data to YAML: {str(e)}")
    except IOError as e:
        raise TemplateError(f"Failed to write YAML file '{file_path}': {str(e)}")
