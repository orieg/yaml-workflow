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
    copy_file_task,
    delete_file_direct,
    delete_file_task,
    move_file_direct,
    move_file_task,
    read_file_direct,
    read_file_task,
    read_json,
    read_json_task,
    read_yaml,
    read_yaml_task,
    write_file_direct,
    write_file_task,
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
            "file": file_path,
            "content": content,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_file_task(config)
    assert result is not None, "Task should return a result dictionary"
    expected_path = str(temp_workspace / "output" / file_path)
    assert result["path"] == expected_path
    assert result["content"] == content
    assert Path(expected_path).read_text() == content


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
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / file_path
    full_path.write_text(content)
    step = {
        "name": "read_test",
        "task": "read_file",
        "inputs": {
            "file": file_path,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = read_file_task(config)
    assert result is not None, "Task should return a result dictionary"
    assert result["path"] == file_path
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
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / source).write_text(content)
    step = {
        "name": "copy_test",
        "task": "copy_file",
        "inputs": {
            "source": source,
            "destination": dest,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = copy_file_task(config)
    assert result is not None
    assert result["source"] == source
    expected_dest_path = str(temp_workspace / "output" / dest)
    assert result["destination"] == expected_dest_path
    assert Path(expected_dest_path).read_text() == content


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
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    source_path_abs = output_dir / source
    source_path_abs.write_text(content)
    step = {
        "name": "move_test",
        "task": "move_file",
        "inputs": {
            "source": source,
            "destination": dest,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = move_file_task(config)
    assert result is not None
    assert result["source"] == source
    expected_dest_path = str(temp_workspace / "output" / dest)
    assert result["destination"] == expected_dest_path
    assert Path(expected_dest_path).read_text() == content
    assert not source_path_abs.exists()


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
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / file_path
    full_path.write_text("delete me")
    assert full_path.exists()

    step = {
        "name": "delete_test",
        "task": "delete_file",
        "inputs": {
            "file": file_path,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = delete_file_task(config)
    assert result is not None, "Task should return a result dictionary"
    expected_path = str(temp_workspace / "output" / file_path)
    assert result["path"] == expected_path
    assert not full_path.exists()


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


def test_file_tasks_missing_inputs(temp_workspace):
    """Test file tasks fail when required inputs are missing."""
    # Test write_file_task missing 'file'
    step_write_no_file = {
        "name": "w1",
        "task": "write_file",
        "inputs": {"content": "c"},
    }
    config_w1 = TaskConfig(step_write_no_file, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_w1:
        write_file_task(config_w1)
    assert "No file path provided" in str(excinfo_w1.value.original_error)

    # Test write_file_task missing 'content'
    step_write_no_content = {
        "name": "w2",
        "task": "write_file",
        "inputs": {"file": "f.txt"},
    }
    config_w2 = TaskConfig(step_write_no_content, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_w2:
        write_file_task(config_w2)
    assert "No content provided" in str(excinfo_w2.value.original_error)

    # Test read_file_task missing 'file'
    step_read_no_file = {"name": "r1", "task": "read_file", "inputs": {}}
    config_r1 = TaskConfig(step_read_no_file, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_r1:
        read_file_task(config_r1)
    assert "No file path provided" in str(excinfo_r1.value.original_error)

    # Test copy_file_task missing 'source'
    step_copy_no_source = {
        "name": "c1",
        "task": "copy_file",
        "inputs": {"destination": "d"},
    }
    config_c1 = TaskConfig(step_copy_no_source, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_c1:
        copy_file_task(config_c1)
    assert "No source file provided" in str(excinfo_c1.value.original_error)

    # Test copy_file_task missing 'destination'
    step_copy_no_dest = {"name": "c2", "task": "copy_file", "inputs": {"source": "s"}}
    config_c2 = TaskConfig(step_copy_no_dest, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_c2:
        copy_file_task(config_c2)
    assert "No destination file provided" in str(excinfo_c2.value.original_error)

    # Test move_file_task missing 'source'
    step_move_no_source = {
        "name": "m1",
        "task": "move_file",
        "inputs": {"destination": "d"},
    }
    config_m1 = TaskConfig(step_move_no_source, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_m1:
        move_file_task(config_m1)
    assert "No source file provided" in str(excinfo_m1.value.original_error)

    # Test move_file_task missing 'destination'
    step_move_no_dest = {"name": "m2", "task": "move_file", "inputs": {"source": "s"}}
    config_m2 = TaskConfig(step_move_no_dest, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_m2:
        move_file_task(config_m2)
    assert "No destination file provided" in str(excinfo_m2.value.original_error)

    # Test append_file_task missing 'file'
    step_append_no_file = {
        "name": "a1",
        "task": "append_file",
        "inputs": {"content": "c"},
    }
    config_a1 = TaskConfig(step_append_no_file, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_a1:
        append_file_task(config_a1)
    assert "No file path provided" in str(excinfo_a1.value.original_error)

    # Test append_file_task missing 'content'
    step_append_no_content = {
        "name": "a2",
        "task": "append_file",
        "inputs": {"file": "f.txt"},
    }
    config_a2 = TaskConfig(step_append_no_content, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_a2:
        append_file_task(config_a2)
    assert "No content provided" in str(excinfo_a2.value.original_error)

    # Test delete_file_task missing 'file'
    step_delete_no_file = {"name": "d1", "task": "delete_file", "inputs": {}}
    config_d1 = TaskConfig(step_delete_no_file, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_d1:
        delete_file_task(config_d1)
    assert "No file path provided" in str(excinfo_d1.value.original_error)


def test_file_tasks_file_not_found(temp_workspace):
    """Test file tasks handle file not found errors."""
    non_existent_file = "non_existent_file.txt"
    existing_file = "existing.txt"
    (temp_workspace / existing_file).write_text("exists")

    # Test read_file_task
    step_read = {
        "name": "r_nf",
        "task": "read_file",
        "inputs": {"file": non_existent_file},
    }
    config_read = TaskConfig(step_read, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_read:
        read_file_task(config_read)
    assert isinstance(excinfo_read.value.original_error, FileNotFoundError)

    # Test copy_file_task (source not found)
    step_copy = {
        "name": "c_nf",
        "task": "copy_file",
        "inputs": {"source": non_existent_file, "destination": "d.txt"},
    }
    config_copy = TaskConfig(step_copy, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_copy:
        copy_file_task(config_copy)
    assert isinstance(excinfo_copy.value.original_error, FileNotFoundError)

    # Test move_file_task (source not found)
    step_move = {
        "name": "m_nf",
        "task": "move_file",
        "inputs": {"source": non_existent_file, "destination": "d.txt"},
    }
    config_move = TaskConfig(step_move, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as excinfo_move:
        move_file_task(config_move)
    assert isinstance(excinfo_move.value.original_error, FileNotFoundError)

    # Test delete_file_task (file not found is okay, should not raise error)
    step_del = {
        "name": "d_nf",
        "task": "delete_file",
        "inputs": {"file": non_existent_file},
    }
    config_del = TaskConfig(step_del, {}, temp_workspace)
    try:
        result_del = delete_file_task(config_del)
        assert result_del is not None
        assert result_del["path"] == str(temp_workspace / "output" / non_existent_file)
    except TaskExecutionError:
        pytest.fail("delete_file_task should not raise error for non-existent file")


def test_file_error_handling(temp_workspace):
    """Placeholder for more specific error tests (permissions, etc.)."""
    pass  # Keep existing structure, add more specific tests later if needed


def test_append_file_task(temp_workspace):
    """Test appending to a file using task handler."""
    existing_file = "append_existing.txt"
    non_existing_file = "append_new.txt"
    initial_content = "Line1\n"
    append_content = "Line2"

    # Setup existing file inside output/
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    existing_file_abs = output_dir / existing_file
    existing_file_abs.write_text(initial_content)

    # Test appending to existing file
    step_append_existing = {
        "name": "append_exist",
        "task": "append_file",
        "inputs": {"file": existing_file, "content": append_content},
    }
    config_ae = TaskConfig(step_append_existing, {}, temp_workspace)
    result_ae = append_file_task(config_ae)
    assert result_ae["path"] == str(existing_file_abs)
    assert existing_file_abs.read_text() == initial_content + append_content

    # Test appending to non-existing file (should create it in output/)
    step_append_new = {
        "name": "append_new",
        "task": "append_file",
        "inputs": {"file": non_existing_file, "content": append_content},
    }
    config_an = TaskConfig(step_append_new, {}, temp_workspace)
    result_an = append_file_task(config_an)
    expected_new_path = temp_workspace / "output" / non_existing_file
    assert result_an["path"] == str(expected_new_path)
    assert expected_new_path.read_text() == append_content


def test_json_tasks(temp_workspace, sample_data):
    """Test read_json_task and write_json_task."""
    json_file = "data.json"
    invalid_json_file = "invalid.json"
    non_existent_file = "no.json"

    # Test write_json_task
    step_write = {
        "name": "write_json",
        "task": "write_json",
        "inputs": {"file": json_file, "data": sample_data, "indent": 4},
    }
    config_w = TaskConfig(step_write, {}, temp_workspace)
    result_w = write_json_task(config_w)
    assert result_w is not None
    assert result_w["path"] == str(temp_workspace / "output" / json_file)
    # Verify file content
    written_data = json.loads((temp_workspace / "output" / json_file).read_text())
    assert written_data == sample_data

    # Setup read test file inside output/
    read_test_path = temp_workspace / "output" / json_file
    read_test_path.parent.mkdir(exist_ok=True)
    read_test_path.write_text(json.dumps(sample_data))

    # Test read_json_task (valid file)
    step_read = {
        "name": "read_json",
        "task": "read_json",
        "inputs": {"file": json_file},
    }
    config_r = TaskConfig(step_read, {}, temp_workspace)
    result_r = read_json_task(config_r)
    assert result_r["data"] == sample_data

    # Test read_json_task (file not found)
    step_read_nf = {
        "name": "read_json_nf",
        "task": "read_json",
        "inputs": {"file": non_existent_file},
    }
    config_r_nf = TaskConfig(step_read_nf, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc_nf:
        read_json_task(config_r_nf)
    assert isinstance(exc_nf.value.original_error, FileNotFoundError)

    # Test read_json_task (invalid JSON)
    (temp_workspace / invalid_json_file).write_text(
        "{"
    )  # Write invalid JSON outside output/
    step_read_inv = {
        "name": "read_json_inv",
        "task": "read_json",
        "inputs": {"file": invalid_json_file},
    }
    config_r_inv = TaskConfig(step_read_inv, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc_inv:
        read_json_task(config_r_inv)  # Task resolves path to output/invalid.json
    # Expect FileNotFoundError because the file doesn't exist at the resolved path
    assert isinstance(exc_inv.value.original_error, FileNotFoundError)


def test_yaml_tasks(temp_workspace, sample_data):
    """Test read_yaml_task and write_yaml_task."""
    yaml_file = "data.yaml"
    invalid_yaml_file = "invalid.yaml"
    non_existent_file = "no.yaml"

    # Test write_yaml_task
    step_write = {
        "name": "write_yaml",
        "task": "write_yaml",
        "inputs": {"file": yaml_file, "data": sample_data},
    }
    config_w = TaskConfig(step_write, {}, temp_workspace)
    result_w = write_yaml_task(config_w)
    assert result_w is not None
    assert result_w["path"] == str(temp_workspace / "output" / yaml_file)
    # Verify file content
    written_data = yaml.safe_load((temp_workspace / "output" / yaml_file).read_text())
    assert written_data == sample_data

    # Setup read test file inside output/
    read_test_path = temp_workspace / "output" / yaml_file
    read_test_path.parent.mkdir(exist_ok=True)
    read_test_path.write_text(yaml.dump(sample_data))

    # Test read_yaml_task (valid file)
    step_read = {
        "name": "read_yaml",
        "task": "read_yaml",
        "inputs": {"file": yaml_file},
    }
    config_r = TaskConfig(step_read, {}, temp_workspace)
    result_r = read_yaml_task(config_r)
    assert result_r["data"] == sample_data

    # Test read_yaml_task (file not found)
    step_read_nf = {
        "name": "read_yaml_nf",
        "task": "read_yaml",
        "inputs": {"file": non_existent_file},
    }
    config_r_nf = TaskConfig(step_read_nf, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc_nf:
        read_yaml_task(config_r_nf)
    assert isinstance(exc_nf.value.original_error, FileNotFoundError)

    # Test read_yaml_task (invalid YAML)
    (temp_workspace / invalid_yaml_file).write_text(
        "key: [nested: value"
    )  # Write invalid YAML outside output/
    step_read_inv = {
        "name": "read_yaml_inv",
        "task": "read_yaml",
        "inputs": {"file": invalid_yaml_file},
    }
    config_r_inv = TaskConfig(step_read_inv, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc_inv:
        read_yaml_task(config_r_inv)  # Task resolves path to output/invalid.yaml
    # Expect FileNotFoundError because the file doesn't exist at the resolved path
    assert isinstance(exc_inv.value.original_error, FileNotFoundError)


def test_file_tasks_with_templating(temp_workspace):
    """Test file tasks with templated inputs."""
    context = {
        "args": {
            "output_dir": "templated_output",
            "filename": "templated_file.txt",
            "message": "Templated content for file.",
            "source_file": "source_template.txt",
        }
    }
    # Setup source file inside output/
    source_content = "This is the source file content."
    output_dir_tmpl = temp_workspace / "output"
    output_dir_tmpl.mkdir(parents=True, exist_ok=True)
    (output_dir_tmpl / context["args"]["source_file"]).write_text(source_content)

    # Test write_file_task with templated path and content
    step_write = {
        "name": "write_templated",
        "task": "write_file",
        "inputs": {
            "file": "{{ args.output_dir }}/{{ args.filename }}",
            "content": "{{ args.message }}",
        },
    }
    config_w = TaskConfig(step_write, context, temp_workspace)
    result_w = write_file_task(config_w)
    expected_path = (
        temp_workspace
        / "output"
        / context["args"]["output_dir"]
        / context["args"]["filename"]
    )
    assert result_w["path"] == str(expected_path)
    assert expected_path.read_text() == context["args"]["message"]

    # Test copy_file_task with templated source and destination
    step_copy = {
        "name": "copy_templated",
        "task": "copy_file",
        "inputs": {
            "source": "{{ args.source_file }}",
            "destination": "{{ args.output_dir }}/copy_{{ args.filename }}",
        },
    }
    config_c = TaskConfig(step_copy, context, temp_workspace)
    result_c = copy_file_task(config_c)
    expected_dest_path = (
        temp_workspace
        / "output"
        / context["args"]["output_dir"]
        / f"copy_{context['args']['filename']}"
    )
    assert result_c["destination"] == str(expected_dest_path)
    assert expected_dest_path.read_text() == source_content


def test_file_tasks_with_absolute_paths(temp_workspace):
    """Test file tasks using absolute paths."""
    # Create absolute paths *within* the temp workspace for safety
    abs_source_path = (temp_workspace / "absolute_source.txt").resolve()
    abs_dest_path = (temp_workspace / "sub" / "absolute_dest.txt").resolve()
    abs_read_path = (temp_workspace / "absolute_read.txt").resolve()

    content_write = "Absolute write test."
    content_read = "Absolute read test."

    # Write the file needed for reading
    abs_read_path.write_text(content_read)

    # Test write_file_task with absolute path
    step_write = {
        "name": "write_abs",
        "task": "write_file",
        "inputs": {"file": str(abs_source_path), "content": content_write},
    }
    config_w = TaskConfig(step_write, {}, temp_workspace)
    result_w = write_file_task(config_w)
    assert result_w["path"] == str(abs_source_path)
    assert abs_source_path.read_text() == content_write

    # Test read_file_task with absolute path
    step_read = {
        "name": "read_abs",
        "task": "read_file",
        "inputs": {"file": str(abs_read_path)},
    }
    config_r = TaskConfig(step_read, {}, temp_workspace)
    result_r = read_file_task(config_r)
    assert result_r["content"] == content_read

    # Test copy_file_task with absolute paths
    step_copy = {
        "name": "copy_abs",
        "task": "copy_file",
        "inputs": {"source": str(abs_source_path), "destination": str(abs_dest_path)},
    }
    config_c = TaskConfig(step_copy, {}, temp_workspace)
    result_c = copy_file_task(config_c)
    assert result_c["source"] == str(abs_source_path)
    assert result_c["destination"] == str(abs_dest_path)
    assert abs_dest_path.read_text() == content_write
