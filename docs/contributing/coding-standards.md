# Coding Standards

This document outlines the coding standards and best practices for contributing to the YAML Workflow Engine project.

## Python Code Style

### Code Formatting

We use [Black](https://black.readthedocs.io/) for code formatting and [isort](https://pycqa.github.io/isort/) for import sorting:

```bash
# Format Python files
black src/ tests/

# Sort imports
isort --profile black src/ tests/

# Run both
black src/ tests/ && isort --profile black src/ tests/
```

### Type Hints

Use type hints for all function parameters and return values:

```python
from typing import Dict, List, Optional

def process_data(
    input_data: List[Dict[str, str]],
    batch_size: Optional[int] = None
) -> Dict[str, int]:
    """Process input data and return statistics."""
    results = {}
    # Implementation
    return results
```

### Docstrings

Use Google-style docstrings for all modules, classes, and functions:

```python
def validate_workflow(
    workflow_file: str,
    strict: bool = False
) -> Dict[str, Any]:
    """Validate a workflow file without executing it.

    Args:
        workflow_file: Path to the workflow file to validate.
        strict: Whether to perform strict validation.

    Returns:
        Dict containing validation results.

    Raises:
        ValidationError: If the workflow is invalid.
        FileNotFoundError: If the workflow file doesn't exist.
    """
    # Implementation
```

### Error Handling

1. Use custom exceptions for domain-specific errors:
```python
class WorkflowError(Exception):
    """Base class for workflow-related errors."""
    pass

class ValidationError(WorkflowError):
    """Raised when workflow validation fails."""
    pass
```

2. Provide helpful error messages:
```python
if not os.path.exists(workflow_file):
    raise FileNotFoundError(
        f"Workflow file not found: {workflow_file}"
    )
```

## Testing

### Test Organization

Organize tests to mirror the source code structure:

```
tests/
├── __init__.py
├── test_cli.py
├── test_engine.py
└── tasks/
    ├── __init__.py
    ├── test_base.py
    └── test_file_tasks.py
```

### Test Cases

Use descriptive test names and arrange tests using the AAA pattern:

```python
def test_workflow_validation_catches_missing_required_params():
    # Arrange
    workflow_data = {
        "name": "test",
        "steps": [
            {
                "name": "step1",
                "task": "shell",
                # Missing required 'command' parameter
            }
        ]
    }
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc:
        validate_workflow_data(workflow_data)
    assert "Missing required parameter: command" in str(exc.value)
```

### Test Coverage

Maintain high test coverage:

```bash
# Run tests with coverage
pytest tests/ --cov=yaml_workflow

# Generate coverage report
pytest tests/ --cov=yaml_workflow --cov-report=html
```

## YAML Files

### Workflow Files

Follow these guidelines for workflow files:

1. Use descriptive names:
```yaml
name: Data Processing Pipeline
description: Process and analyze data from multiple sources
```

2. Group related parameters:
```yaml
params:
  # Input configuration
  input_file:
    type: string
    description: Input data file
  
  # Processing options
  batch_size:
    type: integer
    default: 1000
```

3. Use consistent indentation (2 spaces):
```yaml
steps:
  - name: process
    task: shell
    params:
      command: |
        python process.py \
          --input {{ input_file }} \
          --batch-size {{ batch_size }}
```

### Configuration Files

For configuration files:

1. Use clear sections:
```yaml
# Project settings
project:
  name: example
  version: 1.0.0

# Task defaults
tasks:
  shell:
    timeout: 300
```

2. Include comments for non-obvious settings:
```yaml
tasks:
  http_request:
    # Increase timeout for slow APIs
    timeout: 60
    # Disable SSL verification for local development
    verify_ssl: false
```

## Git Workflow

### Commits

1. Use descriptive commit messages:
```
feat: Add HTTP request retry mechanism

- Add exponential backoff retry logic
- Configure retry attempts via workflow
- Add tests for retry functionality
```

2. Keep commits focused and atomic

### Branches

1. Feature branches:
   - `feature/add-http-retry`
   - `feature/improve-error-handling`

2. Fix branches:
   - `fix/validation-error`
   - `fix/cli-parameters`

### Pull Requests

1. Include clear descriptions
2. Reference related issues
3. Update documentation
4. Add/update tests
5. Ensure CI passes

## Code Review

### Checklist

- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Error handling implemented
- [ ] Performance considerations addressed
- [ ] Security implications considered

### Review Comments

1. Be constructive and specific
2. Explain the reasoning
3. Provide examples when helpful
4. Consider alternative approaches 