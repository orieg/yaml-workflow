"""Workflow visualization utilities."""

from typing import Dict, List, Optional


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


def generate_text(workflow: dict, flow: Optional[str] = None) -> str:
    """Generate an ASCII DAG representation of a workflow.

    Args:
        workflow: Parsed workflow dictionary containing 'steps' and optionally 'flows'.
        flow: Optional flow name to determine step ordering.

    Returns:
        An ASCII text diagram string.
    """
    # Handle both top-level and nested workflow formats
    if "workflow" in workflow:
        workflow = workflow["workflow"]

    workflow_name = workflow.get("name", "Workflow")
    steps = workflow.get("steps", [])
    step_map: Dict[str, dict] = {step["name"]: step for step in steps}
    ordered_names = _get_ordered_step_names(workflow, steps, flow)

    # Collect error edges for display
    error_edges: List[tuple] = []
    for name in ordered_names:
        step = step_map.get(name)
        if step:
            on_error = step.get("on_error")
            if isinstance(on_error, dict) and on_error.get("next"):
                error_edges.append((name, on_error["next"]))

    # Calculate column widths
    max_name = max((len(n) for n in ordered_names), default=8)
    max_task = max(
        (len(step_map.get(n, {}).get("task", "")) for n in ordered_names), default=4
    )
    box_inner = max(max_name, max_task + 2, 12)  # minimum 12 chars

    lines = []
    lines.append(f"  Workflow: {workflow_name}")
    if flow:
        lines.append(f"  Flow: {flow}")
    lines.append("")

    for i, name in enumerate(ordered_names):
        step = step_map.get(name)
        if not step:
            continue
        task_type = step.get("task", "unknown")
        has_condition = "condition" in step

        # Find error edges from this step
        step_errors = [target for src, target in error_edges if src == name]

        # Build the box
        if has_condition:
            # Diamond-style for conditional
            marker = "?"
        else:
            marker = " "

        name_padded = name.center(box_inner)
        task_padded = task_type.center(box_inner)
        border = "+" + "-" * (box_inner + 2) + "+"

        lines.append(f"  {border}")
        lines.append(f"  |{marker}{name_padded} |")
        lines.append(f"  | {task_padded} |")
        lines.append(f"  {border}")

        # Error edge annotation on the right
        if step_errors:
            for target in step_errors:
                lines[-1] = lines[-1] + f"  --error--> [{target}]"

        # Draw connector to next step
        if i < len(ordered_names) - 1:
            mid = box_inner // 2 + 3
            lines.append(" " * mid + "|")
            lines.append(" " * mid + "v")

    # Summary line
    lines.append("")
    total = len(ordered_names)
    conditional = sum(1 for n in ordered_names if "condition" in step_map.get(n, {}))
    lines.append(
        f"  {total} steps ({conditional} conditional, {total - conditional} always-run)"
    )
    if error_edges:
        lines.append(
            f"  {len(error_edges)} error path(s): "
            + ", ".join(f"{s} -> {t}" for s, t in error_edges)
        )

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
