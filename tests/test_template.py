"""Tests for template engine."""

import pytest
from yaml_workflow.template import TemplateEngine
from yaml_workflow.exceptions import TemplateError


@pytest.fixture
def template_engine():
    """Create a template engine instance."""
    return TemplateEngine()


@pytest.fixture
def variables():
    """Create test variables."""
    return {
        "args": {
            "input_file": "input.txt",
            "output_file": "output.txt"
        },
        "env": {
            "HOME": "/home/user",
            "PATH": "/usr/bin:/bin"
        },
        "steps": {
            "step1": {
                "output": "step1 output"
            }
        },
        "batch": {
            "item": {"id": 1, "name": "test"},
            "index": 0,
            "name": "batch_task"
        },
        "workflow_name": "test_workflow",
        "workspace": "/tmp/workspace",
        "run_number": "1",
        "timestamp": "2024-03-20T12:00:00",
        "workflow_file": "workflow.yaml"
    }


def test_process_template(template_engine, variables):
    """Test processing a template."""
    template = 'Input: {{ args["input_file"] }}, Output: {{ args["output_file"] }}'
    result = template_engine.process_template(template, variables)
    assert result == "Input: input.txt, Output: output.txt"


def test_process_template_undefined_variable(template_engine, variables):
    """Test processing a template with undefined variable."""
    template = '{{ args["missing"] }}'
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert 'Template error: Invalid namespace \'args["missing"]\'' in error_msg
    assert "Available namespaces:" in error_msg
    assert "args" in error_msg
    assert "env" in error_msg
    assert "steps" in error_msg
    assert "batch" in error_msg


def test_process_template_syntax_error(template_engine, variables):
    """Test processing a template with syntax error."""
    template = '{{ args["input_file"] }'  # Missing closing brace
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    assert "Template syntax error:" in str(exc.value)


def test_process_template_simple(template_engine, variables):
    """Test simple variable substitution."""
    template = 'Input file: {{ args["input_file"] }}'
    result = template_engine.process_template(template, variables)
    assert result == "Input file: input.txt"


def test_process_template_nested(template_engine, variables):
    """Test nested variable access."""
    template = '{{ steps["step1"]["output"] }}'
    result = template_engine.process_template(template, variables)
    assert result == "step1 output"


def test_process_template_invalid_attribute(template_engine, variables):
    """Test error on invalid attribute access."""
    template = '{{ args["input_file"]["invalid"] }}'
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert 'Template error: Invalid namespace \'args["input_file"]["invalid"]\'' in error_msg
    assert "Available namespaces:" in error_msg
    assert "args" in error_msg
    assert "env" in error_msg
    assert "steps" in error_msg
    assert "batch" in error_msg


def test_process_template_invalid_namespace(template_engine, variables):
    """Test error on invalid namespace access."""
    template = '{{ invalid["variable"] }}'
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert 'Template error: Invalid namespace \'invalid["variable"]\'' in error_msg
    assert "Available namespaces:" in error_msg
    assert "args" in error_msg
    assert "env" in error_msg
    assert "steps" in error_msg
    assert "batch" in error_msg


def test_process_template_batch_access(template_engine, variables):
    """Test batch namespace access."""
    template = 'Item: {{ batch["item"]["name"] }}, Index: {{ batch["index"] }}'
    result = template_engine.process_template(template, variables)
    assert result == "Item: test, Index: 0"


def test_process_value_string(template_engine, variables):
    """Test processing string value."""
    value = 'File: {{ args["input_file"] }}'
    result = template_engine.process_value(value, variables)
    assert result == "File: input.txt"


def test_process_value_dict(template_engine, variables):
    """Test processing dictionary value."""
    value = {
        "file": '{{ args["input_file"] }}',
        "path": '{{ env["HOME"] }}'
    }
    result = template_engine.process_value(value, variables)
    assert result == {
        "file": "input.txt",
        "path": "/home/user"
    }


def test_process_value_list(template_engine, variables):
    """Test processing list value."""
    value = ['{{ args["input_file"] }}', '{{ env["HOME"] }}']
    result = template_engine.process_value(value, variables)
    assert result == ["input.txt", "/home/user"]


def test_process_value_non_template(template_engine, variables):
    """Test processing non-template value."""
    value = 42
    result = template_engine.process_value(value, variables)
    assert result == 42 