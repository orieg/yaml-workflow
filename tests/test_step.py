import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from yaml_workflow.exceptions import TaskExecutionError  # May need this later
from yaml_workflow.step import Step
from yaml_workflow.template import TemplateEngine, TemplateError


# Fixture for a TemplateEngine instance
@pytest.fixture
def template_engine():
    return TemplateEngine()


# Fixture for basic step data
@pytest.fixture
def basic_step_data():
    return {"name": "test_step", "task": "shell", "inputs": {"command": "echo hello"}}


# Fixture for basic context
@pytest.fixture
def basic_context():
    return {
        "args": {"arg1": "val1"},
        "env": {"ENV_VAR": "env_val"},
        "steps": {"prev_step": {"result": "prev_result"}},
        "workflow_name": "Test Workflow",
        "workspace": "/fake/workspace",
        "output": "/fake/workspace/output",
    }


# Fixture for mock workspace and output dirs
@pytest.fixture
def mock_dirs(tmp_path):
    workspace = tmp_path / "workspace"
    output = tmp_path / "output"
    # No need to create them, Step doesn't directly interact with them
    return workspace, output


# --- Initial tests for __init__ ---


def test_step_init_basic(basic_step_data, basic_context, mock_dirs, template_engine):
    """Test basic Step initialization."""
    workspace_dir, output_dir = mock_dirs
    step = Step(
        basic_step_data, basic_context, workspace_dir, output_dir, template_engine
    )

    assert step.name == "test_step"
    assert step.task == "shell"
    assert step.inputs == {"command": "echo hello"}
    assert step.condition is None
    assert step.on_error == {}  # Default
    assert step.context == basic_context
    assert step.workspace_dir == workspace_dir
    assert step.output_dir == output_dir
    assert step.template_engine == template_engine


