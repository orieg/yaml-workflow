# docs/examples/custom_tasks/my_tasks.py

"""Example custom tasks for documentation."""

import logging

from yaml_workflow.tasks import TaskConfig, register_task

# Configure logging for the tasks module if desired
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


@register_task()
def multiply_by(value: int, multiplier: int = 2) -> int:
    """
    Multiplies the input value by a multiplier.

    Args:
        value: The number to multiply.
        multiplier: The number to multiply by (default: 2).

    Returns:
        The result of the multiplication.
    """
    logging.info(f"Task 'multiply_by': Multiplying {value} by {multiplier}")
    result = value * multiplier
    # logging.info(f"Task 'multiply_by': Result = {result}")
    return result


@register_task("custom_greeting")
def create_special_greeting(name: str) -> str:
    """Creates a special greeting with a custom name."""
    logging.info(f"Task 'custom_greeting': Creating greeting for {name}")
    greeting = f"✨ Special Greeting for {name}! ✨"
    # logging.info(f"Task 'custom_greeting': Result = {greeting}")
    return greeting


@register_task()
def process_with_config(data_key: str, config: TaskConfig) -> str:
    """
    An example task that explicitly uses the TaskConfig object.
    It retrieves data from the full context using the provided key.
    """
    logging.info(
        f"Task 'process_with_config': Accessing context['{data_key}'] via config"
    )
    full_context = config._context
    data_to_process = full_context.get(data_key, "Default Data")
    workspace_path = getattr(config.workspace, "path", config.workspace)
    logging.info(
        f"Task 'process_with_config': Processing data '{data_to_process}' in workspace {workspace_path}"
    )
    # Perform some action...
    result = f"Processed: {data_to_process} (from {data_key})"
    # logging.info(f"Task 'process_with_config': Result = {result}")
    return result


# Note: For these tasks to be discoverable by the workflow engine,
# this module (my_tasks.py) needs to be imported by the Python code
# that *calls* the workflow engine, or by a module that is imported
# early in the execution (like the project's __init__.py).
# For simple testing via the CLI, you might need to adjust PYTHONPATH
# or install the package containing these tasks.
