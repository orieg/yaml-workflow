"""
Workspace management for workflow execution.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import METADATA_FILE, WorkflowState
from yaml_workflow.exceptions import WorkflowError

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
    Get the next available run number for a workflow by checking metadata files.

    Args:
        base_dir: Base directory containing workflow runs
        workflow_name: Name of the workflow

    Returns:
        int: Next available run number
    """
    sanitized_name = sanitize_name(workflow_name)
    workspace = base_dir / sanitized_name

    if not workspace.is_dir():
        return 1

    # Check metadata file
    metadata_path = workspace / METADATA_FILE
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                metadata = json.load(f)
                run_number = metadata.get("run_number", 0)
                if run_number and isinstance(run_number, int):
                    return run_number + 1
        except (json.JSONDecodeError, IOError):
            pass

    return 1


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


def resolve_path(workspace: Path, file_path: str, use_output_dir: bool = True) -> Path:
    """
    Resolve a file path relative to the workspace directory.

    Args:
        workspace: Workspace directory
        file_path: File path to resolve
        use_output_dir: Whether to place files in the output directory by default

    Returns:
        Path: Resolved absolute path

    The function handles paths in the following way:
    1. If the path is absolute, return it as is
    2. If the path starts with output/, logs/, or temp/, resolve it relative to workspace
    3. If use_output_dir is True and path doesn't start with a known directory, resolve relative to workspace/output/
    4. Otherwise, resolve relative to workspace
    """
    path = Path(file_path)

    # If path is absolute, return it as is
    if path.is_absolute():
        return path

    # If path starts with a known workspace subdirectory, resolve relative to workspace
    if any(file_path.startswith(prefix) for prefix in ["output/", "logs/", "temp/"]):
        return workspace / path

    # If use_output_dir is True and path doesn't start with a known directory, resolve relative to workspace/output/
    if use_output_dir:
        return workspace / "output" / path

    # Otherwise, resolve relative to workspace
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
    """State manager for batch processing with namespace support."""
    def __init__(self, workspace: Path, name: str):
        """Initialize batch state.
        
        Args:
            workspace: Path to workspace directory
            name: Name of the batch process
        """
        self.workspace = workspace
        self.name = name
        self.state_dir = workspace / ".batch_state"
        self.state_file = self.state_dir / f"{name}_state.json"
        
        self.state = {
            "processed": [],  # Keep order for resume
            "failed": {},     # item -> error info
            "template_errors": {},  # Track template resolution failures
            "namespaces": {   # Track namespace states
                "args": {},
                "env": {},
                "steps": {},
                "batch": {}
            },
            "stats": {
                "total": 0,
                "processed": 0,
                "failed": 0,
                "template_failures": 0,
                "retried": 0
            }
        }
        
        self._load_state()
        
    def _load_state(self) -> None:
        """Load state from file if it exists."""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except json.JSONDecodeError as e:
                raise WorkflowError(f"Failed to load batch state: {e}")
                
    def save(self) -> None:
        """Save current state to file."""
        self.state_dir.mkdir(exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))
        
    def mark_processed(self, item: Any, result: Dict[str, Any]) -> None:
        """Mark an item as successfully processed.
        
        Args:
            item: The processed item
            result: Processing result
        """
        if item not in self.state["processed"]:
            self.state["processed"].append(item)
            self.state["stats"]["processed"] += 1
            
    def mark_failed(self, item: Any, error: str) -> None:
        """Mark an item as failed.
        
        Args:
            item: The failed item
            error: Error message
        """
        self.state["failed"][str(item)] = {
            "error": error,
            "timestamp": str(datetime.now())
        }
        self.state["stats"]["failed"] += 1
        
    def mark_template_error(self, item: Any, error: str) -> None:
        """Mark an item as having a template error.
        
        Args:
            item: The item with template error
            error: Template error message
        """
        self.state["template_errors"][str(item)] = {
            "error": error,
            "timestamp": str(datetime.now())
        }
        self.state["stats"]["template_failures"] += 1
        
    def update_namespace(self, namespace: str, data: Dict[str, Any]) -> None:
        """Update namespace data.
        
        Args:
            namespace: Name of the namespace
            data: Namespace data to update
        """
        if namespace in self.state["namespaces"]:
            self.state["namespaces"][namespace].update(data)
            
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics.
        
        Returns:
            Dict containing processing statistics
        """
        return self.state["stats"]
        
    def reset(self) -> None:
        """Reset batch state."""
        self.state = {
            "processed": [],
            "failed": {},
            "template_errors": {},
            "namespaces": {
                "args": {},
                "env": {},
                "steps": {},
                "batch": {}
            },
            "stats": {
                "total": 0,
                "processed": 0,
                "failed": 0,
                "template_failures": 0,
                "retried": 0
            }
        }
        if self.state_file.exists():
            self.state_file.unlink()
