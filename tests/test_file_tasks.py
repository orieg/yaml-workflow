import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, cast

import pytest
import yaml

from yaml_workflow.exceptions import TaskExecutionError, TemplateError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.file_tasks import (
    append_file_direct,
    append_file_task,
    copy_file_direct,
    copy_file_task,
    delete_file_direct,
    delete_file_task,
    ensure_directory,
    move_file_direct,
    move_file_task,
    process_templates,
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
    file_path = "output/test.txt"
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
    expected_path = str(temp_workspace / file_path)
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
    file_path_relative = "test.txt"
    file_path_in_output = "output/test.txt"
    content = "Hello, World!"
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / file_path_relative
    full_path.write_text(content)
    step = {
        "name": "read_test",
        "task": "read_file",
        "inputs": {
            "file": file_path_in_output,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = read_file_task(config)
    assert result is not None, "Task should return a result dictionary"
    assert result["path"] == file_path_in_output
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
    source_relative = "source.txt"
    dest_relative = "dest.txt"
    source_in_output = "output/source.txt"
    dest_in_output = "output/dest.txt"
    content = "Test content"
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / source_relative).write_text(content)
    step = {
        "name": "copy_test",
        "task": "copy_file",
        "inputs": {
            "source": source_in_output,
            "destination": dest_in_output,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = copy_file_task(config)
    assert result is not None
    expected_src_path = str(temp_workspace / source_in_output)
    expected_dest_path = str(temp_workspace / dest_in_output)
    assert result["source"] == source_in_output
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
    source_relative = "source.txt"
    dest_relative = "dest.txt"
    source_in_output = "output/source.txt"
    dest_in_output = "output/dest.txt"
    content = "Test content"
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    source_path_abs = output_dir / source_relative
    source_path_abs.write_text(content)
    step = {
        "name": "move_test",
        "task": "move_file",
        "inputs": {
            "source": source_in_output,
            "destination": dest_in_output,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = move_file_task(config)
    assert result is not None
    expected_src_path = str(temp_workspace / source_in_output)
    expected_dest_path = str(temp_workspace / dest_in_output)
    assert result["source"] == source_in_output
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
    file_path_relative = "test_to_delete.txt"
    file_path_in_output = "output/test_to_delete.txt"
    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / file_path_relative
    full_path.write_text("delete me")
    assert full_path.exists()

    step = {
        "name": "delete_test",
        "task": "delete_file",
        "inputs": {
            "file": file_path_in_output,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = delete_file_task(config)
    assert result is not None, "Task should return a result dictionary"
    expected_path = str(full_path)
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
        "inputs": {"file": f"output/{non_existent_file}"},
    }
    config_del = TaskConfig(step_del, {}, temp_workspace)
    try:
        result_del = delete_file_task(config_del)
        assert result_del is not None
        expected_del_path = str(temp_workspace / "output" / non_existent_file)
        assert result_del["path"] == expected_del_path
    except TaskExecutionError as e:
        pytest.fail(f"delete_file_task raised an unexpected error: {e}")


def test_file_error_handling(temp_workspace):
    """Placeholder for more specific error tests (permissions, etc.)."""
    pass  # Keep existing structure, add more specific tests later if needed


def test_append_file_task(temp_workspace):
    """Test appending to a file using task handler."""
    file_path_relative = "test.txt"
    file_path_in_output = "output/test.txt"
    initial_content = "Hello"
    append_content = ", World!"

    output_dir = temp_workspace / "output"
    output_dir.mkdir(exist_ok=True)
    full_path = output_dir / file_path_relative
    full_path.write_text(initial_content)

    step = {
        "name": "append_test",
        "task": "append_file",
        "inputs": {
            "file": file_path_in_output,
            "content": append_content,
        },
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = append_file_task(config)
    assert result is not None
    expected_path = str(full_path)
    assert result["path"] == expected_path
    assert result["content"] == append_content
    assert full_path.read_text() == initial_content + append_content


def test_json_tasks(temp_workspace, sample_data):
    """Test read_json_task and write_json_task."""
    file_path_relative = "data.json"
    file_path_in_output = "output/data.json"
    full_path = temp_workspace / file_path_in_output

    # Test write_json_task
    step_write = {
        "name": "write_json_test",
        "task": "write_json",
        "inputs": {"file": file_path_in_output, "data": sample_data},
    }
    config_w = TaskConfig(step_write, {}, temp_workspace)
    result_w = write_json_task(config_w)
    assert result_w is not None
    assert result_w["path"] == str(full_path)
    assert full_path.exists()
    with open(full_path, "r") as f:
        assert json.load(f) == sample_data

    # Test read_json_task
    step_read = {
        "name": "read_json_test",
        "task": "read_json",
        "inputs": {"file": file_path_in_output},
    }
    config_r = TaskConfig(step_read, {}, temp_workspace)
    result_r = read_json_task(config_r)
    assert result_r is not None
    assert result_r["data"] == sample_data

    # Test direct function calls
    direct_file_path = temp_workspace / "direct.json"
    write_json_direct(str(direct_file_path), sample_data, workspace=temp_workspace)
    assert direct_file_path.exists()
    read_data = read_json(str(direct_file_path), temp_workspace)
    assert read_data == sample_data


def test_yaml_tasks(temp_workspace, sample_data):
    """Test read_yaml_task and write_yaml_task."""
    file_path_relative = "data.yaml"
    file_path_in_output = "output/data.yaml"
    full_path = temp_workspace / file_path_in_output

    # Test write_yaml_task
    step_write = {
        "name": "write_yaml_test",
        "task": "write_yaml",
        "inputs": {"file": file_path_in_output, "data": sample_data},
    }
    config_w = TaskConfig(step_write, {}, temp_workspace)
    result_w = write_yaml_task(config_w)
    assert result_w is not None
    assert result_w["path"] == str(full_path)
    assert full_path.exists()
    with open(full_path, "r") as f:
        assert yaml.safe_load(f) == sample_data

    # Test read_yaml_task
    step_read = {
        "name": "read_yaml_test",
        "task": "read_yaml",
        "inputs": {"file": file_path_in_output},
    }
    config_r = TaskConfig(step_read, {}, temp_workspace)
    result_r = read_yaml_task(config_r)
    assert result_r is not None
    assert result_r["data"] == sample_data

    # Test direct function calls
    direct_file_path = temp_workspace / "direct.yaml"
    write_yaml_direct(str(direct_file_path), sample_data, temp_workspace)
    assert direct_file_path.exists()
    read_data = read_yaml(str(direct_file_path), temp_workspace)
    assert read_data == sample_data


def test_file_tasks_with_templating(temp_workspace):
    """Test file tasks with templated inputs."""
    context = {
        "args": {
            "output_dir": "templated_output",
            "filename": "templated_file.txt",
            "message": "Templated content for file.",
            "source_file": "source_template.txt",
            "dest_dir": "copied_files",
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
        temp_workspace / context["args"]["output_dir"] / context["args"]["filename"]
    )
    assert result_w["path"] == str(expected_path)
    assert result_w["content"] == context["args"]["message"]
    assert expected_path.exists()
    assert expected_path.read_text() == context["args"]["message"]

    # Test read_file_task with templated path
    step_read = {
        "name": "read_templated",
        "task": "read_file",
        "inputs": {"file": "{{ args.output_dir }}/{{ args.filename }}"},
    }
    config_r = TaskConfig(step_read, context, temp_workspace)
    result_r = read_file_task(config_r)
    expected_read_input_path = (
        f"{context['args']['output_dir']}/{context['args']['filename']}"
    )
    assert result_r["path"] == expected_read_input_path
    assert result_r["content"] == context["args"]["message"]

    # Test copy_file_task with templated source and destination
    step_copy = {
        "name": "copy_templated",
        "task": "copy_file",
        "inputs": {
            "source": "output/{{ args.source_file }}",
            "destination": "{{ args.dest_dir }}/copied_{{ args.filename }}",
        },
    }
    config_c = TaskConfig(step_copy, context, temp_workspace)
    result_c = copy_file_task(config_c)
    expected_copy_input_source = f"output/{context['args']['source_file']}"
    expected_dest_path = (
        temp_workspace
        / context["args"]["dest_dir"]
        / f"copied_{context['args']['filename']}"
    )
    assert result_c["source"] == expected_copy_input_source
    assert result_c["destination"] == str(expected_dest_path)
    assert expected_dest_path.exists()
    assert expected_dest_path.read_text() == source_content


def test_file_tasks_with_absolute_paths(temp_workspace):
    """Test file tasks when absolute paths are provided in inputs."""
    absolute_dir = temp_workspace / "absolute_test_dir"
    absolute_dir.mkdir()
    absolute_file = absolute_dir / "absolute_file.txt"
    absolute_dest = absolute_dir / "absolute_dest.txt"
    content = "Absolute Content"

    # Write File Task
    step_write = {
        "name": "write_abs",
        "task": "write_file",
        "inputs": {"file": str(absolute_file), "content": content},
    }
    config = TaskConfig(step_write, {}, temp_workspace)
    result = write_file_task(config)
    assert result["path"] == str(absolute_file)
    assert absolute_file.read_text() == content

    # Read File Task
    step_read = {
        "name": "read_abs",
        "task": "read_file",
        "inputs": {"file": str(absolute_file)},
    }
    config = TaskConfig(step_read, {}, temp_workspace)
    result = read_file_task(config)
    assert result["path"] == str(absolute_file)
    assert result["content"] == content

    # Copy File Task
    copy_step = {
        "name": "copy_abs",
        "task": "copy_file",
        "inputs": {"source": str(absolute_file), "destination": str(absolute_dest)},
    }
    config = TaskConfig(copy_step, {}, temp_workspace)
    result = copy_file_task(config)
    assert result["source"] == str(absolute_file)
    assert result["destination"] == str(absolute_dest)
    assert absolute_dest.read_text() == content

    # Delete File Task (deleting the copy)
    delete_step = {
        "name": "delete_abs",
        "task": "delete_file",
        "inputs": {"file": str(absolute_dest)},
    }
    config = TaskConfig(delete_step, {}, temp_workspace)
    result = delete_file_task(config)
    assert result["path"] == str(absolute_dest)
    assert not absolute_dest.exists()

    # Check original still exists before move
    assert absolute_file.exists()

    # Move File Task
    move_dest = absolute_dir / "moved_absolute_file.txt"
    move_step = {
        "name": "move_abs",
        "task": "move_file",
        "inputs": {"source": str(absolute_file), "destination": str(move_dest)},
    }
    config = TaskConfig(move_step, {}, temp_workspace)
    result = move_file_task(config)
    assert result["source"] == str(absolute_file)
    assert result["destination"] == str(move_dest)
    assert not absolute_file.exists()  # Original should be gone
    assert move_dest.exists()
    assert move_dest.read_text() == content


# ─── ensure_directory error path (lines 34-35) ───


def test_ensure_directory_oserror(tmp_path):
    """Test ensure_directory raises TaskExecutionError on OSError."""
    # Use a path under a file (not a dir) so mkdir fails
    blocker = tmp_path / "blocker"
    blocker.write_text("I am a file")
    bad_path = blocker / "subdir" / "file.txt"
    with pytest.raises(TaskExecutionError):
        ensure_directory(bad_path, "test_step")


# ─── write_file_direct error path (lines 69-70) ───


def test_write_file_direct_encoding_error(tmp_path):
    """Test write_file_direct raises TaskExecutionError on UnicodeEncodeError."""
    file_path = tmp_path / "bad_encode.txt"
    # A string with a surrogate that cannot encode to ascii
    content = "Hello \ud800 World"
    with pytest.raises(TaskExecutionError):
        write_file_direct(str(file_path), content, tmp_path, encoding="ascii")


def test_write_file_direct_io_error(tmp_path):
    """Test write_file_direct raises TaskExecutionError on IOError."""
    # Try writing to a path that is actually a directory
    dir_path = tmp_path / "adir"
    dir_path.mkdir()
    with pytest.raises(TaskExecutionError):
        write_file_direct(str(dir_path), "content", tmp_path)


# ─── read_file_direct with logger debug paths (lines 111-125) ───


def test_read_file_direct_with_logger_file_not_found(tmp_path):
    """Test read_file_direct with a logger when the file does not exist."""
    import logging

    logger = logging.getLogger("test_read_direct_logger")
    with pytest.raises(TaskExecutionError):
        read_file_direct("nonexistent.txt", tmp_path, logger=logger)


def test_read_file_direct_with_logger_success(tmp_path):
    """Test read_file_direct with a logger on a successful read."""
    import logging

    logger = logging.getLogger("test_read_direct_logger_ok")
    file_path = tmp_path / "readable.txt"
    file_path.write_text("hello")
    result = read_file_direct(str(file_path), tmp_path, logger=logger)
    assert result == "hello"


def test_read_file_direct_decode_error(tmp_path):
    """Test read_file_direct raises TaskExecutionError on UnicodeDecodeError."""
    import logging

    logger = logging.getLogger("test_read_decode_err")
    file_path = tmp_path / "binary.bin"
    file_path.write_bytes(b"\x80\x81\x82\xff")
    with pytest.raises(TaskExecutionError):
        read_file_direct(str(file_path), tmp_path, encoding="ascii", logger=logger)


def test_read_file_direct_parent_exists_listing(tmp_path):
    """Test read_file_direct debug path listing parent dir contents when file missing."""
    import logging

    logger = logging.getLogger("test_read_parent_listing")
    # Create a file in the dir so there is something to list
    (tmp_path / "other.txt").write_text("x")
    with pytest.raises(TaskExecutionError):
        read_file_direct("missing_file.txt", tmp_path, logger=logger)


# ─── append_file_direct error path (lines 156-157) ───


def test_append_file_direct_io_error(tmp_path):
    """Test append_file_direct raises TaskExecutionError on IOError."""
    dir_path = tmp_path / "adir"
    dir_path.mkdir()
    with pytest.raises(TaskExecutionError):
        append_file_direct(str(dir_path), "content", tmp_path)


# ─── delete_file_direct error path (lines 235-236) ───


def test_delete_file_direct_io_error(tmp_path):
    """Test delete_file_direct raises TaskExecutionError on IOError."""
    # Deleting a directory with unlink should fail
    dir_path = tmp_path / "a_directory"
    dir_path.mkdir()
    # Put a file inside so it's not empty (unlink on dir fails)
    (dir_path / "child.txt").write_text("x")
    with pytest.raises((TaskExecutionError, IsADirectoryError, PermissionError)):
        delete_file_direct(str(dir_path), tmp_path)


# ─── read_json_task missing inputs and error paths (lines 498, 504-519) ───


def test_read_json_task_missing_file(temp_workspace):
    """Test read_json_task raises error when file param is missing."""
    step = {"name": "rj1", "task": "read_json", "inputs": {}}
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        read_json_task(config)
    assert "No file path provided" in str(exc.value.original_error)


def test_read_json_task_invalid_json(temp_workspace):
    """Test read_json_task raises error when file contains invalid JSON."""
    bad_json = temp_workspace / "bad.json"
    bad_json.write_text("not valid json {{{")
    step = {"name": "rj2", "task": "read_json", "inputs": {"file": "bad.json"}}
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError):
        read_json_task(config)


def test_read_json_task_file_not_found(temp_workspace):
    """Test read_json_task raises error when file does not exist."""
    step = {
        "name": "rj3",
        "task": "read_json",
        "inputs": {"file": "nonexistent.json"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError):
        read_json_task(config)


# ─── write_json_task missing inputs and error paths (lines 545-551, 554-562, 582-597) ───


def test_write_json_task_missing_file(temp_workspace):
    """Test write_json_task raises error when file param is missing."""
    step = {
        "name": "wj1",
        "task": "write_json",
        "inputs": {"data": {"key": "val"}},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        write_json_task(config)
    assert "No file path provided" in str(exc.value.original_error)


def test_write_json_task_missing_data(temp_workspace):
    """Test write_json_task raises error when data param is missing."""
    step = {
        "name": "wj2",
        "task": "write_json",
        "inputs": {"file": "output/out.json"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        write_json_task(config)
    assert "No data provided" in str(exc.value.original_error)


def test_write_json_task_output_dir_creation(temp_workspace):
    """Test write_json_task creates output/ directory when file path contains it."""
    step = {
        "name": "wj3",
        "task": "write_json",
        "inputs": {"file": "output/test.json", "data": {"hello": "world"}},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = write_json_task(config)
    assert result is not None
    assert (temp_workspace / "output").is_dir()
    output_file = Path(result["path"])
    assert output_file.exists()
    with open(output_file) as f:
        assert json.load(f) == {"hello": "world"}


# ─── read_yaml_task missing inputs and error paths (lines 614, 620-635) ───


def test_read_yaml_task_missing_file(temp_workspace):
    """Test read_yaml_task raises error when file param is missing."""
    step = {"name": "ry1", "task": "read_yaml", "inputs": {}}
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        read_yaml_task(config)
    assert "No file path provided" in str(exc.value.original_error)


def test_read_yaml_task_file_not_found(temp_workspace):
    """Test read_yaml_task raises error when file does not exist."""
    step = {
        "name": "ry2",
        "task": "read_yaml",
        "inputs": {"file": "nonexistent.yaml"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError):
        read_yaml_task(config)


def test_read_yaml_task_invalid_yaml(temp_workspace):
    """Test read_yaml_task raises error when file contains invalid YAML."""
    bad_yaml = temp_workspace / "bad.yaml"
    bad_yaml.write_text(":\n  :\n  - :\n    invalid: [")
    step = {"name": "ry3", "task": "read_yaml", "inputs": {"file": "bad.yaml"}}
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError):
        read_yaml_task(config)


# ─── write_yaml_task missing inputs and error paths (lines 652, 654, 666-681) ───


def test_write_yaml_task_missing_file(temp_workspace):
    """Test write_yaml_task raises error when file param is missing."""
    step = {
        "name": "wy1",
        "task": "write_yaml",
        "inputs": {"data": {"key": "val"}},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        write_yaml_task(config)
    assert "No file path provided" in str(exc.value.original_error)


def test_write_yaml_task_missing_data(temp_workspace):
    """Test write_yaml_task raises error when data param is missing."""
    step = {
        "name": "wy2",
        "task": "write_yaml",
        "inputs": {"file": "out.yaml"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        write_yaml_task(config)
    assert "No data provided" in str(exc.value.original_error)


# ─── process_templates (lines 697-715) ───


def test_process_templates_string():
    """Test process_templates resolves a simple string template."""
    context = {"args": {"name": "Alice"}}
    result = process_templates("Hello {{ args.name }}", context)
    assert result == "Hello Alice"


def test_process_templates_dict():
    """Test process_templates resolves templates in a dict."""
    context = {"args": {"x": "1", "y": "2"}}
    data = {"a": "{{ args.x }}", "b": "{{ args.y }}"}
    result = process_templates(data, context)
    assert result == {"a": "1", "b": "2"}


def test_process_templates_list():
    """Test process_templates resolves templates in a list."""
    context = {"args": {"v": "val"}}
    data = ["{{ args.v }}", "literal"]
    result = process_templates(data, context)
    assert result == ["val", "literal"]


def test_process_templates_non_string():
    """Test process_templates passes through non-string, non-container types."""
    result = process_templates(42, {})
    assert result == 42
    result2 = process_templates(True, {})
    assert result2 is True
    result3 = process_templates(None, {})
    assert result3 is None


def test_process_templates_undefined_variable():
    """Test process_templates raises TemplateError for undefined variables."""
    context = {"args": {"name": "Alice"}, "env": {}, "steps": {}}
    with pytest.raises(TemplateError, match="Failed to resolve variable"):
        process_templates("{{ args.missing_var }}", context)


def test_process_templates_undefined_no_args():
    """Test process_templates raises TemplateError when context keys are missing."""
    context = {}
    with pytest.raises(TemplateError, match="Failed to resolve variable"):
        process_templates("{{ args.missing }}", context)


# ─── read_json decode error (lines 737-738) ───


def test_read_json_invalid_content(tmp_path):
    """Test read_json raises TaskExecutionError on invalid JSON content."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("this is not json")
    with pytest.raises(TaskExecutionError):
        read_json(str(bad_file), tmp_path)


# ─── write_json_direct error path (lines 796-802) ───


def test_write_json_direct_type_error(tmp_path):
    """Test write_json_direct raises TemplateError on non-serializable data."""
    file_path = tmp_path / "bad.json"
    with pytest.raises(TemplateError, match="Failed to write JSON"):
        write_json_direct(str(file_path), {1, 2, 3}, workspace=tmp_path)


def test_write_json_direct_io_error(tmp_path):
    """Test write_json_direct raises TemplateError on IOError."""
    # Try to write to a directory path
    dir_path = tmp_path / "adir"
    dir_path.mkdir()
    with pytest.raises(TemplateError, match="Failed to write JSON"):
        write_json_direct(str(dir_path), {"a": 1}, workspace=tmp_path)


def test_write_json_direct_with_logger(tmp_path):
    """Test write_json_direct with a logger for debug output."""
    import logging

    logger = logging.getLogger("test_write_json_logger")
    file_path = tmp_path / "logged.json"
    result = write_json_direct(
        str(file_path), {"key": "value"}, workspace=tmp_path, logger=logger
    )
    assert Path(result).exists()
    with open(result) as f:
        assert json.load(f) == {"key": "value"}


def test_write_json_direct_error_with_logger(tmp_path):
    """Test write_json_direct error path with logger present."""
    import logging

    logger = logging.getLogger("test_write_json_err_logger")
    file_path = tmp_path / "bad.json"
    with pytest.raises(TemplateError, match="Failed to write JSON"):
        write_json_direct(str(file_path), {1, 2, 3}, workspace=tmp_path, logger=logger)


# ─── read_yaml parse error (lines 824-825) ───


def test_read_yaml_invalid_content(tmp_path):
    """Test read_yaml raises TaskExecutionError on invalid YAML content."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text(":\n  - : [invalid")
    with pytest.raises(TaskExecutionError):
        read_yaml(str(bad_file), tmp_path)


# ─── write_yaml_direct error path (lines 858-859) ───


def test_write_yaml_direct_io_error(tmp_path):
    """Test write_yaml_direct raises TemplateError on IOError."""
    dir_path = tmp_path / "adir"
    dir_path.mkdir()
    with pytest.raises(TemplateError, match="Failed to write YAML"):
        write_yaml_direct(str(dir_path), {"a": 1}, workspace=tmp_path)


# ─── copy/move/delete direct with missing source (error paths) ───


def test_copy_file_direct_missing_source(tmp_path):
    """Test copy_file_direct raises TaskExecutionError when source is missing."""
    with pytest.raises(TaskExecutionError):
        copy_file_direct(
            str(tmp_path / "no_such_file.txt"),
            str(tmp_path / "dest.txt"),
            tmp_path,
        )


def test_move_file_direct_missing_source(tmp_path):
    """Test move_file_direct raises TaskExecutionError when source is missing."""
    with pytest.raises(TaskExecutionError):
        move_file_direct(
            str(tmp_path / "no_such_file.txt"),
            str(tmp_path / "dest.txt"),
            tmp_path,
        )


# ─── delete_file_task missing file param (line 481) ───


def test_delete_file_task_missing_file_param(temp_workspace):
    """Test delete_file_task raises error when file param is missing."""
    step = {"name": "df1", "task": "delete_file", "inputs": {}}
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        delete_file_task(config)
    assert "No file path provided" in str(exc.value.original_error)


# ─── append_file_task error paths (line 385) ───


def test_append_file_task_missing_file(temp_workspace):
    """Test append_file_task raises error when file param is missing."""
    step = {
        "name": "af1",
        "task": "append_file",
        "inputs": {"content": "c"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        append_file_task(config)
    assert "No file path provided" in str(exc.value.original_error)


def test_append_file_task_missing_content(temp_workspace):
    """Test append_file_task raises error when content param is missing."""
    step = {
        "name": "af2",
        "task": "append_file",
        "inputs": {"file": "f.txt"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(TaskExecutionError) as exc:
        append_file_task(config)
    assert "No content provided" in str(exc.value.original_error)


# ─── write_json_direct without workspace (line 772->783 branch) ───


def test_write_json_direct_no_workspace(tmp_path):
    """Test write_json_direct when workspace is None."""
    file_path = str(tmp_path / "no_ws.json")
    result = write_json_direct(file_path, {"test": True}, workspace=None)
    assert result == file_path
    with open(file_path) as f:
        assert json.load(f) == {"test": True}


def test_write_yaml_direct_no_workspace(tmp_path):
    """Test write_yaml_direct when workspace is None."""
    file_path = str(tmp_path / "no_ws.yaml")
    result = write_yaml_direct(file_path, {"test": True}, workspace=None)
    assert result == file_path
    with open(file_path) as f:
        assert yaml.safe_load(f) == {"test": True}


# ─── read_file_direct without logger (error path, line 120->125) ───


def test_read_file_direct_error_without_logger(tmp_path):
    """Test read_file_direct error path without logger."""
    with pytest.raises(TaskExecutionError):
        read_file_direct("nonexistent.txt", tmp_path, logger=None)


# ─── append_file_direct creates directory (new file) ───


def test_append_file_direct_creates_new_file(tmp_path):
    """Test append_file_direct creates file and parent dirs if they don't exist."""
    file_path = tmp_path / "subdir" / "new_append.txt"
    result = append_file_direct(str(file_path), "new content", tmp_path)
    assert result == str(file_path)
    assert file_path.read_text() == "new content"


# ─── delete_file_direct on non-existent file ───


def test_delete_file_direct_nonexistent(tmp_path):
    """Test delete_file_direct succeeds silently when file does not exist."""
    file_path = tmp_path / "does_not_exist.txt"
    result = delete_file_direct(str(file_path), tmp_path)
    assert result == str(file_path)
