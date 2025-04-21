"""
Workspace management for workflow execution.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from yaml_workflow.exceptions import WorkflowError

from .state import METADATA_FILE, WorkflowState


def sanitize_name(name: str) -> str:
    """
    Sanitize a name for use in file paths.

    Args:
        name: Name to sanitize

    Returns:
        str: Sanitized name
    """
    # Replace spaces and special characters with underscores
    return re.sub(r"[^\w\-_]", "_", name)


def get_next_run_number(base_dir: Path, workflow_name: str) -> int:
    """
    Get the next available run number for a workflow by checking existing run directories.

    Args:
        base_dir: Base directory containing workflow runs
        workflow_name: Name of the workflow

    Returns:
        int: Next available run number
    """
    sanitized_name = sanitize_name(workflow_name)
    highest_run_number = 0
    latest_run_dir = None

    # Find existing run directories for this workflow
    if base_dir.is_dir():  # Check if base_dir exists
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.startswith(f"{sanitized_name}_run_"):
                try:
                    # Extract run number from directory name
                    run_num_str = item.name.split("_run_")[-1]
                    run_num = int(run_num_str)
                    if run_num > highest_run_number:
                        highest_run_number = run_num
                        latest_run_dir = item
                except (ValueError, IndexError):
                    continue  # Ignore directories with malformed names

    # If we found existing runs, try to get the run number from the latest one's metadata
    # This is more reliable than just parsing the directory name in case of manual renaming/gaps
    if latest_run_dir:
        metadata_path = latest_run_dir / METADATA_FILE
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    meta_run_number = metadata.get("run_number")
                    if isinstance(meta_run_number, int):
                        # Use the metadata run number if valid
                        highest_run_number = meta_run_number
            except (json.JSONDecodeError, IOError):
                # If metadata is corrupt, we might fall back to the highest number found from dir names
                pass

    # The next run number is the highest found + 1
    return highest_run_number + 1


def save_metadata(workspace: Path, metadata: Dict[str, Any]) -> None:
    """Save metadata to the workspace directory."""
    metadata_path = workspace / METADATA_FILE
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)


def get_run_number_from_metadata(workspace: Path) -> Optional[int]:
    """
    Get run number from workspace metadata file.

    Args:
        workspace: Workspace directory

    Returns:
        Optional[int]: Run number if found in metadata, None otherwise
    """
    metadata_path = workspace / METADATA_FILE
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
                run_number = metadata.get("run_number")
                if isinstance(run_number, int):
                    return run_number
        except (json.JSONDecodeError, IOError):
            pass
    return None


def create_workspace(
    workflow_name: str, custom_dir: Optional[str] = None, base_dir: str = "runs"
) -> Path:
    """
    Create a workspace directory for a workflow run.

    Args:
        workflow_name: Name of the workflow
        custom_dir: Optional custom directory path
        base_dir: Base directory for workflow runs

    Returns:
        Path: Path to the workspace directory
    """
    base_path = Path(base_dir)
    base_path.mkdir(exist_ok=True)

    sanitized_name = sanitize_name(workflow_name)

    if custom_dir:
        workspace = Path(custom_dir)
    else:
        # Get run number
        run_number = get_next_run_number(base_path, sanitized_name)
        workspace = base_path / f"{sanitized_name}_run_{run_number}"

    # Create workspace directories
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "temp").mkdir(exist_ok=True)

    # Create new metadata
    metadata = {
        "workflow_name": workflow_name,
        "created_at": datetime.now().isoformat(),
        "run_number": run_number if not custom_dir else 1,
        "custom_dir": bool(custom_dir),
        "base_dir": str(base_path.absolute()),
    }

    save_metadata(workspace, metadata)

    return workspace


def resolve_path(workspace: Path, file_path: str) -> Path:
    """
    Resolve a file path relative to the workspace directory.

    Args:
        workspace: Workspace directory
        file_path: File path to resolve

    Returns:
        Path: Resolved absolute path

    Handles paths:
    1. If path is absolute, return it as is.
    2. If path is relative, join it with the workspace root.
       Users should include prefixes like 'output/', 'logs/', 'temp/' explicitly if needed.
    """
    path = Path(file_path)

    # If path is absolute, return it as is
    if path.is_absolute():
        return path

    # Otherwise, resolve relative to workspace root
    # Implicit 'output/' prefixing removed for consistency.
    return workspace / path


def get_workspace_info(workspace: Path) -> Dict[str, Any]:
    """
    Get information about a workspace.

    Args:
        workspace: Workspace directory

    Returns:
        dict: Workspace information
    """
    metadata_path = workspace / METADATA_FILE
    metadata = {}
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

    # Calculate size and file count
    total_size = 0
    file_count = 0
    for root, _, files in os.walk(workspace):
        for file in files:
            file_path = Path(root) / file
            total_size += file_path.stat().st_size
            file_count += 1

    return {
        **metadata,
        "path": str(workspace.absolute()),
        "size": total_size,
        "files": file_count,
    }


class BatchState:
    """Manages batch processing state."""

    def __init__(self, workspace: Path, name: str):
        """Initialize batch state.

        Args:
            workspace: Workspace directory
            name: Name of the batch
        """
        self.workspace = workspace
        self.name = name
        self.state_dir = workspace / "temp" / "batch_state"
        self.state_file = self.state_dir / f"{name}.json"

        # Initialize with empty state
        self.state: Dict[str, Any] = {
            "processed": [],  # List[str]
            "failed": {},  # Dict[str, Dict[str, str]]
            "template_errors": {},  # Dict[str, Dict[str, str]]
            "namespaces": {  # Dict[str, Dict[str, Any]]
                "args": {},
                "env": {},
                "steps": {},
                "batch": {},
            },
            "stats": {  # Dict[str, int]
                "total": 0,
                "processed": 0,
                "failed": 0,
                "template_failures": 0,
                "retried": 0,
            },
        }

        # Load existing state if available
        if self.state_file.exists():
            self._load_state()

    def _load_state(self) -> None:
        """Load state from file."""
        try:
            state_data = json.loads(self.state_file.read_text())
            self.state.update(state_data)
        except Exception as e:
            raise WorkflowError(f"Failed to load batch state: {e}")

    def save(self) -> None:
        """Save current state to file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def mark_processed(self, item: Any, result: Dict[str, Any]) -> None:
        """Mark an item as successfully processed.

        Args:
            item: The processed item
            result: Processing result
        """
        processed_items = cast(List[str], self.state["processed"])
        if str(item) not in processed_items:
            processed_items.append(str(item))
            self.state["stats"]["processed"] += 1

    def mark_failed(self, item: Any, error: str) -> None:
        """Mark an item as failed.

        Args:
            item: The failed item
            error: Error message
        """
        failed_items = cast(Dict[str, Dict[str, str]], self.state["failed"])
        failed_items[str(item)] = {
            "error": error,
            "timestamp": str(datetime.now()),
        }
        self.state["stats"]["failed"] += 1

    def mark_template_error(self, item: Any, error: str) -> None:
        """Mark an item as having a template error.

        Args:
            item: The item with template error
            error: Template error message
        """
        template_errors = cast(Dict[str, Dict[str, str]], self.state["template_errors"])
        template_errors[str(item)] = {
            "error": error,
            "timestamp": str(datetime.now()),
        }
        self.state["stats"]["template_failures"] += 1

    def update_namespace(self, namespace: str, data: Dict[str, Any]) -> None:
        """Update namespace data.

        Args:
            namespace: Name of the namespace
            data: Namespace data to update
        """
        namespaces = cast(Dict[str, Dict[str, Any]], self.state["namespaces"])
        if namespace in namespaces:
            namespaces[namespace].update(data)

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics.

        Returns:
            Dict containing processing statistics
        """
        return cast(Dict[str, int], self.state["stats"])

    def reset(self) -> None:
        """Reset batch state."""
        self.state = {
            "processed": [],  # List[str]
            "failed": {},  # Dict[str, Dict[str, str]]
            "template_errors": {},  # Dict[str, Dict[str, str]]
            "namespaces": {  # Dict[str, Dict[str, Any]]
                "args": {},
                "env": {},
                "steps": {},
                "batch": {},
            },
            "stats": {  # Dict[str, int]
                "total": 0,
                "processed": 0,
                "failed": 0,
                "template_failures": 0,
                "retried": 0,
            },
        }
        if self.state_file.exists():
            self.state_file.unlink()
