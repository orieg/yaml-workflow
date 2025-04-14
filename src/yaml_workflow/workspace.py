"""
Workspace management for workflow execution.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

METADATA_FILE = ".workflow_metadata.json"


class WorkflowState:
    """Manages workflow execution state and persistence."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.metadata_path = workspace / METADATA_FILE
        self._load_state()

    def _load_state(self) -> None:
        """Load workflow state from metadata file."""
        if self.metadata_path.exists():
            with open(self.metadata_path) as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

        # Initialize execution state if not present
        if "execution_state" not in self.metadata:
            self.metadata["execution_state"] = {
                "current_step": 0,
                "completed_steps": [],
                "failed_step": None,
                "step_outputs": {},
                "last_updated": datetime.now().isoformat(),
                "status": "not_started",  # Possible values: not_started, in_progress, completed, failed
                "flow": None,  # Track which flow is being executed
            }
            self.save()  # Save the initialized state to disk

    def save(self) -> None:
        """Save current state to metadata file."""
        self.metadata["execution_state"]["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def get_state(self) -> Dict[str, Any]:
        """Get the current workflow state.

        Returns:
            Dict[str, Any]: Current workflow state including execution state and step outputs
        """
        return {
            "execution_state": self.metadata["execution_state"],
            "steps": {
                step: {
                    "status": (
                        "completed"
                        if step in self.metadata["execution_state"]["completed_steps"]
                        else (
                            "failed"
                            if self.metadata["execution_state"]["failed_step"]
                            and self.metadata["execution_state"]["failed_step"][
                                "step_name"
                            ]
                            == step
                            else "not_started"
                        )
                    ),
                    "outputs": self.metadata["execution_state"]["step_outputs"].get(
                        step, {}
                    ),
                }
                for step in set(
                    self.metadata["execution_state"]["completed_steps"]
                    + (
                        [self.metadata["execution_state"]["failed_step"]["step_name"]]
                        if self.metadata["execution_state"]["failed_step"]
                        else []
                    )
                )
            },
        }

    def mark_step_complete(self, step_name: str, outputs: Dict[str, Any]) -> None:
        """Mark a step as completed and store its outputs."""
        state = self.metadata["execution_state"]
        state["current_step"] += 1
        state["completed_steps"].append(step_name)
        state["step_outputs"][step_name] = outputs
        state["status"] = "in_progress"
        self.save()

    def mark_step_failed(self, step_name: str, error: str) -> None:
        """Mark a step as failed with error information."""
        state = self.metadata["execution_state"]
        state["failed_step"] = {
            "step_name": step_name,
            "error": error,
            "failed_at": datetime.now().isoformat(),
        }
        state["status"] = "failed"
        self.save()

    def mark_workflow_completed(self) -> None:
        """Mark the workflow as completed."""
        state = self.metadata["execution_state"]
        state["status"] = "completed"
        state["completed_at"] = datetime.now().isoformat()
        self.save()

    def set_flow(self, flow_name: Optional[str]) -> None:
        """Set the flow being executed."""
        state = self.metadata["execution_state"]
        state["flow"] = flow_name
        self.save()

    def get_flow(self) -> Optional[str]:
        """Get the name of the flow being executed."""
        return self.metadata["execution_state"].get("flow")

    def can_resume_from_step(self, step_name: str) -> bool:
        """Check if workflow can be resumed from a specific step."""
        state = self.metadata["execution_state"]
        return (
            state["status"] == "failed"
            and state["failed_step"] is not None
            and step_name not in state["completed_steps"]
        )

    def get_completed_outputs(self) -> Dict[str, Any]:
        """Get outputs from all completed steps."""
        return self.metadata["execution_state"]["step_outputs"]

    def reset_state(self) -> None:
        """Reset workflow execution state."""
        self.metadata["execution_state"] = {
            "current_step": 0,
            "completed_steps": [],
            "failed_step": None,
            "step_outputs": {},
            "last_updated": datetime.now().isoformat(),
            "status": "not_started",
            "flow": None,
        }
        self.save()


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
        workspace = base_path / sanitized_name

    # Load existing metadata if it exists
    metadata_path = workspace / METADATA_FILE
    existing_metadata = {}
    if metadata_path.exists():
        try:
            with open(metadata_path) as f:
                existing_metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Get run number
    existing_run = get_run_number_from_metadata(workspace)
    run_number = (existing_run + 1) if existing_run is not None else 1

    # Create workspace directories
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "temp").mkdir(exist_ok=True)

    # Create new metadata preserving execution state
    metadata = {
        "workflow_name": workflow_name,
        "created_at": datetime.now().isoformat(),
        "run_number": run_number,
        "custom_dir": bool(custom_dir),
        "base_dir": str(base_path.absolute()),
    }

    # Preserve execution state if it exists and indicates a failed state
    if "execution_state" in existing_metadata:
        exec_state = existing_metadata["execution_state"]
        if exec_state.get("status") == "failed" and exec_state.get("failed_step"):
            metadata["execution_state"] = exec_state

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
