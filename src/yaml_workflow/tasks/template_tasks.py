"""Template-based task handlers."""

import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import StrictUndefined, Template, UndefinedError

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

        # Process inputs with template resolution
        processed = config.process_inputs()

        template_str = processed.get("template")
        if not template_str:
            raise ValueError("No template provided")

        output_file = processed.get("output")
        if not output_file:
            raise ValueError("No output file specified")

        # Render template with strict undefined handling
        template = Template(template_str, undefined=StrictUndefined)
        rendered = template.render(**config._context)

        # Save to file
        # Assuming output_file is relative to workspace
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
