"""
Basic task functions for demonstration and testing.
"""


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


def create_greeting(template: str = "Hello, {{ name }}!", **kwargs) -> str:
    """
    Create a greeting using a template and keyword arguments.

    Args:
        template: Template string with placeholders. Defaults to "Hello, {{ name }}!"
        **kwargs: Keyword arguments to fill template placeholders

    Returns:
        str: Formatted greeting
    """
    from jinja2 import Template

    return Template(template).render(**kwargs)
