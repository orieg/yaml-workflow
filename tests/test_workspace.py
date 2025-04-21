"""Tests for workspace management functions."""

import json
import os
import time
from pathlib import Path

import pytest

from yaml_workflow.exceptions import WorkflowError
from yaml_workflow.workspace import (
    METADATA_FILE,
    create_workspace,
    get_run_number_from_metadata,
    get_workspace_info,
    resolve_path,
    save_metadata,
)


def test_create_workspace_default(tmp_path: Path):
    """Test default workspace creation."""
    base_dir = tmp_path / "runs"
    ws_path = create_workspace("test_workflow", base_dir=str(base_dir))

    assert ws_path.name == "test_workflow_run_1"
    assert ws_path.parent == base_dir
    assert (ws_path / "logs").is_dir()
    assert (ws_path / "output").is_dir()
    assert (ws_path / "temp").is_dir()
    assert (ws_path / METADATA_FILE).is_file()

    with open(ws_path / METADATA_FILE) as f:
        metadata = json.load(f)
    assert metadata["workflow_name"] == "test_workflow"
    assert metadata["run_number"] == 1
    assert metadata["custom_dir"] is False
    assert metadata["base_dir"] == str(base_dir.absolute())


def test_create_workspace_custom_dir(tmp_path: Path):
    """Test workspace creation with a custom directory (covers lines 57-60)."""
    custom_path = tmp_path / "my_custom_ws"
    # Deliberately don't create custom_path beforehand to test creation

    ws_path = create_workspace("custom_wf", custom_dir=str(custom_path))

    assert ws_path == custom_path
    assert ws_path.is_dir()
    assert (ws_path / "logs").is_dir()
    assert (ws_path / "output").is_dir()
    assert (ws_path / "temp").is_dir()
    assert (ws_path / METADATA_FILE).is_file()

    with open(ws_path / METADATA_FILE) as f:
        metadata = json.load(f)
    assert metadata["workflow_name"] == "custom_wf"
    assert metadata["run_number"] == 1  # Run number is 1 for custom dirs
    assert metadata["custom_dir"] is True
    # base_dir in metadata reflects default 'runs', even if unused for path calculation
    assert metadata["base_dir"] == str(Path("runs").absolute())


def test_create_workspace_next_run_number(tmp_path: Path):
    """Test correct run number increment (covers lines 80-90)."""
    base_dir = tmp_path / "runs_increment"
    wf_name = "increment_wf"
    sanitized_name = "increment_wf"  # Assuming sanitize_name works

    # Simulate run 1 existing
    run1_path = base_dir / f"{sanitized_name}_run_1"
    run1_path.mkdir(parents=True)
    save_metadata(run1_path, {"run_number": 1, "workflow_name": wf_name})
    # Ensure metadata file has older timestamp if needed for get_next_run logic
    time.sleep(0.01)

    # Create the next run
    ws_path_2 = create_workspace(wf_name, base_dir=str(base_dir))

    assert ws_path_2.name == f"{sanitized_name}_run_2"
    assert (ws_path_2 / METADATA_FILE).is_file()
    with open(ws_path_2 / METADATA_FILE) as f:
        metadata_2 = json.load(f)
    assert metadata_2["run_number"] == 2

    # Simulate run 2 existing
    time.sleep(0.01)
    ws_path_3 = create_workspace(wf_name, base_dir=str(base_dir))
    assert ws_path_3.name == f"{sanitized_name}_run_3"
    assert (ws_path_3 / METADATA_FILE).is_file()
    with open(ws_path_3 / METADATA_FILE) as f:
        metadata_3 = json.load(f)
    assert metadata_3["run_number"] == 3


def test_get_workspace_info_missing_metadata(tmp_path: Path):
    """Test get_workspace_info when metadata file is missing."""
    ws_path = tmp_path / "no_metadata_ws"
    ws_path.mkdir()
    (ws_path / "output" / "file.txt").parent.mkdir(parents=True)
    (ws_path / "output" / "file.txt").write_text("hello")

    info = get_workspace_info(ws_path)

    assert info["path"] == str(ws_path.absolute())
    assert info["size"] == 5  # Size of "hello"
    assert info["files"] == 1
    # Check that default/missing values are handled gracefully
    assert "workflow_name" not in info
    assert "run_number" not in info
    assert "created_at" not in info


# Note: Testing the error handling in cleanup_old_runs (lines 328-331)
# for shutil.move errors is complex and potentially platform-dependent.
# Skipping for now unless specific issues arise.

# Note: Testing lines 243-244 within get_workspace_info remains unclear,
# as they appear within the os.walk loop unrelated to metadata parsing.
# Assuming they are covered implicitly by standard walks.

# --- Tests for Helper Functions ---


def test_get_run_number_from_metadata_valid(tmp_path: Path):
    """Test get_run_number_from_metadata with valid metadata."""
    ws_path = tmp_path / "valid_meta_ws"
    ws_path.mkdir()
    metadata = {"run_number": 5, "workflow_name": "test"}
    (ws_path / METADATA_FILE).write_text(json.dumps(metadata))

    run_number = get_run_number_from_metadata(ws_path)
    assert run_number == 5


def test_get_run_number_from_metadata_missing_file(tmp_path: Path):
    """Test get_run_number_from_metadata when file is missing."""
    ws_path = tmp_path / "missing_meta_ws"
    ws_path.mkdir()

    run_number = get_run_number_from_metadata(ws_path)
    assert run_number is None


def test_get_run_number_from_metadata_invalid_json(tmp_path: Path):
    """Test get_run_number_from_metadata with invalid JSON."""
    ws_path = tmp_path / "invalid_json_ws"
    ws_path.mkdir()
    (ws_path / METADATA_FILE).write_text("this is not json")

    run_number = get_run_number_from_metadata(ws_path)
    assert run_number is None


def test_get_run_number_from_metadata_missing_key(tmp_path: Path):
    """Test get_run_number_from_metadata when run_number key is missing."""
    ws_path = tmp_path / "missing_key_ws"
    ws_path.mkdir()
    metadata = {"workflow_name": "test"}  # Missing run_number
    (ws_path / METADATA_FILE).write_text(json.dumps(metadata))

    run_number = get_run_number_from_metadata(ws_path)
    assert run_number is None


def test_resolve_path_relative(tmp_path: Path):
    """Test resolve_path with a relative path."""
    ws_path = tmp_path / "resolve_ws"
    ws_path.mkdir()

    resolved = resolve_path(ws_path, "output/data.csv")
    assert resolved == ws_path / "output" / "data.csv"
    assert resolved.is_absolute()


def test_resolve_path_absolute(tmp_path: Path):
    """Test resolve_path with an absolute path."""
    ws_path = tmp_path / "resolve_ws_abs"
    ws_path.mkdir()
    abs_path_str = str((tmp_path / "absolute_file.txt").absolute())

    resolved = resolve_path(ws_path, abs_path_str)
    assert resolved == Path(abs_path_str)
    assert resolved.is_absolute()


def test_resolve_path_nonexistent(tmp_path: Path):
    """Test resolve_path with a non-existent relative path."""
    ws_path = tmp_path / "resolve_ws_nonexist"
    ws_path.mkdir()

    resolved = resolve_path(ws_path, "temp/subdir/myfile.yaml")
    assert resolved == ws_path / "temp" / "subdir" / "myfile.yaml"
    assert resolved.is_absolute()
    # We don't expect resolve_path to create the file/dir
    assert not resolved.exists()
