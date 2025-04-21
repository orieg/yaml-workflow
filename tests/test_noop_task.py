from pathlib import Path
from typing import Any, Dict

import pytest

from yaml_workflow.exceptions import TaskExecutionError, TemplateError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.noop import noop_task


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Create a temporary workspace for testing."""
    return tmp_path


@pytest.fixture
def basic_context() -> Dict[str, Any]:
    """Create a basic context with namespaces."""
    return {
        "args": {
            "test_arg": "value1",
            "debug": True,
            "items": ["apple", "banana", "cherry"],
            "count": 3,
        },
        "env": {"test_env": "value2"},
        "steps": {"previous_step": {"output": "value3"}},
        "root_var": "value4",
    }


def test_noop_basic(workspace, basic_context):
    """Test basic noop task functionality."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {"message": "Hello World", "number": 42},
    }

    config = TaskConfig(step, basic_context, workspace)
    result = noop_task(config)

    assert result["task_name"] == "test_noop"
    assert result["task_type"] == "noop"
    assert result["processed_inputs"]["message"] == "Hello World"
    assert result["processed_inputs"]["number"] == 42

    # Verify available variables
    vars = result["available_variables"]
    assert "args" in vars
    assert "env" in vars
    assert "steps" in vars
    assert "root" in vars


def test_noop_template_resolution(workspace, basic_context):
    """Test template resolution in inputs."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {
            "arg_value": "{{ args.test_arg }}",
            "env_value": "{{ env.test_env }}",
            "step_value": "{{ steps.previous_step.output }}",
            "root_value": "{{ root_var }}",
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    result = noop_task(config)
    processed = result["processed_inputs"]

    assert processed["arg_value"] == "value1"
    assert processed["env_value"] == "value2"
    assert processed["step_value"] == "value3"
    assert processed["root_value"] == "value4"


def test_noop_instruct_conditional(workspace, basic_context):
    """Test conditional logic using standard Jinja2 syntax."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {
            "debug_status": """
                {% if args.debug %}
                Debug mode is ON
                {% else %}
                Debug mode is OFF
                {% endif %}
            """,
            "item_count": """
                {% set count = args.count %}
                Total items: {{ count }}
            """,
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    result = noop_task(config)
    processed = result["processed_inputs"]

    assert processed["debug_status"].strip() == "Debug mode is ON"
    assert processed["item_count"].strip() == "Total items: 3"


def test_noop_instruct_list_processing(workspace, basic_context):
    """Test list processing using standard Jinja2 syntax."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {
            "processed_items": """
                {% for item in args["items"] %}
                Item {{ loop.index }}: {{ item }}
                {% endfor %}
            """.strip()
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    result = noop_task(config)
    processed = result["processed_inputs"]

    expected = "\n".join(
        [
            "                Item 1: apple",
            "                Item 2: banana",
            "                Item 3: cherry",
        ]
    )
    assert processed["processed_items"].strip() == expected.strip()


def test_noop_error_handling(workspace, basic_context):
    """Test error handling when should_fail is True."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {"should_fail": True, "message": "This task will fail"},
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        noop_task(config)

    assert "Task failed as requested" in str(exc_info.value)
    assert exc_info.value.step_name == "test_noop"


def test_noop_undefined_variable(workspace, basic_context):
    """Test error handling for undefined template variables."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {"undefined": "{{ args.nonexistent }}"},
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        noop_task(config)

    assert "nonexistent" in str(exc_info.value)


def test_noop_instruct_error_handling(workspace, basic_context):
    """Test error handling in templates."""
    step = {
        "name": "test_noop",
        "task": "noop",
        "inputs": {
            "error_prone": """
                {{ args.nonexistent }}
            """
        },
    }

    config = TaskConfig(step, basic_context, workspace)
    with pytest.raises(TaskExecutionError) as exc_info:
        noop_task(config)

    error_msg = str(exc_info.value)
    assert "args.nonexistent" in error_msg
    assert "Available variables in 'args' namespace:" in error_msg
