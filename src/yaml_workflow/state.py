"""
State management for workflow execution.

This module handles the persistence and management of workflow execution state,
including step completion, outputs, and retry mechanisms.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal, TypedDict

# Type definitions
class ExecutionState(TypedDict):
    current_step: int
    completed_steps: List[str]
    failed_step: Optional[Dict[str, str]]
    step_outputs: Dict[str, Any]
    last_updated: str
    status: Literal["not_started", "in_progress", "completed", "failed"]
    flow: Optional[str]
    retry_state: Dict[str, Dict[str, Any]]

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
                            and self.metadata["execution_state"]["failed_step"]["step_name"] == step
                            else "not_started"
                        )
                    ),
                    "outputs": self.metadata["execution_state"]["step_outputs"].get(step, {}),
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
            "retry_state": {},  # Add retry state tracking
            "last_updated": datetime.now().isoformat(),
            "status": "not_started",
            "flow": None,
        }
        self.save()

    def get_retry_state(self, step_name: str) -> Dict[str, Any]:
        """Get retry state for a step."""
        return self.metadata["execution_state"].get("retry_state", {}).get(step_name, {})

    def update_retry_state(self, step_name: str, retry_state: Dict[str, Any]) -> None:
        """Update retry state for a step."""
        if "retry_state" not in self.metadata["execution_state"]:
            self.metadata["execution_state"]["retry_state"] = {}
        self.metadata["execution_state"]["retry_state"][step_name] = retry_state
        self.save()

    def clear_retry_state(self, step_name: str) -> None:
        """Clear retry state for a step."""
        if "retry_state" in self.metadata["execution_state"]:
            self.metadata["execution_state"]["retry_state"].pop(step_name, None)
            self.save()
