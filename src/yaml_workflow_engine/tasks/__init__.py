"""
Task modules for the YAML Workflow Engine.

This package contains various task modules that can be used in workflows.
Each module provides specific functionality that can be referenced in workflow YAML files.
"""

from typing import Any, Callable, Dict, Optional
from pathlib import Path

# Type for task handlers
TaskHandler = Callable[[Dict[str, Any], Dict[str, Any], Path], Any]

# Registry of task handlers
_task_handlers: Dict[str, TaskHandler] = {}

def register_task(name: str) -> Callable[[TaskHandler], TaskHandler]:
    """
    Decorator to register a task handler.
    
    Args:
        name: Name of the task type
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: TaskHandler) -> TaskHandler:
        _task_handlers[name] = func
        return func
    return decorator

def get_task_handler(task_type: str) -> Optional[TaskHandler]:
    """
    Get a task handler by type.
    
    Args:
        task_type: Type of task
        
    Returns:
        Optional[TaskHandler]: Task handler function if found, None otherwise
    """
    return _task_handlers.get(task_type)

# Import built-in task handlers
from . import template_tasks
from . import shell_tasks
from . import file_tasks 