def test_step_init_on_error_dict(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test Step initialization with on_error as a dictionary."""
    step_data = basic_step_data.copy()
    on_error_config = {"action": "continue", "message": "Step failed: {{ error }}"}
    step_data["on_error"] = on_error_config
    workspace_dir, output_dir = mock_dirs

    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    assert step.on_error == on_error_config


def test_step_init_on_error_string(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test Step initialization with on_error as a string."""
    step_data = basic_step_data.copy()
    step_data["on_error"] = "continue"
    workspace_dir, output_dir = mock_dirs

    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    # Should be normalized to a dict
    assert step.on_error == {"action": "continue"}


def test_step_init_on_error_invalid(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test Step initialization with an invalid on_error type."""
    step_data = basic_step_data.copy()
    step_data["on_error"] = 123  # Invalid type
    workspace_dir, output_dir = mock_dirs

    with caplog.at_level(logging.WARNING):
        step = Step(
            step_data, basic_context, workspace_dir, output_dir, template_engine
        )

    # Should default to empty dict and log a warning
    assert step.on_error == {}
    assert "Invalid type for on_error" in caplog.text
    assert "Defaulting to 'fail'" in caplog.text


# --- Tests for evaluate_condition ---


def test_evaluate_condition_no_condition(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test evaluate_condition returns True when no condition is set."""
    workspace_dir, output_dir = mock_dirs
    step = Step(
        basic_step_data, basic_context, workspace_dir, output_dir, template_engine
    )
    assert step.evaluate_condition() is True


def test_evaluate_condition_true(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test evaluate_condition evaluates a true condition."""
    step_data = basic_step_data.copy()
    step_data["condition"] = "{{ args.arg1 == 'val1' }}"  # Should be True
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    assert step.evaluate_condition() is True


def test_evaluate_condition_false(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test evaluate_condition evaluates a false condition."""
    step_data = basic_step_data.copy()
    step_data["condition"] = "{{ args.arg1 == 'wrong_val' }}"  # Should be False
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    assert step.evaluate_condition() is False


def test_evaluate_condition_template_error(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test evaluate_condition handles TemplateError during evaluation."""
    step_data = basic_step_data.copy()
    step_data["condition"] = "{{ undefined_var }}"  # Will raise TemplateError
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    with caplog.at_level(logging.WARNING):
        result = step.evaluate_condition()

    assert result is False  # Should return False on template error
    assert "Could not resolve condition" in caplog.text
    assert "Skipping step" in caplog.text


def test_evaluate_condition_other_exception(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test evaluate_condition handles other exceptions during evaluation."""
    step_data = basic_step_data.copy()
    # Malformed template that might cause non-TemplateError in Jinja or processing
    step_data["condition"] = "{{ args.arg1 | non_existent_filter }}"
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    # Mock the template engine to raise a generic Exception
    mock_engine = MagicMock(spec=TemplateEngine)
    mock_engine.process_template.side_effect = Exception("Generic processing error")
    step.template_engine = mock_engine  # Replace engine with mock

    with caplog.at_level(logging.WARNING):
        result = step.evaluate_condition()

    assert result is False  # Should return False on other exceptions
    assert "Unexpected error evaluating condition" in caplog.text
    assert "Skipping step" in caplog.text


# --- Tests for render_inputs ---


def test_render_inputs_simple(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test render_inputs with simple templates."""
    step_data = basic_step_data.copy()
    step_data["inputs"] = {
        "command": "echo {{ args.arg1 }}",
        "fixed": "some_string",
        "env_val": "{{ env.ENV_VAR }}",
    }
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    rendered = step.render_inputs()
    assert rendered["command"] == "echo val1"
    assert rendered["fixed"] == "some_string"  # Non-templates should pass through
    assert rendered["env_val"] == "env_val"


def test_render_inputs_nested(
    basic_step_data, basic_context, mock_dirs, template_engine
):
    """Test render_inputs with nested structures."""
    step_data = basic_step_data.copy()
    step_data["inputs"] = {
        "config": {
            "user": "{{ args.arg1 }}",
            "port": 8080,  # Numbers should pass through
            "settings": [
                "a",
                "{{ env.ENV_VAR }}",
                {"nested_key": "{{ steps.prev_step.result }}"},
            ],
        },
        "another_input": "{{ workflow_name }}",
    }
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    rendered = step.render_inputs()
    assert rendered["config"]["user"] == "val1"
    assert rendered["config"]["port"] == 8080
    assert rendered["config"]["settings"][0] == "a"
    assert rendered["config"]["settings"][1] == "env_val"
    assert rendered["config"]["settings"][2]["nested_key"] == "prev_result"
    assert rendered["another_input"] == "Test Workflow"


def test_render_inputs_template_error(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test render_inputs raises TemplateError correctly."""
    step_data = basic_step_data.copy()
    step_data["inputs"] = {"bad_input": "{{ undefined_var }}"}
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(TemplateError) as excinfo:
            step.render_inputs()

    assert "Template error rendering inputs" in caplog.text
    assert "undefined_var" in str(excinfo.value)


def test_render_inputs_other_exception(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test render_inputs handles other exceptions during rendering."""
    step_data = basic_step_data.copy()
    step_data["inputs"] = {"problem": "{{ args.arg1 | non_existent_filter }}"}
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)

    # Mock the template engine's process_value to raise a generic Exception
    mock_engine = MagicMock(spec=TemplateEngine)
    mock_engine.process_value.side_effect = Exception("Generic processing error")
    step.template_engine = mock_engine

    with caplog.at_level(logging.ERROR):
        with pytest.raises(TemplateError) as excinfo:
            step.render_inputs()

    assert "Unexpected error rendering inputs" in caplog.text
    # Check that the original exception is wrapped in TemplateError
    assert "Generic processing error" in str(excinfo.value)
    assert isinstance(excinfo.value.original_error, Exception)


# --- Tests for handle_error ---


def test_handle_error_fail_default(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test handle_error with default action (fail)."""
    workspace_dir, output_dir = mock_dirs
    # on_error defaults to {} -> action defaults to 'fail'
    step = Step(
        basic_step_data, basic_context, workspace_dir, output_dir, template_engine
    )
    error = ValueError("Something broke")

    with caplog.at_level(logging.ERROR):
        result = step.handle_error(error, basic_context)

    assert result["success"] is False
    assert "Error in step 'test_step': Something broke" in result["message"]
    assert f"Step '{step.name}' failed: {result['message']}" in caplog.text


def test_handle_error_continue(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test handle_error with 'continue' action."""
    step_data = basic_step_data.copy()
    step_data["on_error"] = {"action": "continue"}
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    error = ValueError("Something broke")

    with caplog.at_level(logging.WARNING):
        result = step.handle_error(error, basic_context)

    assert result["success"] is True  # Handled, so success is True for runner
    assert "Error in step 'test_step': Something broke" in result["message"]
    assert (
        f"Step '{step.name}' failed but workflow continues: {result['message']}"
        in caplog.text
    )


def test_handle_error_custom_message(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test handle_error with a custom message template."""
    step_data = basic_step_data.copy()
    step_data["on_error"] = {
        "action": "fail",
        "message": "Custom error in {{ args.arg1 }} for step {{ name }}: {{ error }}",
    }
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    error = ValueError("Original error detail")

    with caplog.at_level(logging.ERROR):
        result = step.handle_error(error, basic_context)

    assert result["success"] is False
    expected_message = "Custom error in val1 for step test_step: Original error detail"
    assert result["message"] == expected_message
    assert f"Step '{step.name}' failed: {expected_message}" in caplog.text


def test_handle_error_custom_message_render_fail(
    basic_step_data, basic_context, mock_dirs, template_engine, caplog
):
    """Test handle_error when the custom message template fails to render."""
    step_data = basic_step_data.copy()
    step_data["on_error"] = {
        "action": "fail",
        # This template will fail because 'undefined_var' is not in context
        "message": "Error for {{ undefined_var }}: {{ error }}",
    }
    workspace_dir, output_dir = mock_dirs
    step = Step(step_data, basic_context, workspace_dir, output_dir, template_engine)
    error = ValueError("Original error detail")

    with caplog.at_level(logging.WARNING):  # Template failure logged as warning
        result = step.handle_error(error, basic_context)

    assert result["success"] is False  # Step still fails overall
    # Check that the message falls back to the default format
    assert "Error in step 'test_step': Original error detail" in result["message"]
    assert "(failed to render custom message)" in result["message"]
    assert "Failed to render custom error message" in caplog.text
