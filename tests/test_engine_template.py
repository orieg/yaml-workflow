"""Tests for template handling in WorkflowEngine."""

from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import TemplateError, WorkflowError


@pytest.fixture
def workflow_definition():
    """Create a test workflow definition."""
    return {
        "name": "test_workflow",
        "params": {"input_file": {"default": "test.txt"}, "mode": "read"},
        "steps": [
            {
                "name": "step1",
                "module": "yaml_workflow.tasks.file_tasks",
                "function": "read_file",
                "inputs": {"path": "{{ args.input_file }}", "mode": "{{ args.mode }}"},
                "outputs": "content",
            }
        ],
    }


@pytest.fixture
def engine(workflow_definition, tmp_path):
    """Create a test workflow engine."""
    engine = WorkflowEngine(workflow_definition, workspace=str(tmp_path))
    engine.context = {
        "args": {"input_file": "test.txt", "mode": "read"},
        "env": {"HOME": "/home/user"},
        "steps": {},
        "workflow_name": "test_workflow",
    }
    return engine


def test_template_engine_initialization(engine):
    """Test that template engine is properly initialized."""
    assert engine.template_engine is not None


def test_resolve_template_simple(engine):
    """Test simple template resolution."""
    result = engine.resolve_template("File: {{ args.input_file }}")
    assert result == "File: test.txt"


def test_resolve_template_nested(engine):
    """Test nested template resolution."""
    engine.context["steps"]["step1"] = {"output": "result1"}
    result = engine.resolve_template("Output: {{ steps.step1.output }}")
    assert result == "Output: result1"


def test_resolve_template_undefined(engine):
    """Test error on undefined variable."""
    with pytest.raises(TemplateError) as exc:
        engine.resolve_template("{{ args.missing }}")
    error_msg = str(exc.value)
    assert "Template error: Undefined variable 'args.missing'" in error_msg
    assert "Available variables in 'args' namespace" in error_msg


def test_resolve_template_with_multiple_vars(engine):
    """Test template with multiple variables."""
    result = engine.resolve_template(
        "File '{{ args.input_file }}' in mode '{{ args.mode }}'"
    )
    assert result == "File 'test.txt' in mode 'read'"


def test_resolve_template_with_env_vars(engine):
    """Test template with environment variables."""
    result = engine.resolve_template("Home directory: {{ env.HOME }}")
    assert result == "Home directory: /home/user"


def test_resolve_template_with_whitespace(engine):
    """Test template with various whitespace."""
    result = engine.resolve_template(
        "{{args.input_file}} {{ args.mode}} {{args.mode }}"
    )
    assert result == "test.txt read read"


def test_resolve_template_empty_string(engine):
    """Test resolving an empty template string."""
    result = engine.resolve_template("")
    assert result == ""


def test_resolve_template_no_variables(engine):
    """Test template with no variables."""
    result = engine.resolve_template("Plain text")
    assert result == "Plain text"


def test_resolve_template_with_special_chars(engine):
    """Test template with special characters."""
    engine.context["args"]["special"] = "!@#$%^&*()"
    result = engine.resolve_template("Special: {{ args.special }}")
    assert result == "Special: !@#$%^&*()"


def test_resolve_template_with_numbers(engine):
    """Test template with numeric values."""
    engine.context["args"]["number"] = 42
    result = engine.resolve_template("Number: {{ args.number }}")
    assert result == "Number: 42"


def test_resolve_value_string(engine):
    """Test resolving string value."""
    result = engine.resolve_value("Mode: {{ args.mode }}")
    assert result == "Mode: read"


def test_resolve_value_dict(engine):
    """Test resolving dictionary value."""
    value = {"file": "{{ args.input_file }}", "mode": "{{ args.mode }}"}
    result = engine.resolve_value(value)
    assert result == {"file": "test.txt", "mode": "read"}


def test_resolve_value_list(engine):
    """Test resolving list value."""
    value = ["{{ args.input_file }}", "{{ args.mode }}"]
    result = engine.resolve_value(value)
    assert result == ["test.txt", "read"]


def test_resolve_inputs(engine):
    """Test resolving step inputs."""
    inputs = {
        "path": "{{ args.input_file }}",
        "mode": "{{ args.mode }}",
        "options": {"encoding": "utf-8", "name": "{{ workflow_name }}"},
    }
    result = engine.resolve_inputs(inputs)
    assert result == {
        "path": "test.txt",
        "mode": "read",
        "options": {"encoding": "utf-8", "name": "test_workflow"},
    }
