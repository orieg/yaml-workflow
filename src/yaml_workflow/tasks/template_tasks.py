"""Template-based task handlers."""

import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    Template,
    UndefinedError,
)

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error

logger = logging.getLogger(__name__)


@register_task("template")
def render_template(config: TaskConfig) -> Dict[str, Any]:
    """
    Render a template and save it to a file.

    Args:
        config: Task configuration object

    Returns:
        Dict[str, Any]: Dictionary containing the path to the output file

    Raises:
        TaskExecutionError: If template resolution fails or file cannot be written (via handle_task_error)
    """
    task_name = str(config.name or "template_task")
    task_type = str(config.type or "template")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)

        # Get raw inputs directly, do not process them here
        raw_inputs = config.step.get("inputs", {})
        template_str = raw_inputs.get("template")
        if not template_str or not isinstance(template_str, str):
            raise ValueError("Input 'template' must be a non-empty string")

        # Correctly get the output file path using 'output_file' key
        output_file_rel_path = raw_inputs.get("output_file")
        if not output_file_rel_path or not isinstance(output_file_rel_path, str):
            raise ValueError("Input 'output_file' must be a non-empty string")

        # Resolve the full output path relative to the workspace
        output_path = config.workspace / output_file_rel_path

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Resolve the template content using the engine
        # Pass workspace as searchpath to allow includes
        resolved_content = config._template_engine.process_template(
            template_str,
            config._context,
            searchpath=str(config.workspace),  # Pass workspace for includes
        )

        # Write the resolved content to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(resolved_content)

        log_task_result(logger, str(output_path))
        return {"path": str(output_path)}

    except Exception as e:
        # Use a centralized error handler if available, otherwise raise TaskExecutionError
        # Assuming handle_task_error exists (replace if necessary)
        # handle_task_error(task_name, e, config)
        # Fallback if no central handler:
        logger.error(f"Task '{task_name}' failed: {str(e)}", exc_info=True)
        raise TaskExecutionError(
            step_name=task_name, original_error=e, task_config=config.step
        )
