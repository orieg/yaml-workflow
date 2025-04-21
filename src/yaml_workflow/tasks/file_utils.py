"""
File utility tasks for file system operations.
"""

import os
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Tuple

from . import TaskConfig, register_task
from .base import get_task_logger


@register_task("file_utils")
def list_files(config: TaskConfig) -> Dict[str, Any]:
    """
    List files in a directory matching a pattern.

    Args:
        config: Task configuration containing:
            - step: Step configuration
            - context: Workflow context
            - workspace: Workspace directory

    Returns:
        Dict[str, Any]: Dictionary containing:
            - file_list: List of matching file paths
            - total_files: Total number of files found
    """
    logger = get_task_logger(config.workspace, config.step.get("name", "list_files"))

    # Get input parameters
    inputs = config.step.get("inputs", {})
    directory = inputs.get("directory")
    pattern = inputs.get("pattern", "*")
    recursive = inputs.get("recursive", False)

    if not directory:
        raise ValueError("directory parameter is required")

    # Resolve directory path relative to the workspace root
    input_path = Path(directory)
    if input_path.is_absolute():
        resolved_dir = input_path
    else:
        # config.workspace is the Workspace object OR the Path obj in tests
        # Access the path correctly depending on type (safer check)
        workspace_path = getattr(config.workspace, "path", config.workspace)
        resolved_dir = workspace_path / input_path

    # Build glob pattern using resolved_dir
    search_path_base = str(resolved_dir)
    if recursive:
        if not pattern.startswith("**/"):
            pattern = f"**/{pattern}"
    search_pattern = os.path.join(search_path_base, pattern)

    # Find files
    logger.info(f"Searching for files: {search_pattern}")
    # Use Path objects for manipulation and resolve to absolute paths
    file_paths = [
        Path(f).resolve()
        for f in glob(search_pattern, recursive=recursive)
        if Path(f).is_file()
    ]
    # Convert back to strings for the output dictionary
    files_str = [str(p) for p in file_paths]
    total = len(files_str)

    logger.info(f"Found {total} files matching pattern")

    # Return results
    return {"file_list": files_str, "total_files": total}
