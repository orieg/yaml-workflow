# Development Guide

## Setup

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Format code:
```bash
# Format Python files
black src/ tests/  # Code formatting
isort --profile black src/ tests/  # Import sorting (using black-compatible settings)

# Run both formatters in one command
black src/ tests/ && isort --profile black src/ tests/
```

3. Type checking:
```bash
mypy src/
```

## Task Development

### TaskConfig Interface

All tasks in YAML Workflow use the `TaskConfig` interface for standardized configuration and error handling:

```python
from yaml_workflow.tasks import register_task, TaskConfig
from yaml_workflow.exceptions import TaskExecutionError

@register_task("my_task")
def my_task_handler(config: TaskConfig) -> Dict[str, Any]:
    """
    Task implementation using TaskConfig.
    
    Args:
        config: TaskConfig object containing:
               - name: Task name
               - type: Task type
               - inputs: Task inputs
               - workspace: Workspace path
               - _context: Variable context
    
    Returns:
        Dict containing:
        - result: Task result
        - task_name: Name of the task
        - task_type: Type of task
        - available_variables: Variables accessible to the task
    """
    try:
        # Process inputs with template resolution
        processed = config.process_inputs()
        
        # Access variables from different namespaces
        input_value = config.get_variable('value', namespace='args')
        env_var = config.get_variable('API_KEY', namespace='env')
        
        # Access batch context if available
        batch_ctx = config.get_variable('item', namespace='batch')
        
        # Perform task logic
        result = process_data(input_value, env_var)
        
        return {
            "result": result,
            "task_name": config.name,
            "task_type": config.type,
            "available_variables": config.get_available_variables()
        }
    except Exception as e:
        raise TaskExecutionError(
            message=f"Task failed: {str(e)}",
            step_name=config.name,
            original_error=e
        )
```

### Error Handling

Tasks should use standardized error handling through `TaskExecutionError`:

```python
from yaml_workflow.exceptions import TaskExecutionError

def process_with_error_handling(config: TaskConfig) -> Dict[str, Any]:
    try:
        # Process task
        result = process_data()
        return {"result": result}
    except ValueError as e:
        raise TaskExecutionError(
            message="Invalid input data",
            step_name=config.name,
            original_error=e
        )
    except IOError as e:
        raise TaskExecutionError(
            message="Failed to read/write data",
            step_name=config.name,
            original_error=e
        )
    except Exception as e:
        raise TaskExecutionError(
            message=f"Unexpected error: {str(e)}",
            step_name=config.name,
            original_error=e
        )
```

### Template Resolution

Tasks should use `config.process_inputs()` for template resolution:

```python
@register_task("template_task")
def template_task_handler(config: TaskConfig) -> Dict[str, Any]:
    # Process inputs with template resolution
    processed = config.process_inputs()
    
    # Access resolved values
    template = processed.get("template")
    variables = processed.get("variables", {})
    
    try:
        # Use resolved values
        result = render_template(template, variables)
        return {"result": result}
    except Exception as e:
        raise TaskExecutionError(
            message="Template rendering failed",
            step_name=config.name,
            original_error=e
        )
```

### Batch Processing

Tasks can access batch context when used in batch operations:

```python
@register_task("batch_aware_task")
def batch_aware_task_handler(config: TaskConfig) -> Dict[str, Any]:
    # Get batch context if available
    batch_item = config.get_variable('item', namespace='batch')
    batch_index = config.get_variable('index', namespace='batch')
    batch_total = config.get_variable('total', namespace='batch')
    
    if batch_item is not None:
        # We're in a batch context
        print(f"Processing item {batch_index + 1}/{batch_total}")
        result = process_batch_item(batch_item)
    else:
        # Regular task execution
        result = process_single_item()
    
    return {"result": result}
```

### Testing Tasks

Create comprehensive tests for tasks:

```python
def test_my_task():
    # Create test config
    config = TaskConfig(
        name="test_task",
        task_type="my_task",
        inputs={
            "value": "test_value",
            "api_key": "test_key"
        },
        context={
            "args": {"value": "test_value"},
            "env": {"API_KEY": "test_key"},
            "steps": {}
        },
        workspace=Path("/tmp/test")
    )
    
    # Execute task
    result = my_task_handler(config)
    
    # Verify result
    assert result["task_name"] == "test_task"
    assert result["task_type"] == "my_task"
    assert "result" in result
    
    # Test error handling
    config.inputs["value"] = None
    with pytest.raises(TaskExecutionError) as exc_info:
        my_task_handler(config)
    assert "Invalid input" in str(exc_info.value)
```

## Building and Distribution

1. Ensure you have the latest build tools:
```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build twine
```

2. Build both source distribution (sdist) and wheel:
```bash
# This will create both sdist and wheel in the dist/ directory
python -m build

# Or build them separately:
python -m build --sdist  # Create source distribution
python -m build --wheel  # Create wheel
```

3. Check your distribution files:
```bash
# Validate distribution files
twine check dist/*
```

4. Upload to TestPyPI first (recommended):
```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ yaml-workflow
```

5. Upload to PyPI:
```bash
# Upload to PyPI
twine upload dist/*
```

## Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=yaml_workflow
```

## Testing Releases

### Method 1: Local Build Testing

1. Install development dependencies (includes build tools):
```bash
# This will install all development dependencies including build and twine
pip install -e ".[dev]"
```

2. Clean previous builds:
```bash
rm -rf dist/ build/ *.egg-info
```

3. Build the package:
```bash
python -m build
```

4. Check the distribution files:
```bash
twine check dist/*
```

5. Install the built package locally:
```bash
# Create a new virtual environment for testing
python -m venv test-venv
source test-venv/bin/activate  # On Unix/macOS
# On Windows use: test-venv\Scripts\activate

# Install and test the package
pip install dist/*.whl
yaml-workflow init --example hello_world
yaml-workflow run workflows/hello_world.yaml name=Test
```

### Method 2: Using TestPyPI

1. Register an account on TestPyPI:
   - Go to https://test.pypi.org/account/register/
   - Create an account
   - Generate an API token

2. Create a `.pypirc` file in your home directory:
```ini
[distutils]
index-servers =
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = your-test-pypi-token
```

3. Build and upload to TestPyPI:
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build

# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

4. Test installation from TestPyPI:
```bash
# Create a new virtual environment for testing
python -m venv test-venv
source test-venv/bin/activate  # On Unix/macOS
# On Windows use: test-venv\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    yaml-workflow

# Test the package
yaml-workflow init --example hello_world
yaml-workflow run workflows/hello_world.yaml name=Test
```

Note: The `--extra-index-url` is needed because TestPyPI doesn't have all the dependencies.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure all checks pass
5. Submit a pull request

## Package Configuration

The package uses `pyproject.toml` for configuration. Here's the minimum required configuration:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yaml-workflow"
version = "0.1.0"
description = "A powerful and flexible workflow engine that executes tasks defined in YAML configuration files"
readme = "README.md"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
license = { file = "LICENSE" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyyaml>=6.0",
    "jinja2>=3.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
dev = [
    "black>=23.0",
    "isort>=5.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/yaml-workflow"
Issues = "https://github.com/yourusername/yaml-workflow/issues"

[project.scripts]
yaml-workflow = "yaml_workflow.cli:main"

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88  # Match black's line length
```

## Creating Custom Tasks

The workflow engine allows you to extend its functionality by creating custom tasks written in Python. This guide covers the recommended way to define and register your own tasks.

### Using the `@register_task` Decorator

The simplest and preferred way to create a custom task is by using the `@register_task` decorator found in `yaml_workflow.tasks`.

Below is a brief example. For the full runnable code, see:
*   Python task definitions: `docs/examples/custom_tasks/my_tasks.py`
*   Example workflow YAML: `docs/examples/custom_tasks/workflow.yaml`

```python
# Example snippet from docs/examples/custom_tasks/my_tasks.py
from yaml_workflow.tasks import register_task, TaskConfig
import logging

@register_task() # Register with default name 'multiply_by'
def multiply_by(value: int, multiplier: int = 2) -> int:
    logging.info(f"Task 'multiply_by': Multiplying {value} by {multiplier}")
    return value * multiplier

@register_task("custom_greeting") # Register with custom name
def create_special_greeting(name: str) -> str:
    # ... implementation ...
    return f"✨ Special Greeting for {name}! ✨"

# ... other examples including using TaskConfig ...
```

**Key Concepts:**

1.  **Registration:**
    *   Import `register_task` from `yaml_workflow.tasks`.
    *   Decorate your Python function with `@register_task()`.
    *   By default, the task name used in the YAML workflow will be the function name (e.g., `multiply_by`).
    *   You can provide a custom name: `@register_task("custom_name")`.

2.  **Input Handling (Automatic):**
    *   The decorator automatically handles mapping inputs defined in your YAML step to the function's parameters.
    *   Define parameters in your function signature with type hints (e.g., `value: int`, `multiplier: int = 2`).
    *   Inputs are automatically processed using the template engine (e.g., `value: "{{ steps.previous.result }}"`).
    *   Default values for arguments work as expected.

3.  **Accessing `TaskConfig` (Optional):**
    *   If your task needs access to the full context, workspace details, or other metadata, simply include `config: TaskConfig` as a parameter in your function definition.
    *   The decorator will detect this and pass the `TaskConfig` object to your function. You **do not** need to provide `config` in the YAML inputs.
    *   You can mix specific arguments and the `config` parameter.

4.  **Return Values:**
    *   Tasks can return any Python object (strings, numbers, lists, dictionaries, etc.).
    *   The returned value is automatically wrapped and stored in the context under `steps.YOUR_STEP_NAME.result`.
    *   Subsequent steps can access this result using templates like `{{ steps.YOUR_STEP_NAME.result }}`. If the result is a dictionary, access specific keys like `{{ steps.YOUR_STEP_NAME.result.key }}`.

5.  **Error Handling:**
    *   Standard Python exceptions raised within your task will be caught by the engine and will typically cause the workflow to fail (unless `on_error` is configured for the step).
    *   For more controlled error handling specific to the workflow engine (e.g., custom error types recognized by `on_error` logic), you can import and raise exceptions from `yaml_workflow.exceptions`.

6.  **Discovery:**
    *   Ensure the Python module containing your decorated task functions is imported somewhere in your project *before* the workflow runs, so the decorators execute and register the tasks. A common pattern is to import them in your project's main `__init__.py` or a dedicated `tasks.py` module that is imported early.

### Example YAML Usage

This snippet shows how the custom tasks defined above might be used in a workflow. See `docs/examples/custom_tasks/workflow.yaml` for the complete runnable example.

```yaml
# Example snippet from docs/examples/custom_tasks/workflow.yaml
steps:
  - name: multiply_step
    task: multiply_by # Uses the function name
    inputs:
      value: "{{ args.initial_value | default(10) }}"
      multiplier: 5 # Override default

  - name: show_multiply_result
    task: echo # Use a built-in task to show the result
    inputs:
      message: "Multiplication Result: {{ steps.multiply_step.result }}"

  - name: greeting_step
    task: custom_greeting # Uses the custom registered name
    inputs:
      name: "{{ args.user_name | default('Example User') }}"

  # ... other steps using process_with_config ...
``` 