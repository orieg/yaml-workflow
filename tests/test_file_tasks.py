import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, cast

import pytest
import yaml

from yaml_workflow.exceptions import TaskExecutionError, TemplateError
from yaml_workflow.tasks import TaskConfig, register_task
from yaml_workflow.tasks.base import (
    get_task_logger,
    log_task_error,
    log_task_execution,
    log_task_result,
)
from yaml_workflow.tasks.file_tasks import (
    append_file_direct,
    append_file_task,
    copy_file_direct,
    delete_file_direct,
    move_file_direct,
    read_file_direct,
    read_file_task,
    read_json,
    read_yaml,
    write_file_direct,
    write_json_direct,
    write_json_task,
    write_yaml_direct,
    write_yaml_task,
)


@pytest.fixture
def sample_data():
    """Create sample data for file operations."""
    return {
        "name": "Test User",
        "age": 30,
        "items": ["item1", "item2"],
        "settings": {"theme": "dark", "notifications": True},
    }


@register_task("write_file")
def write_file(config: TaskConfig) -> Any:
    """Write content to a file."""
    task_name = config.name or "write_file_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        processed = config.process_inputs()
        file_path = processed["path"]
        content = processed["content"]

        path = config.workspace / file_path
        os.makedirs(path.parent, exist_ok=True)

        with open(path, "w") as f:
            f.write(content)

        result = {"path": str(path)}
        log_task_result(logger, result)
        return cast(Any, result)
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_file")
def read_file(config: TaskConfig) -> Any:
    """Read content from a file."""
    task_name = config.name or "read_file_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        processed = config.process_inputs()
        file_path = processed["path"]

        path = config.workspace / file_path
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path) as f:
            content = f.read()

        result = {"content": content}
        log_task_result(logger, result)
        return cast(Any, result)
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("copy_file")
def copy_file(config: TaskConfig) -> Dict[str, Any]:
    """Copy a file from source to destination."""
    task_name = config.name or "copy_file_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        processed = config.process_inputs()
        source = processed["source"]
        destination = processed["destination"]

        src = config.workspace / source
        dst = config.workspace / destination

        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        os.makedirs(dst.parent, exist_ok=True)
        shutil.copy2(src, dst)

        result = {"source": str(src), "destination": str(dst)}
        log_task_result(logger, result)
        return result
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("move_file")
def move_file(config: TaskConfig) -> Dict[str, Any]:
    """Move a file from source to destination."""
    task_name = config.name or "move_file_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        processed = config.process_inputs()
        source = processed["source"]
        destination = processed["destination"]

        src = config.workspace / source
        dst = config.workspace / destination

        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        os.makedirs(dst.parent, exist_ok=True)
        shutil.move(src, dst)

        result = {"source": str(src), "destination": str(dst)}
        log_task_result(logger, result)
        return result
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("delete_file")
def delete_file(config: TaskConfig) -> Any:
    """Delete a file."""
    task_name = config.name or "delete_file_task"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(
        logger,
        {"name": task_name, "type": config.type},
        config._context,
        config.workspace,
    )

    try:
        processed = config.process_inputs()
        file_path = processed["path"]

        path = config.workspace / file_path
        if path.exists():
            os.remove(path)

        result = {"path": str(path)}
        log_task_result(logger, result)
        return cast(Any, result)
    except Exception as e:
        log_task_error(logger, e)
        raise


def test_write_text_file_direct(temp_workspace):
    """Test writing text file using direct function."""
    file_path = temp_workspace / "test.txt"
    content = "Hello, World!"
    result = write_file_direct(str(file_path), content, temp_workspace)
    assert result == str(file_path)
    assert Path(file_path).read_text() == content


