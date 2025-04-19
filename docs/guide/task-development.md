# Task Development Guide

This guide provides instructions and best practices for developing custom tasks for the YAML Workflow engine.

## Creating New Tasks

- **Using `TaskConfig`**: Understand how to access parameters, context, and workspace information via the `TaskConfig` object passed to your task function.
- **Task Registration**: Use the `@register_task("your_task_name")` decorator to make your task available in workflow YAML files.
- **Type Safety**: Utilize Python type hints for function arguments and return values to improve clarity and enable static analysis.
- **Logging**: Use `get_task_logger` from `yaml_workflow.tasks.base` to get a logger specific to the task instance.
- **Path Handling**: If your task deals with file paths provided in `inputs`, use the `config.workspace` attribute and standard `pathlib` operations (`config.workspace / relative_path`) to resolve paths. Assume relative paths are relative to the workspace root. Avoid hardcoding subdirectories like `output/` unless intrinsic to the task's core function.

## Returning Results

Tasks should return the primary output they generate. This could be a single value (like a string, number, boolean) or a dictionary containing multiple related output values.

The workflow engine consistently stores the *entire* return value of a task under the `result` key within the `steps` namespace for the executed step. This provides a predictable access pattern regardless of the return type.

## Accessing Previous Step Outputs

Always use the `steps` namespace in your Jinja2 templates within task `inputs` to access the results of previously executed steps. 

- **Primary Output**: Access the complete result returned by the previous step using `{{ steps.STEP_NAME.result }}`.
  - If the step returned a single value (e.g., a string), this will be the value itself.
  - If the step returned a dictionary (e.g., `{"stdout": "output", "code": 0}`), this will be the dictionary.

- **Dictionary Keys**: If the previous step returned a dictionary, access specific keys within that dictionary using `{{ steps.STEP_NAME.result.KEY }}`.
  ```yaml
  steps:
    - name: my_shell_step
      task: shell
      inputs:
        command: "ls -l"
      # Shell task returns a dict: {"stdout": ..., "stderr": ..., "return_code": ...}
      
    - name: my_echo
      task: echo
      inputs:
        message: "Hello"
      # Echo task returns a string: "Hello"
      
    - name: use_results
      task: some_other_task
      inputs:
        # Access stdout from the shell step's result dictionary
        shell_stdout: "{{ steps.my_shell_step.result.stdout }}"
        # Access the return code from the shell step's result dictionary
        shell_code: "{{ steps.my_shell_step.result.return_code }}"
        
        # Access the single string value returned by the echo step
        echo_output: "{{ steps.my_echo.result }}"
  ```

- **Step Status/Error**: Note that step metadata like `status` and `error` are accessed directly on the step object, *not* under the `result` key:
  ```yaml
  condition: "{{ steps.my_shell_step.status == 'completed' }}"
  error_message: "{{ steps.my_shell_step.error }}" # Only available if step failed
  ```

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