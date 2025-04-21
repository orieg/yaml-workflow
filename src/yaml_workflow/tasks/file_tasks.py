"""
File operation tasks for working with files and directories.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TaskExecutionError, TemplateError
from ..workspace import resolve_path
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_error, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error


def ensure_directory(file_path: Path, step_name: str) -> None:
    """
    Ensure the directory exists for the given file path.

    Args:
        file_path: Path to the file
        step_name: Name of the step for error reporting

    Raises:
        TaskExecutionError: If directory cannot be created
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


# Direct file operations


def write_file_direct(
    file_path: str,
    content: str,
    workspace: Path,
    encoding: str = "utf-8",
    step_name: str = "write_file",
) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file
        content: Content to write
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)
        step_name: Name of the step for error reporting

    Returns:
        str: Path to written file

    Raises:
        TaskExecutionError: If file cannot be written or encoded
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        ensure_directory(resolved_path, step_name)
        with open(resolved_path, "wb") as f:
            f.write(content.encode(encoding))
        return str(resolved_path)
    except (IOError, UnicodeEncodeError) as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


def read_file_direct(
    file_path: str,
    workspace: Path,
    encoding: str = "utf-8",
    step_name: str = "read_file",
    logger=None,
) -> str:
    """Read content from a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)
        step_name: Name of the step for error reporting
        logger: Optional logger for debug output

    Returns:
        str: File content

    Raises:
        TaskExecutionError: If file cannot be read or decoded
    """
    try:
        if logger:
            logger.debug(f"Original file_path={file_path}")
            logger.debug(f"Workspace={workspace}, exists={workspace.exists()}")

        resolved_path = resolve_path(workspace, file_path)

        if logger:
            logger.debug(
                f"Resolved path={resolved_path}, exists={resolved_path.exists()}"
            )
            if not resolved_path.exists():
                parent_dir = resolved_path.parent
                logger.debug(
                    f"Parent directory={parent_dir}, exists={parent_dir.exists()}"
                )
                if parent_dir.exists():
                    logger.debug(f"Directory contents: {list(parent_dir.glob('*'))}")

        with open(resolved_path, "rb") as f:
            content = f.read().decode(encoding)
            if logger:
                logger.debug(f"Successfully read {len(content)} bytes from file")
            return content
    except (IOError, UnicodeDecodeError) as e:
        if logger:
            logger.error(f"ERROR: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"TRACEBACK:\n{traceback.format_exc()}")
        raise TaskExecutionError(step_name=step_name, original_error=e)


def append_file_direct(
    file_path: str,
    content: str,
    workspace: Path,
    encoding: str = "utf-8",
    step_name: str = "append_file",
) -> str:
    """Append content to a file.

    Args:
        file_path: Path to the file
        content: Content to append
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)
        step_name: Name of the step for error reporting

    Returns:
        str: Path to the file

    Raises:
        TaskExecutionError: If file cannot be appended to
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        ensure_directory(resolved_path, step_name)
        with open(resolved_path, "a", encoding=encoding) as f:
            f.write(content)
        return str(resolved_path)
    except (IOError, UnicodeEncodeError) as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


def copy_file_direct(
    source: str, destination: str, workspace: Path, step_name: str = "copy_file"
) -> str:
    """Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        workspace: Workspace directory
        step_name: Name of the step for error reporting

    Returns:
        str: Path to destination file

    Raises:
        TaskExecutionError: If file cannot be copied
    """
    try:
        source_path = resolve_path(workspace, source)
        dest_path = resolve_path(workspace, destination)
        ensure_directory(dest_path, step_name)
        shutil.copy2(source_path, dest_path)
        return str(dest_path)
    except (IOError, shutil.Error) as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


def move_file_direct(
    source: str, destination: str, workspace: Path, step_name: str = "move_file"
) -> str:
    """Move a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        workspace: Workspace directory
        step_name: Name of the step for error reporting

    Returns:
        str: Path to destination file

    Raises:
        TaskExecutionError: If file cannot be moved
    """
    try:
        source_path = resolve_path(workspace, source)
        dest_path = resolve_path(workspace, destination)
        ensure_directory(dest_path, step_name)
        shutil.move(str(source_path), str(dest_path))
        return str(dest_path)
    except (IOError, shutil.Error) as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


def delete_file_direct(
    file_path: str, workspace: Path, step_name: str = "delete_file"
) -> str:
    """Delete a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory
        step_name: Name of the step for error reporting

    Returns:
        str: Path to deleted file

    Raises:
        TaskExecutionError: If file cannot be deleted
    """
    try:
        resolved_path = resolve_path(workspace, file_path)
        if resolved_path.exists():
            resolved_path.unlink()
        return str(resolved_path)
    except IOError as e:
        raise TaskExecutionError(step_name=step_name, original_error=e)


# Task handlers


@register_task("write_file")
def write_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Write content to a file."""
    task_name = str(config.name or "write_file")
    task_type = config.type or "write_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path = processed.get("file")
        content = processed.get("content")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("No file path provided")
        if content is None:
            raise ValueError("No content provided")

        result = write_file_direct(
            file_path, str(content), config.workspace, encoding, task_name
        )
        output = {"path": result, "content": content}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("read_file")
def read_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Read content from a file."""
    task_name = str(config.name or "read_file")
    task_type = config.type or "read_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path_input = processed.get("file")

        # Debug logging
        logger.debug(
            f"Workspace={config.workspace}, exists={config.workspace.exists()}"
        )
        logger.debug(f"file_path param={file_path_input}")
        logger.debug(f"All inputs={processed}")

        encoding = processed.get("encoding", "utf-8")

        if not file_path_input:
            error_msg = "No file path provided (param 'file' is missing)"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Debug: Print resolved path
        resolved_path = str(resolve_path(config.workspace, file_path_input))
        logger.debug(f"Resolved path={resolved_path}")

        # Check if file exists before trying to read it
        resolved_file = Path(resolved_path)
        logger.debug(f"File exists={resolved_file.exists()}")
        if not resolved_file.exists():
            parent_dir = resolved_file.parent
            logger.debug(f"Parent directory={parent_dir}, exists={parent_dir.exists()}")
            if parent_dir.exists():
                logger.debug(f"Directory contents: {list(parent_dir.glob('*'))}")

        content = read_file_direct(
            file_path_input, config.workspace, encoding, task_name, logger=logger
        )
        output = {"path": file_path_input, "content": content}
        log_task_result(logger, output)
        return output
    except Exception as e:
        # Debug: Print detailed exception info
        logger.error(f"EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback

        logger.error(f"TRACEBACK:\n{traceback.format_exc()}")

        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("append_file")
def append_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Append content to a file."""
    task_name = str(config.name or "append_file")
    task_type = config.type or "append_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path = processed.get("file")
        content = processed.get("content")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("No file path provided")
        if content is None:
            raise ValueError("No content provided")

        result = append_file_direct(
            file_path, str(content), config.workspace, encoding, task_name
        )
        output = {"path": result, "content": content}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("copy_file")
def copy_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Copy a file from source to destination."""
    task_name = str(config.name or "copy_file")
    task_type = config.type or "copy_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        source = processed.get("source")
        destination = processed.get("destination")

        if not source:
            raise ValueError("No source file provided")
        if not destination:
            raise ValueError("No destination file provided")

        result = copy_file_direct(source, destination, config.workspace, task_name)
        output = {"source": source, "destination": result}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("move_file")
def move_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Move a file from source to destination."""
    task_name = str(config.name or "move_file")
    task_type = config.type or "move_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        source = processed.get("source")
        destination = processed.get("destination")

        if not source:
            raise ValueError("No source file provided")
        if not destination:
            raise ValueError("No destination file provided")

        result = move_file_direct(source, destination, config.workspace, task_name)
        output = {"source": source, "destination": result}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("delete_file")
def delete_file_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Delete a file."""
    task_name = str(config.name or "delete_file")
    task_type = config.type or "delete_file"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path = processed.get("file")

        if not file_path:
            raise ValueError("No file path provided")

        result = delete_file_direct(file_path, config.workspace, task_name)
        output = {"path": result}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("read_json")
def read_json_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Task handler for reading JSON files."""
    task_name = str(config.name or "read_json")
    task_type = config.type or "read_json"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        file_path = processed.get("file")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("No file path provided")

        result_data = read_json(file_path, config.workspace, encoding=encoding)
        output = {"data": result_data}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("write_json")
def write_json_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Write JSON data to a file."""
    task_name = str(config.name or "write_json")
    task_type = config.type or "write_json"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path = processed.get("file")

        # Debug: Print workspace and file path info
        logger.debug(
            f"Workspace={config.workspace}, exists={config.workspace.exists()}"
        )
        logger.debug(f"file_path param={file_path}")
        logger.debug(f"All inputs={processed}")

        data = processed.get("data")
        indent = int(processed.get("indent", 2))
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            error_msg = "No file path provided (param 'file' is missing)"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if data is None:
            error_msg = "No data provided"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Ensure output directory exists
        if "output/" in file_path:
            output_dir = config.workspace / "output"
            logger.debug(
                f"Creating output dir {output_dir}, exists={output_dir.exists()}"
            )
            output_dir.mkdir(exist_ok=True, parents=True)

        # Debug: Print resolved path
        resolved_path = str(resolve_path(config.workspace, file_path))
        logger.debug(f"Resolved path={resolved_path}")

        result_path = write_json_direct(
            file_path,
            data,
            indent=indent,
            workspace=config.workspace,
            encoding=encoding,
            step_name=task_name,
            logger=logger,
        )

        # Debug: Check if file was created
        result_file = Path(result_path)
        logger.debug(f"Result path={result_path}, exists={result_file.exists()}")

        output = {"path": result_path}
        log_task_result(logger, output)
        return output
    except Exception as e:
        # Debug: Print detailed exception info
        logger.error(f"EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback

        logger.error(f"TRACEBACK:\n{traceback.format_exc()}")

        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("read_yaml")
def read_yaml_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Task handler for reading YAML files."""
    task_name = str(config.name or "read_yaml")
    task_type = config.type or "read_yaml"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        file_path = processed.get("file")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("No file path provided")

        result_data = read_yaml(file_path, config.workspace, encoding=encoding)
        output = {"data": result_data}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


@register_task("write_yaml")
def write_yaml_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """Write YAML data to a file."""
    task_name = str(config.name or "write_yaml")
    task_type = config.type or "write_yaml"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)
    try:
        processed = config.process_inputs()
        file_path = processed.get("file")
        data = processed.get("data")
        encoding = processed.get("encoding", "utf-8")

        if not file_path:
            raise ValueError("No file path provided")
        if data is None:
            raise ValueError("No data provided")

        result_path = write_yaml_direct(
            file_path,
            data,
            workspace=config.workspace,
            encoding=encoding,
            step_name=task_name,
        )
        output = {"path": result_path}
        log_task_result(logger, output)
        return output
    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None


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
    file_path: str, workspace: Path, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """Read JSON content from a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)

    Returns:
        Dict[str, Any]: Parsed JSON content

    Raises:
        TaskExecutionError: If file cannot be read or JSON is invalid
    """
    try:
        content = read_file_direct(file_path, workspace, encoding)
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise TaskExecutionError(step_name="read_json", original_error=e)


