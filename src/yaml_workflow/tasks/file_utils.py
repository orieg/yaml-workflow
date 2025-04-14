"""
File utility tasks for file system operations.
"""

import os
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import register_task
from .base import get_task_logger


@register_task("file_utils")
def list_files(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> Dict[str, Any]:
    """
    List files in a directory matching a pattern.

    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory

    Returns:
        Dict[str, Any]: Dictionary containing:
            - file_list: List of matching file paths
            - total_files: Total number of files found
    """
    logger = get_task_logger(workspace, step.get("name", "list_files"))

    # Get input parameters
    inputs = step.get("inputs", {})
    directory = inputs.get("directory")
    pattern = inputs.get("pattern", "*")
    recursive = inputs.get("recursive", False)

    if not directory:
        raise ValueError("directory parameter is required")

    # Resolve directory path
    if not os.path.isabs(directory):
        directory = os.path.join(str(workspace), directory)

    # Build glob pattern
    if recursive:
        if not pattern.startswith("**/"):
            pattern = f"**/{pattern}"
    search_pattern = os.path.join(directory, pattern)

    # Find files
    logger.info(f"Searching for files: {search_pattern}")
    files = [f for f in glob(search_pattern, recursive=recursive) if os.path.isfile(f)]
    total = len(files)

    logger.info(f"Found {total} files matching pattern")

    # Return results
    return {"file_list": files, "total_files": total}
