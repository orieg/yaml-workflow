# Task Development Guide

This guide provides instructions and best practices for creating new custom tasks for the YAML Workflow engine.

## Creating New Tasks

### Core Concepts

- **Task Function:** The main Python function that executes the task logic.
- **`@register_task` Decorator:** Used to register the task function with the engine.
- **`TaskConfig` Object:** Passed to the task function, providing access to step configuration, context, and workspace.

### Steps

1.  **Define the Task Function:**
    - Create a Python function that accepts a single argument: `config: TaskConfig`.
    - Implement the core logic of your task within this function.
    - Access inputs using `config.process_inputs()` which resolves templates.
    - Use `config.workspace` (a `Path` object) for file operations within the workflow run directory.
    - Access workflow context (parameters, outputs from previous steps) via `config._context`.
    - Return a dictionary containing the task's results, or `None` if there's no specific output.

2.  **Register the Task:**
    - Import the `@register_task` decorator: `from yaml_workflow.tasks import register_task`.
    - Apply the decorator to your task function: `@register_task("your_task_name")`.
    - The string argument is the `task:` name used in the YAML workflow definition.

3.  **Handle Inputs:**
    - Use `processed_inputs = config.process_inputs()` to get a dictionary of inputs with templates already resolved.
    - Access specific inputs like `processed_inputs.get("my_input")`.
    - Perform necessary validation on the inputs.

4.  **Implement Task Logic:**
    - Perform the actions required by the task (e.g., API calls, file manipulation, calculations).
    - Use the provided `config.workspace` for any file I/O related to the workflow run.
    - Log information using the task-specific logger (see Error Handling section).

5.  **Return Results:**
    - Return a dictionary containing key outputs of the task. Common keys include `result` or specific named outputs.
    - This dictionary will be stored in the workflow state under `steps.your_step_name`.
    - The engine can map outputs to the main context if the `outputs:` key is used in the YAML step definition.

### Example

```python
# src/my_custom_tasks/greeting_task.py
from pathlib import Path
from typing import Any, Dict, Optional

from yaml_workflow.tasks import TaskConfig, register_task
from yaml_workflow.tasks.base import get_task_logger, log_task_execution, log_task_result
from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error

@register_task("custom_greet")
def custom_greeting_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """A custom task that generates a greeting."""
    task_name = str(config.name or "custom_greet")
    task_type = config.type or "custom_greet"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)

    try:
        processed = config.process_inputs()
        name = processed.get("name", "World")
        prefix = processed.get("prefix", "Hello")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Input 'name' must be a non-empty string")

        greeting = f"{prefix}, {name.strip()}!"

        # Example of writing to a file in the workspace
        output_file = config.workspace / f"greeting_{task_name}.txt"
        output_file.write_text(greeting)

        result = {"greeting_message": greeting, "output_file": str(output_file)}
        log_task_result(logger, result)
        return result

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None # Or re-raise depending on desired flow
```

## Wrapping Existing Functions

Often, you might have existing Python functions that you want to expose as workflow tasks, but their function signatures don't match the required `(config: TaskConfig)` format. You can easily integrate these functions by creating a simple wrapper task.

The wrapper task function will:

1.  Accept the standard `config: TaskConfig` argument.
2.  Be decorated with `@register_task("your_wrapper_task_name")`.
3.  Use `config.process_inputs()` to get the inputs defined in the YAML step.
4.  Extract values from the `processed_inputs` dictionary and map them to the arguments expected by your original function.
5.  Call your original function with the mapped arguments.
6.  Optionally process the return value of your original function into a dictionary suitable for the workflow context.
7.  Include standard error handling using `handle_task_error`.

### Example: Wrapping a Calculation Function

Let's say you have an existing utility function:

```python
# my_utils/calculations.py

def perform_complex_calculation(x: float, y: float, operation: str = 'add') -> float:
    """Performs a calculation based on the operation."""
    if operation == 'add':
        return x + y
    elif operation == 'multiply':
        return x * y
    else:
        raise ValueError(f"Unsupported operation: {operation}")

```

Here's how you can create a wrapper task to use it in a workflow:

```python
# src/my_custom_tasks/calculation_task.py
from typing import Any, Dict, Optional

from yaml_workflow.tasks import TaskConfig, register_task
from yaml_workflow.tasks.base import get_task_logger, log_task_execution, log_task_result
from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error

# Import the existing function
from my_utils.calculations import perform_complex_calculation

@register_task("calculate")
def calculation_wrapper_task(config: TaskConfig) -> Optional[Dict[str, Any]]:
    """A wrapper task to perform calculations using an existing function."""
    task_name = str(config.name or "calculate")
    task_type = config.type or "calculate"
    logger = get_task_logger(config.workspace, task_name)
    log_task_execution(logger, config.step, config._context, config.workspace)

    try:
        processed = config.process_inputs()

        # Extract and validate inputs for the original function
        val1 = processed.get("value1")
        val2 = processed.get("value2")
        op = processed.get("operation", "add") # Default defined here or in original func

        if val1 is None or val2 is None:
            raise ValueError("Inputs 'value1' and 'value2' are required")
        try:
            num1 = float(val1)
            num2 = float(val2)
        except ValueError:
            raise ValueError("Inputs 'value1' and 'value2' must be numbers")
        if not isinstance(op, str):
             raise ValueError("Input 'operation' must be a string")

        # Call the original function
        calculation_result = perform_complex_calculation(x=num1, y=num2, operation=op)

        # Format the result for the workflow
        result = {"calculation_output": calculation_result}
        log_task_result(logger, result)
        return result

    except Exception as e:
        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return None
```