def write_json_direct(
    file_path: str,
    data: Union[Dict[str, Any], List[Any]],
    indent: int = 2,
    workspace: Path = Path("."),
    encoding: str = "utf-8",
    step_name: str = "write_json",
    logger=None,
) -> str:
    """Write JSON data to a file.

    Args:
        file_path: Path to the file
        data: Data to write
        indent: Indentation level (default: 2)
        workspace: Optional workspace directory
        encoding: File encoding (default: utf-8)
        step_name: Name of the step for error reporting
        logger: Optional logger for debug output

    Returns:
        str: Path to written file

    Raises:
        TemplateError: If file cannot be written
    """
    try:
        if logger:
            logger.debug(f"Original file_path={file_path}")
            logger.debug(f"Workspace={workspace}, exists={workspace.exists()}")

        if workspace:
            file_path = str(resolve_path(workspace, file_path))
            if logger:
                logger.debug(f"Resolved file_path={file_path}")
                dir_path = Path(file_path).parent
                logger.debug(f"Directory path={dir_path}, exists={dir_path.exists()}")
            ensure_directory(Path(file_path), step_name)
            if logger:
                dir_path = Path(file_path).parent
                logger.debug(f"After ensure_directory, dir exists={dir_path.exists()}")

        if logger:
            logger.debug(f"Writing JSON to {file_path}")
        with open(file_path, "w") as f:
            json.dump(data, f, indent=indent)

        # Verify file was created
        if logger:
            created_file = Path(file_path)
            logger.debug(
                f"File created, exists={created_file.exists()}, size={created_file.stat().st_size if created_file.exists() else 'N/A'}"
            )

        return file_path
    except (IOError, TypeError) as e:
        if logger:
            logger.error(f"ERROR: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"TRACEBACK:\n{traceback.format_exc()}")
        raise TemplateError(f"Failed to write JSON file '{file_path}': {str(e)}")


def read_yaml(
    file_path: str, workspace: Path, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """Read YAML content from a file.

    Args:
        file_path: Path to the file
        workspace: Workspace directory
        encoding: File encoding (default: utf-8)

    Returns:
        Dict[str, Any]: Parsed YAML content

    Raises:
        TaskExecutionError: If file cannot be read or YAML is invalid
    """
    try:
        content = read_file_direct(file_path, workspace, encoding)
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise TaskExecutionError(step_name="read_yaml", original_error=e)


def write_yaml_direct(
    file_path: str,
    data: Dict[str, Any],
    workspace: Path = Path("."),
    encoding: str = "utf-8",
    step_name: str = "write_yaml",
) -> str:
    """Write YAML data to a file.

    Args:
        file_path: Path to the file
        data: Data to write
        workspace: Optional workspace directory
        encoding: File encoding (default: utf-8)
        step_name: Name of the step for error reporting

    Returns:
        str: Path to written file

    Raises:
        TemplateError: If file cannot be written
    """
    try:
        if workspace:
            file_path = str(resolve_path(workspace, file_path))
            ensure_directory(Path(file_path), step_name)

        with open(file_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        return file_path
    except (IOError, yaml.YAMLError) as e:
        raise TemplateError(f"Failed to write YAML file '{file_path}': {str(e)}")
