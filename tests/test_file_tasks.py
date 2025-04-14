import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from yaml_workflow.tasks import register_task
from yaml_workflow.tasks.base import (
    get_task_logger,
    log_task_error,
    log_task_execution,
    log_task_result,
)
from yaml_workflow.tasks.file_tasks import (
    append_file_direct,
    copy_file_direct,
    delete_file_direct,
    move_file_direct,
    read_file_direct,
    read_json,
    read_yaml,
    write_file_direct,
    write_json,
    write_yaml,
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
def write_file(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """Write content to a file."""
    logger = get_task_logger(workspace, step.get("name", "write_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        path = workspace / step["params"]["file_path"]
        content = step["params"]["content"]
        mode = step.get("mode", "w")

        os.makedirs(path.parent, exist_ok=True)
        with open(path, mode) as f:
            f.write(content)

        result = {"path": str(path)}
        log_task_result(logger, result)
        return result
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("read_file")
def read_file(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """Read content from a file."""
    logger = get_task_logger(workspace, step.get("name", "read_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        path = workspace / step["params"]["file_path"]
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with open(path) as f:
            content = f.read()

        result = {"content": content}
        log_task_result(logger, result)
        return result
    except Exception as e:
        log_task_error(logger, e)
        raise


@register_task("copy_file")
def copy_file(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """Copy a file from source to destination."""
    logger = get_task_logger(workspace, step.get("name", "copy_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        src = workspace / step["source"]
        dst = workspace / step["destination"]

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
def move_file(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """Move a file from source to destination."""
    logger = get_task_logger(workspace, step.get("name", "move_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        src = workspace / step["source"]
        dst = workspace / step["destination"]

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
def delete_file(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """Delete a file."""
    logger = get_task_logger(workspace, step.get("name", "delete_file"))
    log_task_execution(logger, step, context, workspace)

    try:
        path = workspace / step["path"]
        if path.exists():
            os.remove(path)

        result = {"path": str(path)}
        log_task_result(logger, result)
        return result
    except Exception as e:
        log_task_error(logger, e)
        raise


def test_write_text_file(tmp_path):
    """Test writing text file."""
    file_path = tmp_path / "test.txt"
    content = "Hello, World!"
    result = write_file_direct(str(file_path), content, tmp_path)
    assert result == str(file_path)
    assert Path(file_path).read_text() == content


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


def test_read_text_file(tmp_path):
    """Test reading text file."""
    file_path = tmp_path / "test.txt"
    content = "Hello, World!"
    Path(file_path).write_text(content)
    result = read_file_direct(str(file_path), tmp_path)
    assert result == content


def test_read_json_file(tmp_path):
    """Test reading JSON file."""
    data = {"name": "Alice", "age": 25}
    file_path = tmp_path / "data.json"
    Path(file_path).write_text(json.dumps(data))
    result = read_file_direct(str(file_path), tmp_path)
    assert json.loads(result) == data


def test_read_yaml_file(tmp_path):
    """Test reading YAML file."""
    data = {"name": "Bob", "age": 30}
    file_path = tmp_path / "data.yaml"
    Path(file_path).write_text(yaml.dump(data))
    result = read_file_direct(str(file_path), tmp_path)
    assert yaml.safe_load(result) == data


def test_append_text_file(tmp_path):
    """Test appending to text file."""
    file_path = tmp_path / "test.txt"
    initial_content = "Hello"
    append_content = ", World!"
    Path(file_path).write_text(initial_content)
    result = append_file_direct(str(file_path), append_content, tmp_path)
    assert result == str(file_path)
    assert Path(file_path).read_text() == initial_content + append_content


def test_copy_file(tmp_path):
    """Test copying file."""
    source_path = tmp_path / "source.txt"
    dest_path = tmp_path / "dest.txt"
    content = "Test content"
    Path(source_path).write_text(content)
    result = copy_file_direct(str(source_path), str(dest_path), tmp_path)
    assert result == str(dest_path)
    assert Path(dest_path).read_text() == content


def test_move_file(tmp_path):
    """Test moving file."""
    source_path = tmp_path / "source.txt"
    dest_path = tmp_path / "dest.txt"
    content = "Test content"
    Path(source_path).write_text(content)
    result = move_file_direct(str(source_path), str(dest_path), tmp_path)
    assert result == str(dest_path)
    assert Path(dest_path).read_text() == content
    assert not source_path.exists()


def test_delete_file(tmp_path):
    """Test deleting file."""
    file_path = tmp_path / "test.txt"
    content = "Test content"
    Path(file_path).write_text(content)
    result = delete_file_direct(str(file_path), tmp_path)
    assert result == str(file_path)
    assert not file_path.exists()


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


def test_file_error_handling(tmp_path):
    """Test error handling for file operations."""
    non_existent = tmp_path / "non_existent.txt"
    with pytest.raises(FileNotFoundError):
        read_file_direct(str(non_existent), tmp_path)


def test_file_operations_with_directories(tmp_path):
    """Test file operations with nested directories."""
    nested_path = tmp_path / "nested" / "dir" / "test.txt"
    content = "Test content"
    result = write_file_direct(str(nested_path), content, tmp_path)
    assert result == str(nested_path)
    assert Path(nested_path).read_text() == content


def test_file_operations_with_empty_files(tmp_path):
    """Test file operations with empty files."""
    file_path = tmp_path / "empty.txt"
    result = write_file_direct(str(file_path), "", tmp_path)
    assert result == str(file_path)
    assert Path(file_path).read_text() == ""


def test_file_operations_with_special_characters(tmp_path):
    """Test file operations with special characters in content."""
    file_path = tmp_path / "special.txt"
    content = "Line 1\nLine 2\tTabbed\r\nWindows line ending"
    result = write_file_direct(str(file_path), content, tmp_path)
    assert result == str(file_path)
    assert read_file_direct(str(file_path), tmp_path) == content
