"""
Basic task functions for demonstration and testing.
"""

from typing import Any, Dict

from jinja2 import StrictUndefined, Template, UndefinedError

from ..exceptions import TemplateError
from . import register_task


@register_task()
def echo(message: str) -> str:
    """
    Echo back the input message.

    Args:
        message: Message to echo

    Returns:
        str: The input message
    """
    return message


@register_task()
def fail(message: str = "Task failed") -> None:
    """
    A task that always fails.

    Args:
        message: Error message

    Raises:
        RuntimeError: Always raises this error
    """
    raise RuntimeError(message)


@register_task()
def hello_world(name: str = "World") -> str:
    """
    A simple hello world function.

    Args:
        name: Name to include in greeting. Defaults to "World".

    Returns:
        str: The greeting message
    """
    return f"Hello, {name}!"


@register_task()
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


@register_task()
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


@register_task()
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
    except Exception as e:
        raise TemplateError(f"Failed to create greeting: {str(e)}")
