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
        "workflow_name": "test_workflow",
        "workspace": "/tmp/workspace",
        "run_number": "1",
        "timestamp": "2024-03-20T12:00:00",
        "workflow_file": "workflow.yaml"
    }


def test_process_template(template_engine, variables):
    """Test processing a template."""
    template = "Input: {{ args.input_file }}, Output: {{ args.output_file }}"
    result = template_engine.process_template(template, variables)
    assert result == "Input: input.txt, Output: output.txt"


def test_process_template_undefined_variable(template_engine, variables):
    """Test processing a template with undefined variable."""
    template = "{{ args.missing }}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    assert "Variable 'args.missing' is undefined" in str(exc.value)
    assert "Available variables in 'args' namespace:" in str(exc.value)
    assert "'args.input_file': 'str[9]'" in str(exc.value)
    assert "'args.output_file': 'str[10]'" in str(exc.value)


def test_process_template_syntax_error(template_engine, variables):
    """Test processing a template with syntax error."""
    template = "{{ args.input_file }"  # Missing closing brace
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    assert "Template syntax error at line 1:" in str(exc.value)


def test_get_variables_with_types(template_engine, variables):
    """Test getting variables with types."""
    types = template_engine.get_variables_with_types(variables)
    assert types["args"] == "dict[2 items]"
    assert types["args.input_file"] == "str[9]"
    assert types["args.output_file"] == "str[10]"
    assert types["env"] == "dict[2 items]"
    assert types["env.HOME"] == "str[10]"
    assert types["steps"] == "dict[1 items]"
    assert types["steps.step1"] == "dict[1 items]"
    assert types["steps.step1.output"] == "str[12]"


def test_cache_with_invalid_template(template_engine, variables):
    """Test cache behavior with invalid template."""
    # First try with invalid template
    template = "{{ args.input_file }"  # Missing closing brace
    with pytest.raises(TemplateError):
        template_engine.process_template(template, variables)

    # Cache should be cleared
    info = template_engine.get_cache_info()
    assert info["currsize"] == 0

    # Now try with valid template
    template = "{{ args.input_file }}"
    result = template_engine.process_template(template, variables)
    assert result == "input.txt"

    # Cache should have one entry
    info = template_engine.get_cache_info()
    assert info["currsize"] == 1


def test_process_template_simple(template_engine, variables):
    """Test simple variable substitution."""
    template = "Input file: {{ args.input_file }}"
    result = template_engine.process_template(template, variables)
    assert result == "Input file: input.txt"


def test_process_template_nested(template_engine, variables):
    """Test nested variable access."""
    template = "Step output: {{ steps.step1.output }}"
    result = template_engine.process_template(template, variables)
    assert result == "Step output: step1 output"


def test_process_template_invalid_attribute(template_engine, variables):
    """Test error on invalid attribute access."""
    template = "{{ args.input_file.invalid }}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Variable 'args.input_file.invalid' is undefined" in error_msg
    assert "str" in error_msg  # Shows that args.input_file is a string


def test_process_value_string(template_engine, variables):
    """Test processing string value."""
    value = "File: {{ args.input_file }}"
    result = template_engine.process_value(value, variables)
    assert result == "File: input.txt"


def test_process_value_dict(template_engine, variables):
    """Test processing dictionary value."""
    value = {
        "file": "{{ args.input_file }}",
        "path": "{{ env.HOME }}"
    }
    result = template_engine.process_value(value, variables)
    assert result == {
        "file": "input.txt",
        "path": "/home/user"
    }


def test_process_value_list(template_engine, variables):
    """Test processing list value."""
    value = ["{{ args.input_file }}", "{{ env.HOME }}"]
    result = template_engine.process_value(value, variables)
    assert result == ["input.txt", "/home/user"]


def test_process_value_non_template(template_engine, variables):
    """Test processing non-template value."""
    value = 42
    result = template_engine.process_value(value, variables)
    assert result == 42


def test_get_available_variables(template_engine, variables):
    """Test getting available variables."""
    available = template_engine.get_available_variables(variables)
    assert set(available.keys()) == {"args", "env", "steps", "root"}
    assert "input_file" in available["args"]
    assert "output_file" in available["args"]
    assert "HOME" in available["env"]
    assert "PATH" in available["env"]
    assert "step1" in available["steps"]
    assert "workflow_name" in available["root"]


def test_template_caching(template_engine, variables):
    """Test that templates are properly cached."""
    # Process same template multiple times
    template = "File: {{ args.input_file }}"
    for _ in range(3):
        result = template_engine.process_template(template, variables)
        assert result == "File: input.txt"
    
    # Check cache info
    cache_info = template_engine.get_cache_info()
    assert cache_info["hits"] >= 2  # First call is a miss, subsequent calls are hits
    assert cache_info["misses"] == 1
    assert cache_info["maxsize"] == 128


def test_cache_different_templates(template_engine, variables):
    """Test caching with different templates."""
    templates = [
        "File: {{ args.input_file }}",
        "Mode: {{ env.PATH }}",
        "Step: {{ steps.step1.output }}"
    ]
    
    # Process each template twice
    for template in templates:
        template_engine.process_template(template, variables)
        template_engine.process_template(template, variables)
    
    cache_info = template_engine.get_cache_info()
    assert cache_info["hits"] == 3  # One hit per template
    assert cache_info["misses"] == 3  # One miss per template
    assert cache_info["currsize"] == 3


def test_cache_clear(template_engine, variables):
    """Test clearing the template cache."""
    template = "File: {{ args.input_file }}"
    
    # Process template twice to ensure it's cached
    template_engine.process_template(template, variables)
    template_engine.process_template(template, variables)
    
    # Check cache hits
    cache_info = template_engine.get_cache_info()
    assert cache_info["hits"] == 1
    
    # Clear cache
    template_engine.clear_cache()
    
    # Process template again
    template_engine.process_template(template, variables)
    
    # Check that it was a cache miss
    cache_info = template_engine.get_cache_info()
    assert cache_info["hits"] == 0
    assert cache_info["misses"] == 1


def test_cache_size_limit(template_engine, variables):
    """Test that cache respects size limit."""
    # Create a template engine with small cache
    small_cache_engine = TemplateEngine(cache_size=2)
    
    # Process three different templates
    templates = [
        "One: {{ args.input_file }}",
        "Two: {{ env.PATH }}",
        "Three: {{ steps.step1.output }}"
    ]
    
    for template in templates:
        small_cache_engine.process_template(template, variables)
    
    # Check cache size
    cache_info = small_cache_engine.get_cache_info()
    assert cache_info["currsize"] <= 2  # Cache should not exceed size limit


def test_cache_with_invalid_template(template_engine, variables):
    """Test caching behavior with invalid templates."""
    # Try processing invalid template
    with pytest.raises(TemplateError):
        template_engine.process_template("{{ invalid.variable }}", variables)
    
    # Cache should not store failed templates
    cache_info = template_engine.get_cache_info()
    assert cache_info["currsize"] == 0 