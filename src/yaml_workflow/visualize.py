"""Workflow visualization utilities."""

from typing import Optional


def generate_mermaid(workflow: dict, flow: Optional[str] = None) -> str:
    """Generate a Mermaid diagram string from a parsed workflow dict.

    Args:
        workflow: Parsed workflow dictionary containing 'steps' and optionally 'flows'.
        flow: Optional flow name to determine step ordering.

    Returns:
        A Mermaid graph TD diagram string.
    """
    # Handle both top-level and nested workflow formats
    if "workflow" in workflow:
        workflow = workflow["workflow"]

    workflow_name = workflow.get("name", "Workflow")
    steps = workflow.get("steps", [])

    # Build a lookup from step name to step dict
    step_map = {step["name"]: step for step in steps}

    # Determine the ordered list of step names
    ordered_names = _get_ordered_step_names(workflow, steps, flow)

    lines = []
    lines.append(f"%% {workflow_name}")
    lines.append("graph TD")

    # Generate node definitions
    for step_name in ordered_names:
        step = step_map.get(step_name)
        if step is None:
            continue
        task_type = step.get("task", "unknown")
        label = f"{step_name}<br/><small>{task_type}</small>"
        if "condition" in step:
            lines.append(f'    {step_name}{{"{label}"}}')
        else:
            lines.append(f'    {step_name}["{label}"]')

    # Generate sequential edges
    for i in range(len(ordered_names) - 1):
        current = ordered_names[i]
        next_step = ordered_names[i + 1]
        # Only add edge if both steps exist in step_map
        if current in step_map and next_step in step_map:
            lines.append(f"    {current} --> {next_step}")

    # Generate error edges
    for step_name in ordered_names:
        step = step_map.get(step_name)
        if step is None:
            continue
        on_error = step.get("on_error")
        if isinstance(on_error, dict):
            error_next = on_error.get("next")
            if error_next and error_next in step_map:
                lines.append(f"    {step_name} -.->|error| {error_next}")

    return "\n".join(lines)


def _get_ordered_step_names(workflow, steps, flow):
    """Determine the ordered list of step names based on flow configuration.

    Args:
        workflow: The full workflow dict.
        steps: The list of step dicts.
        flow: Optional flow name to use for ordering.

    Returns:
        A list of step name strings in execution order.
    """
    flows_section = workflow.get("flows")

    if flow and flows_section:
        definitions = flows_section.get("definitions", [])
        for flow_def in definitions:
            if isinstance(flow_def, dict) and flow in flow_def:
                return list(flow_def[flow])
    elif flows_section and not flow:
        # Use default flow if defined and no explicit flow requested
        default_flow_name = flows_section.get("default")
        if default_flow_name:
            definitions = flows_section.get("definitions", [])
            for flow_def in definitions:
                if isinstance(flow_def, dict) and default_flow_name in flow_def:
                    return list(flow_def[default_flow_name])

    # Fallback: use step order as defined
    return [step["name"] for step in steps]