**YAML Usage:**

```yaml
steps:
  - name: add_numbers
    task: calculate
    inputs:
      value1: 10
      value2: 5
      operation: add # Optional, defaults to 'add'
    outputs: calculation_result # Maps result["calculation_output"] to context.calculation_result

  - name: multiply_numbers
    task: calculate
    inputs:
      value1: "{{ steps.add_numbers.calculation_output }}" # Use previous result
      value2: 2
      operation: multiply
```

## Using TaskConfig Effectively

- **`config.step`**: The raw dictionary definition of the step from the YAML.
- **`config.name`**: The `name:` defined for the step in the YAML.
- **`config.type`**: The `task:` type defined for the step in the YAML.
- **`config.workspace`**: A `pathlib.Path` object pointing to the root of the current workflow run's workspace.
- **`config._context`**: The full workflow context dictionary (includes `args`, `env`, `steps` namespaces).
- **`config.process_inputs()`**: Resolves Jinja2 templates in the `inputs:` section of the step definition using `config._context` and returns the processed dictionary.

## Error Handling Best Practices

- **Use Centralized Handling:** Import and use the `handle_task_error` utility for consistent error logging and propagation.
- **Wrap Exceptions:** Catch specific exceptions within your task logic and use `handle_task_error` within the `except` block.
- **`ErrorContext`:** Populate the `ErrorContext` dataclass with relevant details (step name, task type, original error, config, context) before passing it to `handle_task_error`.
- **Standard Logging:** Use `get_task_logger`, `log_task_execution`, and `log_task_result` from `yaml_workflow.tasks.base` for standardized logging.

```python
from yaml_workflow.tasks.base import get_task_logger, log_task_execution, log_task_result
from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error

# ... inside your task function ...
task_name = str(config.name or "default_name")
task_type = config.type or "default_type"
logger = get_task_logger(config.workspace, task_name)
log_task_execution(logger, config.step, config._context, config.workspace)

try:
    # --- Your task logic --- 
    processed = config.process_inputs()
    # ... access inputs ...
    if some_condition:
        raise ValueError("Specific validation failed")
    # ... perform actions ...
    result = { ... }
    log_task_result(logger, result)
    return result
except Exception as e:
    context = ErrorContext(
        step_name=task_name,
        task_type=task_type,
        error=e,
        task_config=config.step,       # Pass the raw step config
        template_context=config._context # Pass the full context
    )
    handle_task_error(context)
    # handle_task_error raises by default, so this point might not be reached
    # unless handle_task_error is modified or the raised error is caught again.
    return None # Or handle differently if needed
```

## Type Safety Guidelines

- Use type hints (`typing` module) for your task function signature and internal variables.
- Ensure your task function has a return type hint (e.g., `-> Optional[Dict[str, Any]]`, `-> str`, `-> None`).
- Add a `py.typed` file to your package root if distributing the custom tasks as a library, allowing `mypy` to check types.
- Run `mypy` as part of your quality checks.

## Testing Requirements

- Write unit tests for your task function's logic.
- Mock external dependencies (APIs, complex file interactions) where appropriate.
- Test different input scenarios, including valid and invalid inputs.
- Test error conditions and ensure errors are handled correctly (e.g., using `pytest.raises`).
- Consider creating small example workflow YAML files that use your custom task and test them using `WorkflowEngine` or the CLI runner within integration tests.

```python
# Example test structure (using pytest)
import pytest
from pathlib import Path
from yaml_workflow.tasks import TaskConfig
from my_custom_tasks.greeting_task import custom_greeting_task # Import your task

@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    return tmp_path

@pytest.fixture
def sample_task_config(temp_workspace: Path) -> TaskConfig:
    step = {
        "name": "test_greet",
        "task": "custom_greet",
        "inputs": {
            "name": "Tester",
            "prefix": "Hi"
        }
    }
    context = { # Mock context
        "args": {},
        "env": {},
        "steps": {}
    }
    return TaskConfig(step, context, temp_workspace)

def test_custom_greeting_success(sample_task_config: TaskConfig):
    """Test successful execution of the custom greeting task."""
    result = custom_greeting_task(sample_task_config)
    assert result is not None
    assert result["greeting_message"] == "Hi, Tester!"
    assert "output_file" in result
    assert Path(result["output_file"]).exists()
    assert Path(result["output_file"]).read_text() == "Hi, Tester!"

def test_custom_greeting_invalid_input(sample_task_config: TaskConfig):
    """Test the task with invalid input."""
    sample_task_config.step["inputs"]["name"] = "" # Invalid empty name
    
    # Assuming handle_task_error raises TaskExecutionError wrapping the ValueError
    from yaml_workflow.exceptions import TaskExecutionError
    with pytest.raises(TaskExecutionError) as exc_info:
        custom_greeting_task(sample_task_config)
    
    # Check the original error type
    assert isinstance(exc_info.value.original_error, ValueError)
    assert "Input 'name' must be a non-empty string" in str(exc_info.value.original_error)

``` 