def test_write_text_file_task(temp_workspace):
    """Test writing text file using task handler."""
    file_path = "test.txt"
    content = "Hello, World!"
    step = {
        "name": "write_test",
        "task": "write_file",
        "inputs": {
            "path": file_path,
            "content": content,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_file(config)
    assert result["path"] == str(temp_workspace / file_path)
    assert Path(temp_workspace / file_path).read_text() == content


def test_read_text_file_direct(temp_workspace):
    """Test reading text file using direct function."""
    file_path = temp_workspace / "test.txt"
    content = "Hello, World!"
    file_path.write_text(content)
    result = read_file_direct(str(file_path), temp_workspace)
    assert result == content


def test_read_text_file_task(temp_workspace):
    """Test reading text file using task handler."""
    file_path = "test.txt"
    content = "Hello, World!"
    (temp_workspace / file_path).write_text(content)
    step = {
        "name": "read_test",
        "task": "read_file",
        "inputs": {
            "path": file_path,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = read_file(config)
    assert result["content"] == content


def test_write_json_file(tmp_path):
    """Test writing JSON file."""
    data = {"name": "Alice", "age": 25}
    file_path = tmp_path / "data.json"
    result = write_file_direct(str(file_path), json.dumps(data), tmp_path)
    assert result == str(file_path)
    assert json.loads(Path(file_path).read_text()) == data


def test_write_yaml_file(tmp_path):
    """Test writing YAML file."""
    data = {"name": "Bob", "age": 30}
    file_path = tmp_path / "data.yaml"
    result = write_file_direct(str(file_path), yaml.dump(data), tmp_path)
    assert result == str(file_path)
    assert yaml.safe_load(Path(file_path).read_text()) == data


def test_append_text_file(tmp_path):
    """Test appending to text file."""
    file_path = tmp_path / "test.txt"
    initial_content = "Hello"
    append_content = ", World!"
    Path(file_path).write_text(initial_content)
    result = append_file_direct(str(file_path), append_content, tmp_path)
    assert result == str(file_path)
    assert Path(file_path).read_text() == initial_content + append_content


def test_copy_file_direct(temp_workspace):
    """Test copying file using direct function."""
    source_path = temp_workspace / "source.txt"
    dest_path = temp_workspace / "dest.txt"
    content = "Test content"
    source_path.write_text(content)
    result = copy_file_direct(str(source_path), str(dest_path), temp_workspace)
    assert result == str(dest_path)
    assert Path(dest_path).read_text() == content


def test_copy_file_task(temp_workspace):
    """Test copying file using task handler."""
    source = "source.txt"
    dest = "dest.txt"
    content = "Test content"
    (temp_workspace / source).write_text(content)
    step = {
        "name": "copy_test",
        "task": "copy_file",
        "inputs": {
            "source": source,
            "destination": dest,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = copy_file(config)
    assert result["source"] == str(temp_workspace / source)
    assert result["destination"] == str(temp_workspace / dest)
    assert Path(temp_workspace / dest).read_text() == content


def test_move_file_direct(temp_workspace):
    """Test moving file using direct function."""
    source_path = temp_workspace / "source.txt"
    dest_path = temp_workspace / "dest.txt"
    content = "Test content"
    source_path.write_text(content)
    result = move_file_direct(str(source_path), str(dest_path), temp_workspace)
    assert result == str(dest_path)
    assert Path(dest_path).read_text() == content
    assert not source_path.exists()


def test_move_file_task(temp_workspace):
    """Test moving file using task handler."""
    source = "source.txt"
    dest = "dest.txt"
    content = "Test content"
    (temp_workspace / source).write_text(content)
    step = {
        "name": "move_test",
        "task": "move_file",
        "inputs": {
            "source": source,
            "destination": dest,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = move_file(config)
    assert result["source"] == str(temp_workspace / source)
    assert result["destination"] == str(temp_workspace / dest)
    assert Path(temp_workspace / dest).read_text() == content
    assert not (temp_workspace / source).exists()


def test_delete_file_direct(temp_workspace):
    """Test deleting file using direct function."""
    file_path = temp_workspace / "test.txt"
    content = "Test content"
    file_path.write_text(content)
    result = delete_file_direct(str(file_path), temp_workspace)
    assert result == str(file_path)
    assert not file_path.exists()


def test_delete_file_task(temp_workspace):
    """Test deleting file using task handler."""
    file_path = "test_to_delete.txt"
    (temp_workspace / file_path).write_text("delete me")
    assert (temp_workspace / file_path).exists()

    step = {
        "name": "delete_test",
        "task": "delete_file",
        "inputs": {
            "path": file_path,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = delete_file(config)
    assert result["path"] == str(temp_workspace / file_path)
    assert not (temp_workspace / file_path).exists()


def test_write_csv_file(tmp_path):
    """Test writing CSV file."""
    data = [
        ["Name", "Age", "City"],
        ["Alice", "25", "New York"],
        ["Bob", "30", "London"],
    ]
    file_path = os.path.join(tmp_path, "data.csv")
    csv_content = "\n".join([",".join(row) for row in data])
    result = write_file_direct(file_path, csv_content, tmp_path)
    assert result == file_path
    assert Path(file_path).read_text() == csv_content


def test_file_error_handling(temp_workspace):
    """Test error handling for file operations."""
    # Test non-existent file
    non_existent = "non_existent.txt"
    step = {
        "name": "read_non_existent",
        "task": "read_file",
        "inputs": {
            "path": non_existent,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(FileNotFoundError):
        read_file(config)

    # Test invalid JSON
    invalid_json = temp_workspace / "invalid.json"
    invalid_json.write_text("{invalid")
    with pytest.raises(TaskExecutionError) as exc_info:
        read_json(str(invalid_json), temp_workspace)
    assert "Expecting property name" in str(exc_info.value)

    # Test invalid YAML
    invalid_yaml = temp_workspace / "invalid.yaml"
    invalid_yaml.write_text("invalid: [yaml")
    with pytest.raises(TaskExecutionError) as exc_info:
        read_yaml(str(invalid_yaml), temp_workspace)
    assert "expected" in str(exc_info.value)


def test_file_operations_with_directories(temp_workspace):
    """Test file operations with nested directories."""
    nested_path = "nested/dir/test.txt"
    content = "Test content"
    step = {
        "name": "write_nested",
        "task": "write_file",
        "inputs": {
            "path": nested_path,
            "content": content,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_file(config)
    assert result["path"] == str(temp_workspace / nested_path)
    assert Path(temp_workspace / nested_path).read_text() == content


def test_file_operations_with_empty_files(temp_workspace):
    """Test file operations with empty files."""
    file_path = "empty.txt"
    step = {
        "name": "write_empty",
        "task": "write_file",
        "inputs": {
            "path": file_path,
            "content": "",
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_file(config)
    assert result["path"] == str(temp_workspace / file_path)
    assert Path(temp_workspace / file_path).read_text() == ""


def test_file_operations_with_special_characters(temp_workspace):
    """Test file operations with special characters in content."""
    file_path = "special.txt"
    content = "Line 1\nLine 2\tTabbed\nWindows line ending"
    step = {
        "name": "write_special",
        "task": "write_file",
        "inputs": {
            "path": file_path,
            "content": content,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_file(config)
    assert result["path"] == str(temp_workspace / file_path)
    actual_content = Path(temp_workspace / file_path).read_text().replace("\r\n", "\n")
    assert actual_content == content
