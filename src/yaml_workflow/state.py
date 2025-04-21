"""
State management for workflow execution.

This module handles the persistence and management of workflow execution state,
including step completion, outputs, and retry mechanisms.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, cast


# Type definitions
class ExecutionState(TypedDict):
    current_step_name: Optional[str]
    completed_steps: List[str]
    failed_step: Optional[Dict[str, str]]
    step_outputs: Dict[str, Any]
    last_updated: str
    status: Literal["not_started", "in_progress", "completed", "failed"]
    flow: Optional[str]
    retry_counts: Dict[str, int]
    completed_at: Optional[str]
    error_flow_target: Optional[str]


class NamespaceDict(TypedDict):
    args: Dict[str, Any]
    env: Dict[str, Any]
    steps: Dict[str, Any]
    batch: Dict[str, Any]


METADATA_FILE = ".workflow_metadata.json"
DEFAULT_NAMESPACES: NamespaceDict = {"args": {}, "env": {}, "steps": {}, "batch": {}}


class WorkflowState:
    """Manages workflow execution state and persistence."""

    def __init__(self, workspace: Path, metadata: Optional[Dict[str, Any]] = None):
        """Initialize workflow state.

        Args:
            workspace: Path to workspace directory
            metadata: Optional pre-loaded metadata for resuming workflows
        """
        self.workspace = workspace
        self.metadata_path = workspace / METADATA_FILE

        # Initialize with empty state
        self.metadata: Dict[str, Any] = {
            "execution_state": cast(
                ExecutionState,
                {
                    "current_step_name": None,
                    "completed_steps": [],
                    "failed_step": None,
                    "step_outputs": {},
                    "last_updated": datetime.now().isoformat(),
                    "status": "not_started",
                    "flow": None,
                    "retry_counts": {},
                    "completed_at": None,
                    "error_flow_target": None,
                },
            ),
            "namespaces": DEFAULT_NAMESPACES.copy(),
        }

        if metadata is not None:
            # Update with provided metadata
            self.metadata.update(metadata)
            # Ensure required structures exist
            if "execution_state" not in self.metadata:
                self.metadata["execution_state"] = cast(
                    ExecutionState, self.metadata["execution_state"]
                )
            if "retry_counts" not in self.metadata["execution_state"]:
                self.metadata["execution_state"]["retry_counts"] = {}
            if "error_flow_target" not in self.metadata["execution_state"]:
                self.metadata["execution_state"]["error_flow_target"] = None
            if "namespaces" not in self.metadata:
                self.metadata["namespaces"] = DEFAULT_NAMESPACES.copy()
            self.save()
        else:
            self._load_state()

    def _load_state(self) -> None:
        """Load workflow state from metadata file."""
        if self.metadata_path.exists():
            with open(self.metadata_path) as f:
                loaded_metadata = json.load(f)
                self.metadata.update(loaded_metadata)

        # Ensure all required structures exist
        if "execution_state" not in self.metadata:
            self.metadata["execution_state"] = cast(
                ExecutionState,
                {
                    "current_step_name": None,
                    "completed_steps": [],
                    "failed_step": None,
                    "step_outputs": {},
                    "last_updated": datetime.now().isoformat(),
                    "status": "not_started",
                    "flow": None,
                    "retry_counts": {},
                    "completed_at": None,
                    "error_flow_target": None,
                },
            )
        if "namespaces" not in self.metadata:
            self.metadata["namespaces"] = DEFAULT_NAMESPACES.copy()
        self.save()

    def save(self) -> None:
        """Save current state to metadata file."""
        self.metadata["execution_state"]["last_updated"] = datetime.now().isoformat()
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def get_state(self) -> Dict[str, Any]:
        """Get the current workflow state.

        Returns:
            Dict[str, Any]: Current workflow state including execution state, step outputs, and namespaces
        """
        exec_state = cast(ExecutionState, self.metadata["execution_state"])
        return {
            "execution_state": exec_state,
            "namespaces": self.metadata["namespaces"],
            "steps": {
                # Iterate over all steps recorded in step_outputs
                step_name: step_data.copy()  # Return a copy of the recorded data
                for step_name, step_data in exec_state["step_outputs"].items()
            },
        }

    def update_namespace(self, namespace: str, data: Dict[str, Any]) -> None:
        """Update a namespace with new data.

        Args:
            namespace: Name of the namespace to update
            data: Data to update the namespace with
        """
        namespaces = cast(Dict[str, Dict[str, Any]], self.metadata["namespaces"])
        if namespace not in namespaces:
            namespaces[namespace] = {}
        namespaces[namespace].update(data)
        self.save()

    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get all data from a namespace.

        Args:
            namespace: Name of the namespace to get

        Returns:
            Dict[str, Any]: Namespace data
        """
        namespaces = cast(Dict[str, Dict[str, Any]], self.metadata["namespaces"])
        return namespaces.get(namespace, {})

    def get_variable(self, variable: str, namespace: str) -> Any:
        """Get a variable from a specific namespace.

        Args:
            variable: Name of the variable to get
            namespace: Namespace to get the variable from

        Returns:
            Any: Variable value
        """
        namespaces = cast(Dict[str, Dict[str, Any]], self.metadata["namespaces"])
        return namespaces.get(namespace, {}).get(variable)

    def clear_namespace(self, namespace: str) -> None:
        """Clear all data from a namespace.

        Args:
            namespace: Name of the namespace to clear
        """
        namespaces = cast(Dict[str, Dict[str, Any]], self.metadata["namespaces"])
        if namespace in namespaces:
            namespaces[namespace] = {}
            self.save()

    def mark_step_success(self, step_name: str, outputs: Dict[str, Any]) -> None:
        """Mark a step as completed successfully and store its outputs."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        if step_name not in state["completed_steps"]:
            state["completed_steps"].append(step_name)
        # Store status along with the outputs for consistency
        state["step_outputs"][step_name] = {"status": "completed", **outputs}
        state["status"] = "in_progress"  # Workflow status
        if state["failed_step"] and state["failed_step"]["step_name"] == step_name:
            state["failed_step"] = None
        self.reset_step_retries(step_name)
        self.save()

    def mark_step_failed(self, step_name: str, error: str) -> None:
        """Mark a step as terminally failed (retries exhausted/no error flow)."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        self.reset_step_retries(step_name)
        state["failed_step"] = {
            "step_name": step_name,
            "error": error,
            "failed_at": datetime.now().isoformat(),
        }
        # Also record the failure status in step_outputs for get_state() consistency
        failed_step_info = state["failed_step"]
        assert failed_step_info is not None
        state["step_outputs"][step_name] = {
            "status": "failed",
            "error": error,
            "skipped": False,
            "failed_at": failed_step_info["failed_at"],
        }
        state["status"] = "failed"
        self.save()

    def mark_step_skipped(
        self, step_name: str, reason: str = "Condition not met"
    ) -> None:
        """Mark a step as skipped."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        # Ensure skipped steps are not in completed list
        if step_name in state["completed_steps"]:
            state["completed_steps"].remove(step_name)
        # Add entry to step_outputs
        state["step_outputs"][step_name] = {
            "status": "skipped",
            "reason": reason,
            "skipped_at": datetime.now().isoformat(),
        }
        # Ensure it's not marked as failed if previously failed
        failed_step_info = state.get("failed_step")
        if failed_step_info and failed_step_info.get("step_name") == step_name:
            state["failed_step"] = None
        self.save()

    def mark_workflow_completed(self) -> None:
        """Mark the workflow as completed."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["status"] = "completed"
        state["completed_at"] = datetime.now().isoformat()
        state["current_step_name"] = None
        self.save()

    def set_flow(self, flow_name: Optional[str]) -> None:
        """Set the flow being executed."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["flow"] = flow_name
        self.save()

    def get_flow(self) -> Optional[str]:
        """Get the name of the flow being executed."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        return state.get("flow")

    def can_resume_from_step(self, step_name: str) -> bool:
        """Check if workflow can be resumed from a specific step."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        # Check if workflow is in failed state and has a failed step
        failed_step_info = state.get("failed_step")
        if state["status"] != "failed" or not failed_step_info:
            return False
        # Check if the failed step matches the requested step
        if failed_step_info.get("step_name") != step_name:
            return False
        # Ensure there's no active retry state for this step
        if "retry_counts" in state and step_name in state["retry_counts"]:
            return False
        return True

    def get_executed_steps(self) -> List[str]:
        """Get a list of successfully executed step names."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        return state["completed_steps"]

    def reset_state(self) -> None:
        """Reset the entire workflow state to initial values."""
        self.metadata["execution_state"] = cast(
            ExecutionState,
            {
                "current_step_name": None,
                "completed_steps": [],
                "failed_step": None,
                "step_outputs": {},
                "last_updated": datetime.now().isoformat(),
                "status": "not_started",
                "flow": None,
                "retry_counts": {},
                "completed_at": None,
                "error_flow_target": None,
            },
        )
        # Create a fresh copy of empty namespaces
        self.metadata["namespaces"] = {
            "args": {},
            "env": {},
            "steps": {},
            "batch": {},
        }
        self.save()

    def get_step_retry_count(self, step_name: str) -> int:
        """Get the current retry count for a specific step."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        return state.setdefault("retry_counts", {}).get(step_name, 0)

    def increment_step_retry(self, step_name: str) -> None:
        """Increment the retry count for a specific step."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        retry_counts = state.setdefault("retry_counts", {})
        current_count = retry_counts.get(step_name, 0)
        retry_counts[step_name] = current_count + 1
        self.save()

    def reset_step_retries(self, step_name: str) -> None:
        """Clear the retry state for a specific step."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state.setdefault("retry_counts", {}).pop(step_name, None)
        self.save()

    def set_error_flow_target(self, target_step_name: str) -> None:
        """Set the target step for an error flow jump."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["error_flow_target"] = target_step_name
        self.save()

    def get_error_flow_target(self) -> Optional[str]:
        """Get the target step for an error flow jump, if set."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        return state.setdefault("error_flow_target", None)

    def clear_error_flow_target(self) -> None:
        """Clear the error flow target step."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["error_flow_target"] = None
        self.save()

    def set_current_step(self, step_name: Optional[str]) -> None:
        """Set the name of the step currently being executed."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["current_step_name"] = step_name
        if step_name:
            state["status"] = "in_progress"
        self.save()

    def initialize_execution(self) -> None:
        """Reset state for a new execution run (not resume)."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        state["current_step_name"] = None
        state["completed_steps"] = []
        state["failed_step"] = None
        state["step_outputs"] = {}
        state["status"] = "not_started"
        state["retry_counts"] = {}
        state["completed_at"] = None
        state["error_flow_target"] = None
        self.save()

    def get_completed_outputs(self) -> Dict[str, Any]:
        """Get the outputs of all completed steps."""
        state = cast(ExecutionState, self.metadata["execution_state"])
        return state["step_outputs"]
