from pathlib import Path

import pytest

from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.template_tasks import render_template


@pytest.fixture
def template_context():
    """Create a sample template context."""
    return {
        "name": "Test User",
        "items": ["item1", "item2", "item3"],
        "settings": {"color": "blue", "size": "large"},
    }


def test_simple_template_rendering(temp_workspace):
    """Test basic template rendering."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {"template": "Hello, {{ name }}!", "output_file": "greeting.txt"},
    }

    config = TaskConfig(step, {"name": "Alice"}, temp_workspace)
    result = render_template(config)

    output_file = temp_workspace / "greeting.txt"
    assert output_file.exists()
    assert output_file.read_text() == "Hello, Alice!"


def test_template_with_loops(temp_workspace, template_context):
    """Test template rendering with loops."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {
            "template": """Items:
{% for item in items %}
- {{ item }}
{% endfor %}""",
            "output_file": "items.txt",
        },
    }

    config = TaskConfig(step, template_context, temp_workspace)
    result = render_template(config)

    output_file = temp_workspace / "items.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert "item1" in content
    assert "item2" in content
    assert "item3" in content


def test_template_with_conditionals(temp_workspace, template_context):
    """Test template rendering with conditional statements."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {
            "template": """
{% if settings.color == 'blue' %}
Color is blue
{% else %}
Color is not blue
{% endif %}

{% if settings.size == 'large' %}
Size is large
{% endif %}
""",
            "output_file": "settings.txt",
        },
    }

    config = TaskConfig(step, template_context, temp_workspace)
    result = render_template(config)

    output_file = temp_workspace / "settings.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert "Color is blue" in content
    assert "Size is large" in content


def test_template_filters(temp_workspace):
    """Test template rendering with filters."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {
            "template": """
{{ name | upper }}
{{ name | lower }}
{{ items | join(', ') }}
{{ number | float | round(2) }}
""",
            "output_file": "filtered.txt",
        },
    }

    config = TaskConfig(
        step,
        {"name": "Alice", "items": ["a", "b", "c"], "number": 3.14159},
        temp_workspace,
    )
    result = render_template(config)

    output_file = temp_workspace / "filtered.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert "ALICE" in content
    assert "alice" in content
    assert "a, b, c" in content
    assert "3.14" in content


def test_template_error_handling(temp_workspace):
    """Test template error handling."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {"template": "{{ undefined_variable }}", "output_file": "error.txt"},
    }

    config = TaskConfig(step, {}, temp_workspace)
    with pytest.raises(Exception):
        render_template(config)


def test_template_whitespace_control(temp_workspace):
    """Test template whitespace control."""
    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {
            "template": "{{ items|join('\n') }}",
            "output_file": "whitespace.txt",
        },
    }

    config = TaskConfig(step, {"items": ["a", "b", "c"]}, temp_workspace)
    result = render_template(config)

    output_file = temp_workspace / "whitespace.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert content == "a\nb\nc"


def test_template_from_file(temp_workspace):
    """Test loading template from a file."""
    # Create template file
    template_file = temp_workspace / "template.txt"
    template_file.write_text("Welcome, {{ name }}!\nYour role is: {{ role }}")

    step = {
        "name": "test_template",
        "task": "template",
        "inputs": {
            "template": template_file.read_text(),  # Read template content directly since render_template doesn't support template_file
            "output_file": "welcome.txt",
        },
    }

    config = TaskConfig(step, {"name": "Bob", "role": "Admin"}, temp_workspace)
    result = render_template(config)

    output_file = temp_workspace / "welcome.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert "Welcome, Bob!" in content
    assert "Your role is: Admin" in content


def test_template_with_includes(temp_workspace):
    """Test template rendering with includes."""
    # Create included template directly in workspace
    header_file = temp_workspace / "header.txt"
    header_file.write_text("Welcome to {{ app_name }}")

    step = {
        "name": "test_include",
        "task": "template",
        "inputs": {
            "template": "{% include 'header.txt' %}\nContent for {{ user }}",
            "output_file": "page.txt",
        },
    }

    # Define the context needed for the templates
    context = {"app_name": "My App", "user": "Alice"}
    config = TaskConfig(step, context, temp_workspace)

    # Call render_template with the config
    result = render_template(config)

    output_file = temp_workspace / "page.txt"
    assert output_file.exists()
    content = output_file.read_text()
    assert "Welcome to My App" in content
    assert "Content for Alice" in content
