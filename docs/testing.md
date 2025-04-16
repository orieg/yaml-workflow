# Test Suite Organization

## Overview

The test suite for yaml-workflow is organized into multiple layers, each focusing on different aspects of the system. This organization helps maintain clear boundaries between components and makes it easier to understand and maintain the test suite.

## Test Structure

### Core Layer: Template Engine Tests
**File**: `tests/test_template.py`

Tests the fundamental template engine implementation (`TemplateEngine` class), focusing on:
- Template compilation and caching mechanisms
- Variable resolution and type information handling
- Error handling and reporting
- Cache management
- Basic template processing operations

Example:
```python
def test_process_template(template_engine, variables):
    """Test processing a template."""
    template = "Input: {{ args.input_file }}, Output: {{ args.output_file }}"
    result = template_engine.process_template(template, variables)
    assert result == "Input: input.txt, Output: output.txt"
```

### Integration Layer: Workflow Engine Template Tests
**File**: `tests/test_engine_template.py`

Tests the integration between the workflow engine and template system, covering:
- Template resolution within workflow context
- Step input resolution
- Error message templating
- Workflow-specific template operations

Example:
```python
def test_resolve_template_simple(engine):
    """Test simple template resolution."""
    result = engine.resolve_template("File: {{ args.input_file }}")
    assert result == "File: test.txt"
```

### Task Layer: Template Tasks Tests
**File**: `tests/test_template_tasks.py`

Tests the high-level template task handlers that users interact with directly:
- Template rendering to files
- Complex template features (loops, conditionals)
- Template filters and modifiers
- File-based templates
- Whitespace control
- Template includes (planned feature)

Example:
```python
def test_template_with_loops(temp_workspace, template_context):
    """Test template rendering with loops."""
    step = {
        "template": """Items:
{% for item in items %}
- {{ item }}
{% endfor %}""",
        "output": "items.txt",
    }
    result = render_template(step, template_context, temp_workspace)
```

## Test Categories

Our tests are organized into several categories:

1. **Unit Tests**
   - Test individual components in isolation
   - Focus on specific functionality
   - Fast execution
   - High coverage

2. **Integration Tests**
   - Test component interactions
   - Verify system behavior
   - End-to-end workflow testing

3. **Error Handling Tests**
   - Verify error conditions
   - Test error messages
   - Validate error recovery

4. **Performance Tests**
   - Test caching mechanisms
   - Verify resource usage
   - Check execution time

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_template.py

# Run with coverage
pytest tests/ --cov=yaml_workflow
```

### Test Options

- `-v`: Verbose output
- `-k "test_name"`: Run tests matching pattern
- `--pdb`: Debug on test failure
- `--cov-report html`: Generate HTML coverage report

## Writing New Tests

When adding new tests:

1. **Choose the Right Layer**
   - Core layer for fundamental operations
   - Integration layer for component interactions
   - Task layer for user-facing features

2. **Follow Naming Conventions**
   - Use descriptive test names
   - Group related tests together
   - Include both positive and negative test cases

3. **Use Fixtures**
   - Create reusable test data
   - Share common setup code
   - Keep tests focused and clean

4. **Document Test Purpose**
   - Add clear docstrings
   - Explain test scenarios
   - Document expected behavior

## Test Dependencies

The test suite requires additional dependencies, which can be installed using:
```bash
pip install -e ".[test]"
```

Key test dependencies include:
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking support

## Future Improvements

Planned enhancements to the test suite:

1. **Template Features**
   - Add support for template includes
   - Enhance error reporting
   - Add more complex template scenarios

2. **Performance Testing**
   - Add benchmarks
   - Test large template processing
   - Measure memory usage

3. **Integration Testing**
   - Add more end-to-end tests
   - Test external integrations
   - Add stress testing 