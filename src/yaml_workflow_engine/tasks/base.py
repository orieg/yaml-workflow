"""
Base functionality for task handlers.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

def get_task_logger(workspace: Path, task_name: str) -> logging.Logger:
    """
    Get a logger for a task that logs to the workspace logs directory.
    
    Args:
        workspace: Workspace directory
        task_name: Name of the task
        
    Returns:
        logging.Logger: Configured logger
    """
    # Get logger for task
    logger = logging.getLogger(f"task.{task_name}")
    
    # Logger is already configured if it has handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create file handler
    logs_dir = workspace / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    log_file = logs_dir / "tasks.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Add handler
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    
    return logger

def log_task_execution(
    logger: logging.Logger,
    step: Dict[str, Any],
    context: Dict[str, Any],
    workspace: Path
) -> None:
    """
    Log task execution details.
    
    Args:
        logger: Task logger
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
    """
    task_name = step.get("name", "unnamed_task")
    task_type = step.get("type", "unknown")
    
    logger.info(f"Executing task '{task_name}' of type '{task_type}'")
    logger.debug(f"Step configuration: {step}")
    logger.debug(f"Context: {context}")
    logger.debug(f"Workspace: {workspace}")

def log_task_result(logger: logging.Logger, result: Any) -> None:
    """
    Log task execution result.
    
    Args:
        logger: Task logger
        result: Task result
    """
    logger.info("Task completed successfully")
    logger.debug(f"Result: {result}")

def log_task_error(logger: logging.Logger, error: Exception) -> None:
    """
    Log task execution error.
    
    Args:
        logger: Task logger
        error: Exception that occurred
    """
    logger.error(f"Task failed: {str(error)}", exc_info=True) 