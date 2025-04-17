"""Tests for the task interface and TaskConfig class."""

import pytest
from pathlib import Path

from yaml_workflow.tasks import TaskConfig
from yaml_workflow.exceptions import TemplateError


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
        "inputs": {
            "message": "Hello {{ args.name }}",
            "count": 42,
            "flag": True
        }
    }


@pytest.fixture
def context_with_namespaces():
    """Fixture providing a context with namespaced variables."""
    return {
        "args": {
            "name": "World",
            "count": 10
        },
        "env": {
            "DEBUG": "true",
            "PATH": "/usr/bin"
        },
        "steps": {
            "previous": {
                "output": "success"
            }
        },
        "root_var": "root_value"
    }


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


def test_process_inputs_undefined_variable(basic_step, context_with_namespaces, workspace):
    """Test error handling for undefined template variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    config.inputs["bad_template"] = "{{ args.undefined }}"
    
    with pytest.raises(TemplateError) as exc_info:
        config.process_inputs()
    
    error_msg = str(exc_info.value)
    assert "undefined" in error_msg
    assert "namespace 'args'" in error_msg
    assert "Available variables" in error_msg
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
    assert config._get_undefined_namespace("'dict object' has no attribute 'unknown'") == "args"
    
    config.inputs["test2"] = "{{ env.missing }}"
    assert config._get_undefined_namespace("'dict object' has no attribute 'missing'") == "env"
    
    # Test root namespace (no specific namespace found)
    assert config._get_undefined_namespace("'unknown_var'") == "root"
    assert config._get_undefined_namespace("some random error") == "root"


def test_complex_template_resolution(basic_step, context_with_namespaces, workspace):
    """Test processing complex templates with multiple variables."""
    config = TaskConfig(basic_step, context_with_namespaces, workspace)
    config.inputs["complex"] = """
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