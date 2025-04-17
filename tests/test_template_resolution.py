"""Tests for template resolution functionality in the workflow engine."""

from pathlib import Path

import pytest

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import TemplateError


@pytest.fixture
def engine():
    """Create a basic workflow engine for testing."""
    workflow = {"name": "test_workflow", "steps": [{"name": "step1", "task": "python"}]}
    return WorkflowEngine(workflow)


def test_resolve_simple_value(engine):
    """Test resolving a simple template value."""
    engine.context["test_var"] = "hello"
    result = engine.resolve_value("{{ test_var }}")
    assert result == "hello"


def test_resolve_nested_dict(engine):
    """Test resolving templates in nested dictionaries."""
    engine.context.update({"name": "test", "value": 42, "nested": {"key": "value"}})

    template = {
        "name": "{{ name }}",
        "complex": {"number": "{{ value }}", "nested": '{{ nested["key"] }}'},
    }

    result = engine.resolve_value(template)
    assert result == {"name": "test", "complex": {"number": "42", "nested": "value"}}


def test_resolve_list_values(engine):
    """Test resolving templates in lists."""
    engine.context.update({"items": ["a", "b", "c"], "index": 1})

    template = ["{{ items[0] }}", "{{ items[index] }}", "static"]

    result = engine.resolve_value(template)
    assert result == ["a", "b", "static"]


def test_resolve_inputs_with_namespaces(engine):
    """Test resolving inputs with namespace variables."""
    engine.context.update(
        {
            "args": {"input1": "value1"},
            "env": {"PATH": "/usr/bin"},
            "steps": {"previous": {"output": "result"}},
        }
    )

    inputs = {
        "from_args": '{{ args["input1"] }}',
        "from_env": '{{ env["PATH"] }}',
        "from_steps": '{{ steps["previous"]["output"] }}',
    }

    result = engine.resolve_inputs(inputs)
    assert result == {
        "from_args": "value1",
        "from_env": "/usr/bin",
        "from_steps": "result",
    }


def test_resolve_undefined_variable(engine):
    """Test error handling for undefined variables."""
    with pytest.raises(TemplateError) as exc:
        engine.resolve_value("{{ undefined_var }}")
    assert "undefined_var" in str(exc.value)


def test_resolve_invalid_template(engine):
    """Test error handling for invalid template syntax."""
    with pytest.raises(TemplateError) as exc:
        engine.resolve_value("{{ invalid syntax }")
    assert "template" in str(exc.value).lower()


def test_resolve_complex_expression(engine):
    """Test resolving complex template expressions."""
    engine.context.update({"numbers": [1, 2, 3, 4, 5], "threshold": 3})

    template = "{{ numbers | select('>', threshold) | list }}"
    result = engine.resolve_value(template)
    assert result == "[4, 5]"


def test_resolve_mixed_content(engine):
    """Test resolving templates mixed with static content."""
    engine.context["name"] = "world"
    result = engine.resolve_value("Hello {{ name }}! Count: {{ range(3) | list }}")
    assert result == "Hello world! Count: [0, 1, 2]"


def test_resolve_inputs_type_preservation(engine):
    """Test that resolve_inputs preserves non-string types correctly."""
    engine.context.update({"args": {"number": 42, "flag": True, "list": [1, 2, 3]}})

    inputs = {
        "raw_number": 42,
        "raw_bool": True,
        "raw_list": [1, 2, 3],
        "template_number": '{{ args["number"] }}',
        "template_flag": '{{ args["flag"] }}',
        "template_list": '{{ args["list"] }}',
    }

    result = engine.resolve_inputs(inputs)
    assert isinstance(result["raw_number"], int)
    assert isinstance(result["raw_bool"], bool)
    assert isinstance(result["raw_list"], list)
    assert (
        result["template_number"] == "42"
    )  # Note: becomes string due to template rendering
    assert (
        result["template_flag"] == "True"
    )  # Note: becomes string due to template rendering
    assert (
        result["template_list"] == "[1, 2, 3]"
    )  # Note: becomes string due to template rendering


def test_resolve_nested_namespaces(engine):
    """Test resolving deeply nested namespace references."""
    engine.context.update(
        {"steps": {"step1": {"outputs": {"nested": {"value": "found"}}}}}
    )

    template = '{{ steps["step1"]["outputs"]["nested"]["value"] }}'
    result = engine.resolve_value(template)
    assert result == "found"


def test_resolve_with_filters(engine):
    """Test resolving templates using Jinja2 filters."""
    engine.context["items"] = ["a", "b", "c"]

    templates = {
        "upper": "{{ items[0] | upper }}",
        "join": "{{ items | join('-') }}",
        "length": "{{ items | length }}",
    }

    result = engine.resolve_inputs(templates)
    assert result == {"upper": "A", "join": "a-b-c", "length": "3"}
