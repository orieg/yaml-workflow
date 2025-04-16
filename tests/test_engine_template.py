"""Tests for template handling in WorkflowEngine."""

import pytest
from pathlib import Path
from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import TemplateError, WorkflowError


@pytest.fixture
def workflow_definition():
    """Create a test workflow definition."""
    return {
        "name": "test_workflow",
        "params": {
            "input_file": {"default": "test.txt"},
            "mode": "read"
        },
        "steps": [
            {
                "name": "step1",
                "module": "yaml_workflow.tasks.file_tasks",
                "function": "read_file",
                "inputs": {
                    "path": "{{ args.input_file }}",
                    "mode": "{{ args.mode }}"
                },
                "outputs": "content"
            }
        ]
    }


@pytest.fixture
def engine(workflow_definition, tmp_path):
    """Create a workflow engine instance."""
    return WorkflowEngine(workflow_definition, workspace=str(tmp_path))


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
    assert "Variable 'args.missing' is undefined" in error_msg
    assert "Available variables in 'args' namespace" in error_msg


def test_resolve_value_string(engine):
    """Test resolving string value."""
    result = engine.resolve_value("Mode: {{ args.mode }}")
    assert result == "Mode: read"


def test_resolve_value_dict(engine):
    """Test resolving dictionary value."""
    value = {
        "file": "{{ args.input_file }}",
        "mode": "{{ args.mode }}"
    }
    result = engine.resolve_value(value)
    assert result == {
        "file": "test.txt",
        "mode": "read"
    }


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
        "options": {
            "encoding": "utf-8",
            "name": "{{ workflow_name }}"
        }
    }
    result = engine.resolve_inputs(inputs)
    assert result == {
        "path": "test.txt",
        "mode": "read",
        "options": {
            "encoding": "utf-8",
            "name": "test_workflow"
        }
    }


def test_error_message_template(engine):
    """Test error message template resolution."""
    step = {
        "name": "test_step",
        "on_error": {
            "action": "fail",
            "message": "Failed to process {{ args.input_file }}: {{ error }}"
        }
    }
    error = ValueError("Invalid input")
    
    with pytest.raises(WorkflowError) as exc:
        engine._handle_step_error(step, error)
    
    # Verify that the error message was properly templated
    assert str(exc.value) == "Failed to process test.txt: Invalid input" 