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

from ..exceptions import TemplateError
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

        output_file = raw_inputs.get("output")
        if not output_file or not isinstance(output_file, str):
            raise ValueError("Input 'output' must be a non-empty string")

        # Get the shared template engine from config
        template_engine = config._template_engine

        # Render template using the engine, providing the workspace as searchpath
        # Pass the full context for rendering
        rendered = template_engine.process_template(
            template_str,
            variables=config._context,  # Pass the full context
            searchpath=str(config.workspace),  # Enable includes relative to workspace
        )

        # Save to file (use the raw output_file path)
        output_path = config.workspace / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)

        result = {"output_path": str(output_path)}
        log_task_result(logger, result)
        return result

    except Exception as e:
        # Centralized error handling
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable
