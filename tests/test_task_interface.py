"""Tests for the task interface and TaskConfig class."""

from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import TemplateError
from yaml_workflow.tasks import TaskConfig, get_task_handler, register_task


@pytest.fixture
def workspace():
    """Fixture providing a workspace path."""
    return Path("/tmp/workspace")


@pytest.fixture
def basic_step():
    """Fixture providing a basic step configuration."""
    return {
        "name": "test_step",
        "task": "test_task",
        "inputs": {"message": "Hello {{ args.name }}", "count": 42, "flag": True},
    }


@pytest.fixture
def context_with_namespaces():
    """Fixture providing a context with namespaced variables."""
    return {
        "args": {"name": "World", "count": 10},
        "env": {"DEBUG": "true", "PATH": "/usr/bin"},
        "steps": {"previous": {"output": "success"}},
        "root_var": "root_value",
    }


@register_task()
def my_simple_task(value: int) -> int:
    """A simple task for testing registration."""
    return value * 2


@register_task("custom_name_task")
def another_simple_task(text: str) -> str:
    """A task registered with a custom name."""
    return f"Processed: {text}"


@register_task()
def task_with_args_and_config(message: str, config: TaskConfig) -> str:
    """A task that takes both specific args and the config object."""
    # The config argument is present but might not be used directly
    # Accessing config.workspace.path as an example if needed
    # print(f"Workspace path from config: {config.workspace.path}")
    return f"Processed: {message}"


def test_task_config_initialization(basic_step, context_with_namespaces, workspace):
    """Test TaskConfig initialization with basic attributes."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)

    assert config.name == "test_step"
    assert config.type == "test_task"
    assert config.inputs == basic_step["inputs"]
    assert config.workspace == workspace
    assert config._context == context_with_namespaces
    assert isinstance(config._processed_inputs, dict)
    assert len(config._processed_inputs) == 0


def test_get_variable_with_namespace(basic_step, context_with_namespaces, workspace):
    """Test getting variables from specific namespaces."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)

    assert config.get_variable("name", "args") == "World"
    assert config.get_variable("DEBUG", "env") == "true"
    assert config.get_variable("previous", "steps")["output"] == "success"
    assert config.get_variable("root_var") == "root_value"


def test_get_variable_missing(basic_step, context_with_namespaces, workspace):
    """Test getting non-existent variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)

    assert config.get_variable("nonexistent", "args") is None
    assert config.get_variable("nonexistent") is None
    assert config.get_variable("name", "nonexistent_namespace") is None


def test_get_available_variables(basic_step, context_with_namespaces, workspace):
    """Test getting available variables by namespace."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    available = config.get_available_variables()

    assert set(available["args"]) == {"name", "count"}
    assert set(available["env"]) == {"DEBUG", "PATH"}
    assert set(available["steps"]) == {"previous"}
    assert set(available["root"]) == {"root_var"}


def test_process_inputs_with_templates(basic_step, context_with_namespaces, workspace):
    """Test processing inputs with template variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    processed = config.process_inputs()

    assert processed["message"] == "Hello World"  # Template resolved
    assert processed["count"] == 42  # Non-string preserved
    assert processed["flag"] is True  # Boolean preserved


def test_process_inputs_caching(basic_step, context_with_namespaces, workspace):
    """Test that processed inputs are cached."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)

    first_result = config.process_inputs()
    # Modify context (shouldn't affect cached result)
    config._context["args"]["name"] = "Changed"
    second_result = config.process_inputs()

    assert first_result is second_result
    assert first_result["message"] == "Hello World"


def test_process_inputs_undefined_variable(
    basic_step, context_with_namespaces, workspace
):
    """Test error handling for undefined template variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    config.inputs["bad_template"] = "{{ args.undefined }}"

    with pytest.raises(TemplateError) as exc_info:
        config.process_inputs()

    error_msg = str(exc_info.value)
    assert "Undefined variable 'args.undefined'" in error_msg
    assert "Available variables in 'args' namespace" in error_msg
    assert "count" in error_msg  # Should show available variables
    assert "name" in error_msg  # Should show available variables


def test_get_undefined_namespace(basic_step, context_with_namespaces, workspace):
    """Test extracting namespace from error messages."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)

    # Test direct namespace access patterns
    assert config._get_undefined_namespace("'args.undefined'") == "args"
    assert config._get_undefined_namespace("'env.missing'") == "env"
    assert config._get_undefined_namespace("'steps.unknown'") == "steps"

    # Test with template context
    config.inputs["test1"] = "{{ args.unknown }}"
    assert (
        config._get_undefined_namespace("'dict object' has no attribute 'unknown'")
        == "args"
    )

    config.inputs["test2"] = "{{ env.missing }}"
    assert (
        config._get_undefined_namespace("'dict object' has no attribute 'missing'")
        == "env"
    )

    # Test root namespace (no specific namespace found)
    assert config._get_undefined_namespace("'unknown_var'") == "root"
    assert config._get_undefined_namespace("some random error") == "root"


def test_complex_template_resolution(basic_step, context_with_namespaces, workspace):
    """Test processing complex templates with multiple variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    config.inputs[
        "complex"
    ] = """
        Name: {{ args.name }}
        Count: {{ args.count }}
        Debug: {{ env.DEBUG }}
        Previous: {{ steps.previous.output }}
        Root: {{ root_var }}
    """

    processed = config.process_inputs()
    result = processed["complex"]

    assert "Name: World" in result
    assert "Count: 10" in result
    assert "Debug: true" in result
    assert "Previous: success" in result
    assert "Root: root_value" in result


def test_nested_variable_access(basic_step, context_with_namespaces, workspace):
    """Test accessing nested variables in templates."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    config.inputs["nested"] = "{{ steps.previous['output'] }}"

    processed = config.process_inputs()
    assert processed["nested"] == "success"


def test_nested_type_preservation(basic_step, context_with_namespaces, workspace):
    """Test type preservation in nested template structures."""
    config = TaskConfig(
        {
            "name": "test_types",
            "task": "test_task",
            "inputs": {
                "nested_data": {
                    "boolean": "{{ env.is_enabled }}",
                    "number": "{{ args.value }}",
                    "array": ["{{ env.numbers[0] }}", "{{ env.numbers[1] }}"],
                    "object": {
                        "flag": "{{ env.debug_flag }}",
                        "count": "{{ args.item_count }}",
                    },
                }
            },
        },
        {
            "args": {"value": 42, "item_count": 100},
            "env": {"is_enabled": True, "numbers": [1, 2], "debug_flag": False},
            "steps": {},
        },
        workspace,
    )

    processed = config.process_inputs()
    nested = processed["nested_data"]

    # Check type preservation
    assert isinstance(nested["boolean"], bool)
    assert nested["boolean"] is True

    assert isinstance(nested["number"], int)
    assert nested["number"] == 42

    assert isinstance(nested["array"], list)
    assert all(isinstance(x, int) for x in nested["array"])
    assert nested["array"] == [1, 2]

    assert isinstance(nested["object"]["flag"], bool)
    assert nested["object"]["flag"] is False

    assert isinstance(nested["object"]["count"], int)
    assert nested["object"]["count"] == 100


def test_nested_error_handling(basic_step, context_with_namespaces, workspace):
    """Test error handling in nested template structures."""
    config = TaskConfig(
        {
            "name": "test_errors",
            "task": "test_task",
            "inputs": {
                "nested_errors": {
                    "level1": {
                        "valid": "{{ args.name }}",
                        "invalid": "{{ args.missing }}",
                    },
                    "array": [
                        "{{ env.DEBUG }}",
                        "{{ env.nonexistent }}",
                        "{{ steps.unknown.output }}",
                    ],
                }
            },
        },
        context_with_namespaces,
        workspace,
    )

    with pytest.raises(TemplateError) as exc_info:
        config.process_inputs()

    error_msg = str(exc_info.value)
    # Should identify the undefined variable
    assert "Undefined variable 'args.missing'" in error_msg
    # Should show available variables
    assert "Available variables in 'args' namespace" in error_msg
    assert "name" in error_msg
    assert "count" in error_msg


def test_numeric_type_conversion(basic_step, context_with_namespaces, workspace):
    """Test conversion of numeric string templates to proper number types."""
    config = TaskConfig(
        {
            "name": "test_numbers",
            "task": "test_task",
            "inputs": {
                "numbers": {
                    "integer": "{{ args.int_value }}",
                    "float": "{{ env.float_value }}",
                    "zero": "{{ args.zero }}",
                    "negative": "{{ env.negative }}",
                }
            },
        },
        {
            "args": {"int_value": 42, "zero": 0},
            "env": {"float_value": 3.14, "negative": -1},
            "steps": {},
        },
        workspace,
    )

    processed = config.process_inputs()
    numbers = processed["numbers"]

    # Check numeric type conversion
    assert isinstance(numbers["integer"], int)
    assert numbers["integer"] == 42

    assert isinstance(numbers["float"], float)
    assert numbers["float"] == 3.14

    assert isinstance(numbers["zero"], int)
    assert numbers["zero"] == 0

    assert isinstance(numbers["negative"], int)
    assert numbers["negative"] == -1


def test_task_registration_and_retrieval():
    """Test that tasks are registered and can be retrieved."""
    # Test retrieving task registered with default name
    default_task_handler = get_task_handler("my_simple_task")
    assert default_task_handler is not None
    assert callable(default_task_handler)

    # Test retrieving task registered with custom name
    custom_task_handler = get_task_handler("custom_name_task")
    assert custom_task_handler is not None
    assert callable(custom_task_handler)

    # Test retrieving a non-existent task
    non_existent_handler = get_task_handler("non_existent_task_123")
    assert non_existent_handler is None

    # Optional: Add direct call checks if mocking TaskConfig is feasible/desired
    # mock_config_simple = ...
    # assert default_task_handler(mock_config_simple) == ...
    # mock_config_custom = ...
    # assert custom_task_handler(mock_config_custom) == ...


def test_task_with_args_and_config_param(tmp_path):
    """Test wrapper correctly handles tasks with both specific args and config param."""
    workflow = {
        "steps": [
            {
                "name": "step1",
                "task": "task_with_args_and_config",
                "inputs": {"message": "Test Message"},
            }
        ]
    }
    # Need WorkflowEngine to run the task via the wrapper
    engine = WorkflowEngine(workflow, base_dir=tmp_path)
    result = engine.run()
    assert result["status"] == "completed"
    assert "step1" in result["outputs"]
    assert result["outputs"]["step1"]["result"] == "Processed: Test Message"
