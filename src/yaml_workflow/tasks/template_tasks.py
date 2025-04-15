"""Template-based task handlers."""

import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TemplateError
from ..workspace import resolve_path
from . import register_task

logger = logging.getLogger(__name__)


@register_task("template")
def render_template(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Path
) -> str:
    """
    Render a template and save it to a file.

    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory

    Returns:
        str: Path to the output file

    Raises:
        TemplateError: If template resolution fails or file cannot be written
    """
    try:
        # Get template and output path
        template_str = step.get("template")
        if not template_str:
            raise ValueError("No template provided")

        output_file = step.get("output")
        if not output_file:
            raise ValueError("No output file specified")

        logger.debug(f"Template string: {template_str}")
        logger.debug(f"Context for rendering: {context}")

        # Render template with strict undefined handling
        template = Template(template_str, undefined=StrictUndefined)
        try:
            rendered = template.render(**context)
            logger.debug(f"Rendered template: {rendered}")
        except UndefinedError as e:
            available = {
                "args": list(context["args"].keys()) if "args" in context else [],
                "env": list(context["env"].keys()) if "env" in context else [],
                "steps": list(context["steps"].keys()) if "steps" in context else [],
                "vars": {k: type(v).__name__ for k, v in context.items() 
                        if k not in ["args", "env", "steps"]}
            }
            raise TemplateError(
                f"Failed to resolve variable in template '{template_str}': {str(e)}. "
                f"Available variables: {available}"
            )

        # Save to file
        # For test compatibility, don't use output directory by default
        output_path = resolve_path(workspace, output_file, use_output_dir=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered)

        return str(output_path)

    except ValueError as e:
        raise TemplateError(str(e))
    except IOError as e:
        raise TemplateError(f"Failed to write output file '{output_file}': {str(e)}")
    except Exception as e:
        if not isinstance(e, TemplateError):
            raise TemplateError(f"Failed to process template: {str(e)}")
        raise
