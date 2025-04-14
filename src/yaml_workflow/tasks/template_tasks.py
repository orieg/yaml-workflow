"""Template-based task handlers."""

from pathlib import Path
from typing import Any, Dict

from jinja2 import StrictUndefined, Template, UndefinedError

from ..workspace import resolve_path
from . import register_task


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
        ValueError: If template or output file is not specified
        UndefinedError: If template contains undefined variables
    """
    # Get template and output path
    template_str = step.get("template")
    if not template_str:
        raise ValueError("No template provided")

    output_file = step.get("output")
    if not output_file:
        raise ValueError("No output file specified")

    # Render template with strict undefined handling
    template = Template(template_str, undefined=StrictUndefined)
    try:
        rendered = template.render(**context)
    except UndefinedError as e:
        raise ValueError(f"Template error: {str(e)}")

    # Save to file
    # For test compatibility, don't use output directory by default
    output_path = resolve_path(workspace, output_file, use_output_dir=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)

    return str(output_path)
