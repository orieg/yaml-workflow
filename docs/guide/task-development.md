# Task Development Guide

This guide provides instructions and best practices for developing custom tasks for the YAML Workflow engine.

## Creating New Tasks

- **Using `TaskConfig`**: Understand how to access parameters, context, and workspace information via the `TaskConfig` object passed to your task function.
- **Task Registration**: Use the `@register_task("your_task_name")` decorator to make your task available in workflow YAML files.
- **Type Safety**: Utilize Python type hints for function arguments and return values to improve clarity and enable static analysis.
- **Logging**: Use `get_task_logger` from `yaml_workflow.tasks.base` to get a logger specific to the task instance.

## Returning Results

It's crucial that tasks return results in a predictable way so they can be accessed by subsequent steps using the `steps` namespace.

- **Returning Dictionaries**: If your task naturally produces multiple related output values (e.g., stdout, stderr, return code from a shell command), return them as a dictionary. Subsequent steps can access these values directly by key:
  ```yaml
  steps:
    - name: my_shell_step
      task: shell
      inputs:
        command: "ls -l"
    - name: use_output
      task: echo
      inputs:
        message: "Output was: {{ steps.my_shell_step.stdout }}"
  ```

- **Returning Single Values**: If your task produces a single primary result (e.g., a processed string, a calculated number, a boolean flag), return that value directly. The workflow engine will automatically wrap this single value into a dictionary under the key `"result"` within the `steps` namespace.
  ```yaml
  steps:
    - name: my_echo
      task: echo
      inputs:
        message: "Hello"
    - name: use_output
      task: echo
      inputs:
        message: "Echo said: {{ steps.my_echo.result }}"
  ```

## Accessing Previous Step Outputs

Always use the `steps` namespace in your Jinja2 templates within task `inputs` to access the results of previously executed steps. 

- **Syntax**: `{{ steps.STEP_NAME.KEY }}`
  - `STEP_NAME`: The `name` defined for the previous step in the workflow YAML.
  - `KEY`: 
    - The specific key if the previous step returned a dictionary (e.g., `stdout`, `return_code`).
    - Use `result` if the previous step returned a single value (which the engine wraps).

## Error Handling Best Practices

- **Use Centralized Handling**: Import `handle_task_error` and `ErrorContext` from `yaml_workflow.tasks.error_handling`.
- **Wrap Exceptions**: Catch specific exceptions within your task logic. If an error occurs, create an `ErrorContext` instance and pass it to `handle_task_error`. This ensures consistent error logging and propagation.
  ```python
  from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error
  from yaml_workflow.exceptions import TaskExecutionError
  
  try:
      # Your task logic here
      # ...
      if some_error_condition:
          raise ValueError("Something went wrong")
  except Exception as e:
      # Avoid raising TaskExecutionError directly if possible,
      # let handle_task_error wrap it.
      if isinstance(e, TaskExecutionError):
          raise # Re-raise if it's already the correct type
      
      err_context = ErrorContext(
          step_name=config.name, 
          task_type=config.type, 
          error=e, 
          task_config=config.step # Pass the raw step definition
      )
      handle_task_error(err_context) # This will raise TaskExecutionError
  ```
- **Specific Exceptions**: Define custom exception classes inheriting from `TaskExecutionError` for domain-specific errors if needed.

## Testing Requirements

- Write unit tests for your task function's logic.
- Include integration tests that run your task within a minimal workflow to verify:
  - Parameter handling.
  - Correct output structure (dict vs. single value).
  - Accessing its output via the `steps` namespace in a subsequent step.
  - Error handling behavior.

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