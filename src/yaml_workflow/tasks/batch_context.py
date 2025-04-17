"""Batch processing context management."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from yaml_workflow.tasks import TaskConfig


class BatchContext:
    """Context manager for batch processing with namespace support."""

    def __init__(self, config: TaskConfig):
        """Initialize batch context.

        Args:
            config: Task configuration with namespace support
        """
        self.name = config.name
        self.engine = config.get_variable("engine")
        self.workspace = config.workspace
        self.retry_config = config.inputs.get("retry", {})
        self._context = config._context

    def create_item_context(self, item: Any, index: int) -> Dict[str, Any]:
        """Create context for a batch item while preserving namespaces.

        Args:
            item: The batch item being processed
            index: Index of the item in the batch

        Returns:
            Dict containing the item context with namespace support
        """
        return {
            "args": self._context.get("args", {}),
            "env": self._context.get("env", {}),
            "steps": self._context.get("steps", {}),
            "batch": {"item": item, "index": index, "name": self.name},
        }

    def get_error_context(self, error: Exception) -> Dict[str, Any]:
        """Get error context with namespace information.

        Args:
            error: The exception that occurred

        Returns:
            Dict containing error context with namespace information
        """
        return {
            "error": str(error),
            "available_variables": self.get_available_variables(),
            "namespaces": list(self._context.keys()),
        }

    def get_available_variables(self) -> Dict[str, List[str]]:
        """Get available variables by namespace.

        Returns:
            Dict mapping namespace names to lists of available variables
        """
        return {
            "args": list(self._context.get("args", {}).keys()),
            "env": list(self._context.get("env", {}).keys()),
            "steps": list(self._context.get("steps", {}).keys()),
            "batch": ["item", "index", "name"],
        }
