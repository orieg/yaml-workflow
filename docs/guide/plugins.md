# Plugin Authoring Guide

yaml-workflow supports plugins via Python entry points. Install a plugin package and its tasks become available in any workflow — no configuration needed.

## How Plugins Work

1. A plugin is a regular Python package that defines task functions with `@register_task()`
2. The plugin's `pyproject.toml` declares an entry point in the `yaml_workflow.tasks` group
3. When yaml-workflow starts, it discovers and loads all installed plugins automatically

## Creating a Plugin

### 1. Project Structure

```
yaml-workflow-my-plugin/
  pyproject.toml
  src/
    my_plugin/
      __init__.py
      tasks.py
```

### 2. Define Tasks (`src/my_plugin/tasks.py`)

```python
from typing import Any, Dict
from yaml_workflow.tasks import TaskConfig, register_task


@register_task("my_plugin.greet")
def greet_task(config: TaskConfig) -> Dict[str, Any]:
    """A custom greeting task."""
    processed = config.process_inputs()
    name = processed.get("name", "World")
    style = processed.get("style", "friendly")

    if style == "formal":
        greeting = f"Good day, {name}."
    else:
        greeting = f"Hey {name}!"

    return {"greeting": greeting}


@register_task("my_plugin.transform")
def transform_task(config: TaskConfig) -> Dict[str, Any]:
    """Transform data from a previous step."""
    processed = config.process_inputs()
    data = processed.get("data", "")
    operation = processed.get("operation", "upper")

    if operation == "upper":
        result = data.upper()
    elif operation == "lower":
        result = data.lower()
    elif operation == "reverse":
        result = data[::-1]
    else:
        result = data

    return {"result": result}
```

### 3. Configure Entry Point (`pyproject.toml`)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yaml-workflow-my-plugin"
version = "0.1.0"
description = "Custom tasks for yaml-workflow"
requires-python = ">=3.10"
dependencies = [
    "yaml-workflow>=0.6.0",
]

[project.entry-points."yaml_workflow.tasks"]
my_plugin = "my_plugin.tasks"
```

The key line is the entry point declaration. The format is:

```
[project.entry-points."yaml_workflow.tasks"]
<name> = "<module_path>"
```

- `<name>`: Any unique identifier for your plugin
- `<module_path>`: The Python module to import (importing it triggers `@register_task`)

### 4. Install and Use

```bash
# Install in development mode
pip install -e ./yaml-workflow-my-plugin

# Use in a workflow
```

```yaml
name: Using Plugin Tasks
steps:
  - name: greet_user
    task: my_plugin.greet
    inputs:
      name: "{{ args.user }}"
      style: formal

  - name: transform_greeting
    task: my_plugin.transform
    inputs:
      data: "{{ steps.greet_user.result.greeting }}"
      operation: upper
```

## Task Development Patterns

### Accessing the Full Context

```python
@register_task("my_plugin.context_aware")
def context_aware_task(config: TaskConfig) -> Dict[str, Any]:
    processed = config.process_inputs()

    # Access namespaces
    args = config.context.get("args", {})
    env = config.context.get("env", {})
    steps = config.context.get("steps", {})

    # Access workspace for file operations
    workspace = config.workspace

    return {"result": "done"}
```

### Error Handling

```python
from yaml_workflow.exceptions import TaskExecutionError
from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error
from yaml_workflow.tasks.base import get_task_logger, log_task_execution

@register_task("my_plugin.safe_task")
def safe_task(config: TaskConfig) -> Dict[str, Any]:
    task_name = str(config.name or "safe_task")
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config.context, config.workspace)

    try:
        processed = config.process_inputs()
        # ... task logic ...
        return {"result": "ok"}
    except (ValueError, OSError) as e:
        context = ErrorContext(
            step_name=task_name,
            task_type="my_plugin.safe_task",
            error=e,
            task_config=config.step,
            template_context=config.context,
        )
        handle_task_error(context)
        return {}  # unreachable
```

### Simple Tasks with Auto-Mapping

For simple tasks, the decorator can auto-map inputs to function parameters:

```python
@register_task("my_plugin.add")
def add(a: int, b: int) -> int:
    """Add two numbers. Inputs 'a' and 'b' are auto-mapped from YAML."""
    return a + b
```

```yaml
- name: calculate
  task: my_plugin.add
  inputs:
    a: 10
    b: 20
# Result: steps.calculate.result = 30
```

## Naming Conventions

- Use a namespace prefix for your tasks: `my_plugin.task_name`
- This avoids conflicts with built-in tasks and other plugins
- If two plugins register the same name, the last one loaded wins

## Testing Your Plugin

```python
# tests/test_my_tasks.py
from pathlib import Path
from yaml_workflow.tasks import TaskConfig, get_task_handler

def test_greet_task(tmp_path):
    # Ensure the plugin is loaded
    import my_plugin.tasks  # noqa: F401

    handler = get_task_handler("my_plugin.greet")
    assert handler is not None

    step = {"name": "test", "task": "my_plugin.greet", "inputs": {"name": "Alice"}}
    context = {"args": {}, "env": {}, "steps": {}}
    config = TaskConfig(step, context, tmp_path)

    result = handler(config)
    assert "Alice" in result["greeting"]
```

## Publishing

```bash
# Build
python -m build

# Upload to PyPI
twine upload dist/*

# Users install with:
pip install yaml-workflow-my-plugin
```

Once installed, the tasks are immediately available — no configuration needed.
