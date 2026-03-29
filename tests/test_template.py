"""Tests for template engine."""

import pytest

from yaml_workflow.exceptions import TemplateError
from yaml_workflow.template import AttrDict, TemplateEngine


@pytest.fixture
def template_engine():
    """Create a template engine instance."""
    return TemplateEngine()


@pytest.fixture
def variables():
    """Create test variables."""
    return {
        "args": {"input_file": "input.txt", "output_file": "output.txt"},
        "env": {"HOME": "/home/user", "PATH": "/usr/bin:/bin"},
        "steps": {"step1": {"output": "step1 output"}},
        "batch": {"item": {"id": 1, "name": "test"}, "index": 0, "name": "batch_task"},
        "workflow_name": "test_workflow",
        "workspace": "/tmp/workspace",
        "run_number": "1",
        "timestamp": "2024-03-20T12:00:00",
        "workflow_file": "workflow.yaml",
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
    assert "Template error: Invalid namespace 'args[\"missing\"]'" in error_msg
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
    assert (
        'Template error: Invalid namespace \'args["input_file"]["invalid"]\''
        in error_msg
    )
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
    assert "Template error: Invalid namespace 'invalid[\"variable\"]'" in error_msg
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
    value = {"file": '{{ args["input_file"] }}', "path": '{{ env["HOME"] }}'}
    result = template_engine.process_value(value, variables)
    assert result == {"file": "input.txt", "path": "/home/user"}


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


def test_attrdict_method_access(template_engine):
    """Test accessing dictionary methods via attribute access."""
    data = {"a": 1, "b": 2}
    context = AttrDict(data)
    assert list(context.items()) == [("a", 1), ("b", 2)]
    assert list(context.keys()) == ["a", "b"]
    assert list(context.values()) == [1, 2]


def test_attrdict_attribute_error(template_engine):
    """Test accessing a non-existent attribute raises AttributeError."""
    data = {"a": 1}
    context = AttrDict(data)
    with pytest.raises(AttributeError) as exc:
        _ = context.non_existent
    assert "non_existent" in str(exc.value)


def test_attrdict_set_attribute(template_engine):
    """Test setting an attribute directly on AttrDict."""
    data = {"a": 1}
    context = AttrDict(data)
    context.b = 2
    assert context["b"] == 2
    assert context.b == 2


def test_process_template_with_none_variables(template_engine):
    """Test processing template when variables is None."""
    template = "Test"
    result = template_engine.process_template(template, None)
    assert result == "Test"
    # Test with undefined variable when context is None
    template_undef = "{{ undefined_var }}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template_undef, None)
    error_msg = str(exc.value)
    assert "Template error: Invalid namespace 'undefined_var'" in error_msg
    assert "Available namespaces:" in error_msg


def test_process_template_error_invalid_namespace(template_engine):
    """Test detailed error message for invalid namespace."""
    template = "{{ invalid.foo }}"
    variables = {"valid": {"bar": 1}}
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Template error: Invalid namespace 'invalid'" in error_msg
    assert "Available namespaces:" in error_msg
    assert "- valid" in error_msg


def test_process_template_error_invalid_attribute_access_missing(template_engine):
    """Test error message when accessing missing attribute in dict."""
    template = "{{ steps.foo.missing }}"
    variables = {"steps": {"foo": {"bar": 1}}}
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Template error: Invalid attribute 'missing' on dict" in error_msg
    assert "Type of 'steps.foo' is 'dict'" in error_msg


def test_process_template_error_undefined_root_variable(template_engine):
    """Test error message for undefined root variable."""
    template = "{{ undefined_root }}"
    variables = {"root_var": 1}
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Template error: Invalid namespace 'undefined_root'" in error_msg
    assert "Available namespaces:" in error_msg


def test_process_template_syntax_error_explicit(template_engine):
    """Test explicitly catching TemplateSyntaxError."""
    template = "{% bad tag %}"
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, {})
    assert "Template syntax error:" in str(exc.value)
    assert "Encountered unknown tag 'bad'." in str(exc.value)  # Check Jinja's message


# --- AttrDict edge case tests ---


def test_attrdict_nested_dict_conversion():
    """Test that nested dicts are automatically converted to AttrDict."""
    data = {"outer": {"inner": {"deep": "value"}}}
    ad = AttrDict(data)
    assert isinstance(ad["outer"], AttrDict)
    assert isinstance(ad["outer"]["inner"], AttrDict)
    assert ad.outer.inner.deep == "value"


def test_attrdict_tuple_with_dicts():
    """Test that dicts inside tuples are converted to AttrDict."""
    data = {"items": ({"name": "x"}, "plain")}
    ad = AttrDict(data)
    assert isinstance(ad["items"][0], AttrDict)
    assert ad["items"][0].name == "x"
    assert ad["items"][1] == "plain"


def test_attrdict_items_override():
    """Test that the items() override returns list of tuples."""
    ad = AttrDict({"x": 10, "y": 20})
    result = ad.items()
    assert isinstance(result, list)
    assert set(result) == {("x", 10), ("y", 20)}


def test_attrdict_missing_key_raises_attribute_error():
    """Test that accessing a completely missing key raises AttributeError (line 37-39)."""
    ad = AttrDict({"a": 1})
    with pytest.raises(AttributeError, match="nonexistent"):
        _ = ad.nonexistent


# --- Template variable extraction edge cases ---


def test_extract_variable_path_is_undefined_message(template_engine):
    """Test _extract_variable_path when error contains the 'is undefined' pattern (line 75)."""
    # Directly test _extract_variable_path with a message containing "'is undefined'"
    # The code checks for the literal substring "'is undefined'" in the error msg.
    # When matched, it extracts the var name as error_msg.split("'")[1].
    result = template_engine._extract_variable_path(
        "{{ myvar }}", "'myvar'is undefined'"
    )
    # split("'") -> ['', 'myvar', 'is undefined', ''] -> [1] = 'myvar'
    # Then 'myvar' is found in template match 'myvar', so return 'myvar'
    assert result == "myvar"


def test_extract_variable_path_attribute_error_short(template_engine):
    """Test _extract_variable_path with error where var_parts < 2 (line 82)."""
    # Test the private method directly with an error message that has fewer than 2 parts
    # when split on single quotes.
    result = template_engine._extract_variable_path("{{ x }}", "some error no quotes")
    # split("'") produces ["some error no quotes"] - length 1, so var_name = "unknown"
    # Then search for "unknown" in "{{ x }}" - "unknown" is NOT in "x", so return "unknown"
    assert result == "unknown"


def test_extract_variable_path_no_match_in_template(template_engine):
    """Test _extract_variable_path when var_name is not found in template matches (line 90)."""
    # The error message references a var name that is not in the template string
    result = template_engine._extract_variable_path(
        "{{ something }}", "'str object' has no attribute 'unrelated_var'"
    )
    # var_name = var_parts[-2] = "unrelated_var" (from the attribute error format)
    # "unrelated_var" is NOT in "something", so return "unrelated_var"
    assert result == "unrelated_var"


# --- Process template error paths ---


def test_process_template_root_undefined_with_available_vars(template_engine):
    """Test root-level undefined variable with available variables (lines 203-208)."""
    # This requires len(parts) == 0, which happens when var_path has no dots.
    # But len(parts) > 0 always for a non-empty string. We need the namespace
    # check to fail in a specific way. Let's test the actual code path:
    # When parts[0] is not in vars_dict, we get the "Invalid namespace" error.
    # Lines 203-208 are reached only when len(parts) == 0, which means var_path is empty.
    # This is effectively unreachable in normal flow, but let's verify the namespace path.
    template = "{{ unknown_var }}"
    variables = {"known_var": 42, "other_var": "hello"}
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Invalid namespace 'unknown_var'" in error_msg
    assert "Available namespaces:" in error_msg


def test_process_template_type_error(template_engine):
    """Test TypeError catch during template processing (line 212-213)."""
    # Trigger a TypeError by providing a value that causes issues in rendering
    # One way: use a filter that gets a wrong type
    template = "{{ items | join(',') }}"
    variables = {"items": 42}  # join expects iterable, not int
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    assert "Error processing template:" in error_msg or "Template error:" in error_msg


def test_process_template_deep_nested_attribute_missing_key(template_engine):
    """Test deep nested attribute access where intermediate key is missing (line 189-190)."""
    template = "{{ ns.a.b.c }}"
    variables = {"ns": {"a": {"x": 1}}}  # 'b' doesn't exist under 'a'
    with pytest.raises(TemplateError) as exc:
        template_engine.process_template(template, variables)
    error_msg = str(exc.value)
    # Should fall through the KeyError catch and give undefined variable message
    assert "Undefined variable" in error_msg


def test_process_template_searchpath(template_engine, tmp_path):
    """Test process_template with searchpath parameter."""
    # Create a template file in the searchpath
    template_file = tmp_path / "partial.txt"
    template_file.write_text("included content")

    template = "Result: {% include 'partial.txt' %}"
    result = template_engine.process_template(template, {}, searchpath=str(tmp_path))
    assert "included content" in result


def test_process_template_raw_value_with_dot_path(template_engine):
    """Test that raw value is returned for simple variable reference with dot path."""
    template = "{{ data.nested }}"
    variables = {"data": {"nested": [1, 2, 3]}}
    result = template_engine.process_template(template, variables)
    assert result == [1, 2, 3]


def test_process_template_raw_value_dot_path_none_intermediate(template_engine):
    """Test dot path resolution when intermediate value is None."""
    template = "{{ data.missing.deep }}"
    variables = {"data": {"other": "val"}}
    # This will fail because data.missing is None/missing
    with pytest.raises(TemplateError):
        template_engine.process_template(template, variables)
