"""Tests for template engine."""

import pytest
from yaml_workflow.template import TemplateEngine
from yaml_workflow.exceptions import TemplateError


@pytest.fixture
def template_engine():
    """Create template engine instance for testing."""
    return TemplateEngine()


@pytest.fixture
def test_context():
    """Create test context with variables."""
    return {
        "args": {"input": "test.txt", "mode": "read"},
        "env": {"HOME": "/home/user", "PATH": "/usr/bin"},
        "steps": {
            "step1": {"output": "result1"},
            "step2": {"output": "result2"}
        },
        "workflow_name": "test_workflow",
        "workspace": "/tmp/workspace"
    }


def test_process_template_simple(template_engine, test_context):
    """Test simple variable substitution."""
    template = "Input file: {{ args.input }}"
    result = template_engine.process_template(template, test_context)
    assert result == "Input file: test.txt"


def test_process_template_nested(template_engine, test_context):
    """Test nested variable access."""
    template = "Step output: {{ steps.step1.output }}"
    result = template_engine.process_template(template, test_context)
    assert result == "Step output: result1"


def test_process_template_undefined(template_engine, test_context):
    """Test error on undefined variable."""
    template = "{{ args.missing }}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, test_context)
    error_msg = str(exc.value)
    assert "Variable 'args.missing' is undefined" in error_msg
    assert "Available variables in 'args' namespace" in error_msg
    assert "'input': 'str" in error_msg  # Type information included


def test_process_template_syntax_error(template_engine, test_context):
    """Test error on template syntax error."""
    template = "{% if args.input %"  # Missing endif
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, test_context)
    error_msg = str(exc.value)
    assert "Template syntax error at line" in error_msg
    assert "unexpected 'end of template'" in error_msg.lower()


def test_process_template_invalid_attribute(template_engine, test_context):
    """Test error on invalid attribute access."""
    template = "{{ args.input.invalid }}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, test_context)
    error_msg = str(exc.value)
    assert "Variable 'args.input.invalid' is undefined" in error_msg
    assert "str" in error_msg  # Shows that args.input is a string


def test_process_value_string(template_engine, test_context):
    """Test processing string value."""
    value = "File: {{ args.input }}"
    result = template_engine.process_value(value, test_context)
    assert result == "File: test.txt"


def test_process_value_dict(template_engine, test_context):
    """Test processing dictionary value."""
    value = {
        "file": "{{ args.input }}",
        "path": "{{ env.HOME }}"
    }
    result = template_engine.process_value(value, test_context)
    assert result == {
        "file": "test.txt",
        "path": "/home/user"
    }


def test_process_value_list(template_engine, test_context):
    """Test processing list value."""
    value = ["{{ args.input }}", "{{ env.HOME }}"]
    result = template_engine.process_value(value, test_context)
    assert result == ["test.txt", "/home/user"]


def test_process_value_non_template(template_engine, test_context):
    """Test processing non-template value."""
    value = 42
    result = template_engine.process_value(value, test_context)
    assert result == 42


def test_get_available_variables(template_engine, test_context):
    """Test getting available variables."""
    available = template_engine.get_available_variables(test_context)
    assert set(available.keys()) == {"args", "env", "steps", "root"}
    assert "input" in available["args"]
    assert "HOME" in available["env"]
    assert "step1" in available["steps"]
    assert "workflow_name" in available["root"]


def test_get_variables_with_types(template_engine, test_context):
    """Test getting variables with type information."""
    available = template_engine._get_variables_with_types(test_context)
    
    # Check args types
    assert available["args"]["input"].startswith("str[")
    assert available["args"]["mode"].startswith("str[")
    
    # Check env types
    assert available["env"]["HOME"].startswith("str[")
    assert available["env"]["PATH"].startswith("str[")
    
    # Check steps types
    assert available["steps"]["step1"] == "dict[1 items]"
    assert available["steps"]["step2"] == "dict[1 items]"
    
    # Check root types
    assert available["root"]["workflow_name"].startswith("str[")
    assert available["root"]["workspace"].startswith("str[") 