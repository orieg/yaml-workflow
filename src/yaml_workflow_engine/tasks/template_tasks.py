"""Template-based task handlers."""

from pathlib import Path
from typing import Any, Dict

from jinja2 import Template

from . import register_task
from ..workspace import resolve_path

@register_task("template")
def render_template(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> str:
    """
    Render a template and save it to a file.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        str: Path to the output file
    """
    # Get template and output path
    template_str = step.get("template")
    if not template_str:
        raise ValueError("No template provided")
    
    output_file = step.get("output")
    if not output_file:
        raise ValueError("No output file specified")
    
    # Render template
    template = Template(template_str)
    rendered = template.render(**context)
    
    # Save to file
    output_path = resolve_path(workspace, output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    
    return str(output_path) 