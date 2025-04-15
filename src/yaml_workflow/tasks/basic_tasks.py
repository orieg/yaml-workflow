"""
Basic task functions for demonstration and testing.
"""

from typing import Dict, Any
from jinja2 import Template, StrictUndefined, UndefinedError

from ..exceptions import TemplateError
from . import register_task


def echo(message: str) -> str:
    """
    Echo back the input message.

    Args:
        message: Message to echo

    Returns:
        str: The input message
    """
    return message


def fail(message: str = "Task failed") -> None:
    """
    A task that always fails.

    Args:
        message: Error message

    Raises:
        RuntimeError: Always raises this error
    """
    raise RuntimeError(message)


def hello_world(name: str = "World") -> str:
    """
    A simple hello world function.

    Args:
        name: Name to include in greeting. Defaults to "World".

    Returns:
        str: The greeting message
    """
    return f"Hello, {name}!"


def add_numbers(a: float, b: float) -> float:
    """
    Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        float: Sum of the numbers
    """
    return a + b


def join_strings(*strings: str, separator: str = " ") -> str:
    """
    Join multiple strings together.

    Args:
        *strings: Variable number of strings to join
        separator: String to use as separator. Defaults to space.

    Returns:
        str: Joined string
    """
    return separator.join(strings)


def create_greeting(name: str, context: Dict[str, Any]) -> str:
    """
    Create a greeting message.

    Args:
        name: Name to greet
        context: Template context

    Returns:
        str: Greeting message

    Raises:
        TemplateError: If template resolution fails
    """
    try:
        template = Template("Hello {{ name }}!", undefined=StrictUndefined)
        return template.render(name=name, **context)
    except UndefinedError as e:
        available = {
            "name": name,
            "args": list(context["args"].keys()) if "args" in context else [],
            "env": list(context["env"].keys()) if "env" in context else [],
            "steps": list(context["steps"].keys()) if "steps" in context else []
        }
        raise TemplateError(f"{str(e)}. Available variables: {available}")
    except Exception as e:
        raise TemplateError(f"Failed to create greeting: {str(e)}")
