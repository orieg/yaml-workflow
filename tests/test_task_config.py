import pytest
from pathlib import Path

from yaml_workflow.tasks import TaskConfig
from yaml_workflow.exceptions import TemplateError


@pytest.fixture
def task_config(temp_workspace):
    """Create a task config for testing."""
    return TaskConfig(
        {
            "name": "test_task",
            "task": "shell",
            "inputs": {
                "command": "echo 'Hello {{ args.name }}'",
                "working_dir": "{{ env.WORKSPACE }}",
                "env": {
                    "PATH": "{{ env.PATH }}",
                    "USER": "{{ env.USER }}"
                }
            }
        },
        {
            "args": {"name": "World"},
            "env": {
                "WORKSPACE": "/tmp",
                "PATH": "/usr/bin",
                "USER": "test"
            },
            "steps": {}
        },
        temp_workspace
    )


def test_task_config_initialization(task_config):
    """Test TaskConfig initialization."""
    assert task_config.name == "test_task"
    assert task_config.type == "shell"
    assert isinstance(task_config.inputs, dict)
    assert isinstance(task_config.workspace, Path)


def test_task_config_namespace_access(task_config):
    """Test variable access from different namespaces."""
    assert task_config.get_variable("name", "args") == "World"
    assert task_config.get_variable("PATH", "env") == "/usr/bin"
    assert task_config.get_variable("nonexistent", "args") is None
    assert task_config.get_variable("nonexistent") is None


def test_task_config_available_variables(task_config):
    """Test getting available variables by namespace."""
    variables = task_config.get_available_variables()
    assert "args" in variables
    assert "env" in variables
    assert "steps" in variables
    assert "name" in variables["args"]
    assert "PATH" in variables["env"]
    assert isinstance(variables["steps"], list)


def test_task_config_process_inputs(task_config):
    """Test processing inputs with template resolution."""
    processed = task_config.process_inputs()
    assert processed["command"] == "echo 'Hello World'"
    assert processed["working_dir"] == "/tmp"
    assert processed["env"]["PATH"] == "/usr/bin"
    assert processed["env"]["USER"] == "test"


def test_task_config_undefined_variable():
    """Test handling of undefined variables."""
    config = TaskConfig(
        {
            "name": "test_undefined",
            "task": "shell",
            "inputs": {
                "command": "echo '{{ undefined_var }}'"
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        Path("/tmp")
    )
    
    with pytest.raises(TemplateError) as exc:
        config.process_inputs()
    assert "undefined_var" in str(exc.value)
    assert "Available variables" in str(exc.value)


def test_task_config_invalid_namespace():
    """Test handling of invalid namespace access."""
    config = TaskConfig(
        {
            "name": "test_invalid",
            "task": "shell",
            "inputs": {
                "command": "echo '{{ invalid.var }}'"
            }
        },
        {"args": {}, "env": {}, "steps": {}},
        Path("/tmp")
    )
    
    with pytest.raises(TemplateError) as exc:
        config.process_inputs()
    assert "invalid" in str(exc.value)
    assert "namespace" in str(exc.value).lower()


def test_task_config_nested_variables(task_config):
    """Test handling of nested variable access."""
    config = TaskConfig(
        {
            "name": "test_nested",
            "task": "shell",
            "inputs": {
                "command": "echo '{{ args.user.name }}'",
                "env": {
                    "HOME": "{{ env.paths.home }}"
                }
            }
        },
        {
            "args": {"user": {"name": "test"}},
            "env": {"paths": {"home": "/home/test"}},
            "steps": {}
        },
        Path("/tmp")
    )
    
    processed = config.process_inputs()
    assert processed["command"] == "echo 'test'"
    assert processed["env"]["HOME"] == "/home/test"


def test_task_config_step_outputs(task_config):
    """Test access to step outputs."""
    config = TaskConfig(
        {
            "name": "test_steps",
            "task": "shell",
            "inputs": {
                "command": "cat {{ steps.previous.output_file }}"
            }
        },
        {
            "args": {},
            "env": {},
            "steps": {
                "previous": {
                    "output_file": "/tmp/output.txt",
                    "status": "completed"
                }
            }
        },
        Path("/tmp")
    )
    
    processed = config.process_inputs()
    assert processed["command"] == "cat /tmp/output.txt"


def test_task_config_complex_template(task_config):
    """Test processing of complex template expressions."""
    config = TaskConfig(
        {
            "name": "test_complex",
            "task": "shell",
            "inputs": {
                "command": """
                    {% if env.DEBUG %}
                    echo 'Debug: {{ args.message }}'
                    {% else %}
                    echo '{{ args.message }}'
                    {% endif %}
                """.strip()
            }
        },
        {
            "args": {"message": "Hello"},
            "env": {"DEBUG": True},
            "steps": {}
        },
        Path("/tmp")
    )
    
    processed = config.process_inputs()
    assert "Debug: Hello" in processed["command"] 