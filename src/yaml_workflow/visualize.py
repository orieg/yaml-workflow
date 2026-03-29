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

    Uses unicode box-drawing for regular steps and diamond shapes for
    conditional steps, with proper connectors and error path annotations.

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

    # Calculate widths
    max_name = max((len(n) for n in ordered_names), default=8)
    max_task = max(
        (len(step_map.get(n, {}).get("task", "")) for n in ordered_names), default=4
    )
    box_w = max(max_name, max_task, 10)  # inner content width

    lines: List[str] = []
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
        step_errors = [target for src, target in error_edges if src == name]

        if has_condition:
            _render_diamond(lines, name, task_type, box_w, step_errors)
        else:
            _render_box(lines, name, task_type, box_w, step_errors)

        # Draw connector to next step
        if i < len(ordered_names) - 1:
            mid = box_w // 2 + 4
            lines.append(" " * mid + "\u2502")
            lines.append(" " * mid + "\u25bc")

    # Summary
    lines.append("")
    total = len(ordered_names)
    conditional = sum(1 for n in ordered_names if "condition" in step_map.get(n, {}))
    lines.append(
        f"  {total} steps ({conditional} conditional, {total - conditional} always-run)"
    )
    if error_edges:
        lines.append(
            f"  {len(error_edges)} error path(s): "
            + ", ".join(f"{s} \u2192 {t}" for s, t in error_edges)
        )

    return "\n".join(lines)


def _render_box(
    lines: List[str],
    name: str,
    task_type: str,
    width: int,
    error_targets: List[str],
) -> None:
    """Render a rectangular box node using unicode box-drawing characters."""
    w = width + 2  # padding
    top = "  \u250c" + "\u2500" * w + "\u2510"
    bot = "  \u2514" + "\u2500" * w + "\u2518"
    name_line = "  \u2502" + name.center(w) + "\u2502"
    task_line = "  \u2502" + task_type.center(w) + "\u2502"

    lines.append(top)
    lines.append(name_line)
    lines.append(task_line)

    if error_targets:
        bot_with_err = (
            bot + "  \u2500\u2500error\u2500\u25b6 [" + error_targets[0] + "]"
        )
        lines.append(bot_with_err)
    else:
        lines.append(bot)


def _render_diamond(
    lines: List[str],
    name: str,
    task_type: str,
    width: int,
    error_targets: List[str],
) -> None:
    """Render a diamond-shaped node for conditional steps."""
    w = width + 2  # padding
    half = w // 2

    # Diamond top
    lines.append(" " * (half + 3) + "\u25c7")
    # Top half: /    \
    lines.append(" " * 3 + "\u2571" + name.center(w) + "\u2572")
    # Middle: <  task  >
    lines.append("  \u25c1" + task_type.center(w + 2) + "\u25b7")
    # Bottom half: \    /
    bot_line = " " * 3 + "\u2572" + " " * w + "\u2571"
    if error_targets:
        bot_line += "  \u2500\u2500error\u2500\u25b6 [" + error_targets[0] + "]"
    lines.append(bot_line)
    # Diamond bottom
    lines.append(" " * (half + 3) + "\u25c7")


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
