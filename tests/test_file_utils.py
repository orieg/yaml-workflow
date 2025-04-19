# tests/test_file_utils.py

import os
from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import WorkflowError


@pytest.fixture
def setup_test_files(tmp_path):
    """Create a directory structure with test files."""
    base = tmp_path / "file_utils_test"
    base.mkdir()
    sub = base / "subdir"
    sub.mkdir()

    (base / "file1.txt").write_text("content1")
    (base / "file2.log").write_text("content2")
    (sub / "sub_file1.txt").write_text("content3")
    (sub / "sub_file2.yaml").write_text("key: value")
    # Add a directory inside subdir to test that list_files excludes dirs
    (sub / "nested_dir").mkdir()
    (sub / "nested_dir" / "ignore_me.txt").write_text("nested")

    return base


def run_list_files_task(tmp_path, inputs):
    """Helper function to run the list_files task via WorkflowEngine."""
    workflow = {
        "steps": [
            {
                "name": "list_step",
                "task": "file_utils",  # Uses the default name from @register_task
                "inputs": inputs,
            }
        ]
    }
    # The engine needs a base_dir, use tmp_path
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    return result["outputs"]["list_step"]["result"]


# === Tests for list_files task ===


def test_list_files_default(tmp_path, setup_test_files):
    """Test listing all files in the base directory (default pattern '*')."""
    test_dir = setup_test_files
    result = run_list_files_task(tmp_path, {"directory": str(test_dir)})

    assert result["total_files"] == 2
    # Convert paths to strings for easier comparison
    file_list_str = sorted(
        [str(Path(f).relative_to(test_dir)) for f in result["file_list"]]
    )
    assert file_list_str == ["file1.txt", "file2.log"]


def test_list_files_specific_pattern(tmp_path, setup_test_files):
    """Test listing files with a specific pattern."""
    test_dir = setup_test_files
    result = run_list_files_task(
        tmp_path, {"directory": str(test_dir), "pattern": "*.txt"}
    )

    assert result["total_files"] == 1
    file_list_str = [str(Path(f).relative_to(test_dir)) for f in result["file_list"]]
    assert file_list_str == ["file1.txt"]


def test_list_files_recursive_default_pattern(tmp_path, setup_test_files):
    """Test recursive listing with the default pattern '*'."""
    test_dir = setup_test_files
    result = run_list_files_task(
        tmp_path, {"directory": str(test_dir), "recursive": True}
    )

    assert result["total_files"] == 5  # Includes base, subdir, and nested_dir files
    file_list_str = sorted(
        [str(Path(f).relative_to(test_dir)) for f in result["file_list"]]
    )
    expected = [
        "file1.txt",
        "file2.log",
        "subdir/sub_file1.txt",
        "subdir/sub_file2.yaml",
        "subdir/nested_dir/ignore_me.txt",
    ]
    assert file_list_str == sorted(expected)


def test_list_files_recursive_specific_pattern(tmp_path, setup_test_files):
    """Test recursive listing with a specific pattern."""
    test_dir = setup_test_files
    result = run_list_files_task(
        tmp_path, {"directory": str(test_dir), "pattern": "*.txt", "recursive": True}
    )

    assert result["total_files"] == 3  # txt files in base, subdir, and nested_dir
    file_list_str = sorted(
        [str(Path(f).relative_to(test_dir)) for f in result["file_list"]]
    )
    expected = [
        "file1.txt",
        "subdir/sub_file1.txt",
        "subdir/nested_dir/ignore_me.txt",
    ]
    assert file_list_str == sorted(expected)


def test_list_files_subdir(tmp_path, setup_test_files):
    """Test listing files only within a subdirectory."""
    test_dir = setup_test_files
    sub_dir = test_dir / "subdir"
    result = run_list_files_task(
        tmp_path, {"directory": str(sub_dir), "pattern": "*.yaml"}
    )

    assert result["total_files"] == 1
    # Check relative to sub_dir
    file_list_str = [str(Path(f).relative_to(sub_dir)) for f in result["file_list"]]
    assert file_list_str == ["sub_file2.yaml"]


def test_list_files_relative_path(tmp_path, setup_test_files):
    """Test listing using a relative path for the directory."""
    test_dir = setup_test_files
    # Change CWD to tmp_path so the relative path works
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # The engine runs in a subdir (workflow_run_X) of tmp_path.
        # The test_dir is also a subdir of tmp_path.
        # So, from the engine's workspace, the relative path is one level up.
        relative_dir_str = f"../{test_dir.name}"
        result = run_list_files_task(
            tmp_path, {"directory": relative_dir_str, "pattern": "*.log"}
        )
        assert result["total_files"] == 1
        # Check relative to test_dir for consistency
        file_list_str = [
            str(Path(f).relative_to(test_dir)) for f in result["file_list"]
        ]
        assert file_list_str == ["file2.log"]
    finally:
        os.chdir(original_cwd)


def test_list_files_missing_directory_param(tmp_path):
    """Test that omitting the required 'directory' parameter raises an error."""
    with pytest.raises(WorkflowError) as exc_info:
        run_list_files_task(tmp_path, {"pattern": "*.txt"})  # Missing directory
    # The underlying error is ValueError, wrapped by WorkflowError
    assert "directory parameter is required" in str(exc_info.value)
    assert isinstance(exc_info.value.original_error, ValueError)


def test_list_files_non_existent_directory(tmp_path):
    """Test listing in a directory that does not exist."""
    # The glob function itself doesn't raise an error for non-existent paths,
    # it just returns an empty list. The task should handle this gracefully.
    result = run_list_files_task(tmp_path, {"directory": str(tmp_path / "no_such_dir")})
    assert result["total_files"] == 0
    assert result["file_list"] == []
