"""
State management for YAML workflows.

This module provides state management functionality for tracking workflow execution,
including step completion, failures, and output tracking.
"""

from .workspace import WorkflowState

__all__ = ["WorkflowState"]
