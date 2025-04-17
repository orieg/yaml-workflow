from pathlib import Path
from typing import Any, Dict

from ..exceptions import TaskExecutionError
from . import TaskConfig, register_task


@register_task("noop")
def noop_task(config: TaskConfig) -> Dict[str, Any]:
    """A no-operation task that demonstrates the task interface.

    This task simply returns its processed inputs and can optionally fail
    if the 'should_fail' input is set to true. It also demonstrates the use
    of Jinja2 instructions for complex template logic.

    Args:
        config: The task configuration object

    Returns:
        Dict containing the processed inputs and task metadata

    Raises:
        TaskExecutionError: If should_fail is True

    Example YAML usage:
        ```yaml
        steps:
          - name: example_noop
            task: noop
            inputs:
              message: "Hello {{ args.user_name }}"
              conditional_message: |
                {% if args.debug %}
                Debug mode is ON
                {% else %}
                Debug mode is OFF
                {% endif %}
              list_processing: |
                {% for item in args["items"] %}
                Item {{ loop.index }}: {{ item }}
                {% endfor %}
        ```
    """
    # Process inputs with template resolution
    processed = config.process_inputs()

    # Demonstrate error handling if should_fail is True
    if processed.get("should_fail", False):
        raise TaskExecutionError(
            step_name=config.name, original_error=Exception("Task failed as requested")
        )

    # Return processed inputs and some metadata to demonstrate output handling
    return {
        "processed_inputs": processed,
        "task_name": config.name,
        "task_type": config.type,
        "available_variables": config.get_available_variables(),
    }
