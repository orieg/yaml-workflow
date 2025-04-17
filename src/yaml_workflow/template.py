"""Template engine implementation using Jinja2."""
from typing import Any, Dict, Iterator, Tuple
import re
from jinja2 import Environment, StrictUndefined, Template
from jinja2.exceptions import UndefinedError, TemplateSyntaxError

from .exceptions import TemplateError


class AttrDict(dict):
    """A dictionary that allows attribute access to its keys."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for k, v in list(super().items()):
            if isinstance(v, dict) and not isinstance(v, AttrDict):
                self[k] = AttrDict(v)
            elif isinstance(v, (list, tuple)):
                self[k] = [AttrDict(i) if isinstance(i, dict) else i for i in v]

    def __getattr__(self, key: str) -> Any:
        try:
            # Always check the dictionary first
            if key in self:
                return self[key]
            # If the key doesn't exist, try to get it as a method
            if key in dir(dict):
                method = getattr(super(), key)
                # If it's a callable method, call it immediately
                if callable(method):
                    result = method()
                    return result
                return method
            raise KeyError(key)
        except KeyError as e:
            raise AttributeError(key)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def items(self):
        """Override items to ensure it returns a list of tuples."""
        return list(super().items())


class TemplateEngine:
    """Template engine for processing Jinja2 templates."""

    def __init__(self):
        """Initialize the template engine with strict undefined behavior."""
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def _extract_variable_path(self, template_str: str, error_msg: str) -> str:
        """Extract the full variable path from the template string.
        
        Args:
            template_str: The template string being processed
            error_msg: The error message from Jinja2
            
        Returns:
            str: The full variable path
        """
        # Extract the undefined variable name from the error message
        if "'is undefined'" in error_msg:
            var_name = error_msg.split("'")[1]
        else:
            # Handle attribute error
            var_parts = error_msg.split("'")
            if len(var_parts) >= 2:
                var_name = var_parts[-2]
            else:
                var_name = "unknown"

        # Find the variable in the template string
        pattern = r'{{\s*([^}]+)\s*}}'
        matches = re.findall(pattern, template_str)
        for match in matches:
            if var_name in match:
                return match.strip()
        return var_name

    def process_template(self, template_str: str, variables: Dict[str, Any] = None) -> Any:
        """Process a template string with the given variables.
        
        Args:
            template_str (str): The template string to process.
            variables (dict, optional): Variables to use in template processing.
                Defaults to None.
        
        Returns:
            Any: The processed template value, preserving the original type.
        
        Raises:
            TemplateError: If there is an error processing the template.
        """
        try:
            # If the template is just a variable reference, try to return the raw value
            if template_str.strip().startswith('{{') and template_str.strip().endswith('}}'):
                var_path = template_str.strip()[2:-2].strip()
                if '.' in var_path:
                    parts = var_path.split('.')
                    current = variables
                    for part in parts:
                        if current is None or not isinstance(current, dict):
                            break
                        current = current.get(part)
                    if current is not None:
                        return current

            # Create a new template with the configured environment
            template = self.env.from_string(template_str)
            
            # Convert variables to AttrDict for proper attribute access
            context = AttrDict(variables or {})
            
            # Process the template with the wrapped variables
            return template.render(**context)

        except UndefinedError as e:
            # Get the full variable path from the template
            var_path = self._extract_variable_path(template_str, str(e))
            parts = var_path.split('.')

            # Handle invalid namespace
            if len(parts) > 0:
                namespace = parts[0]
                if namespace not in variables:
                    error_msg = (
                        f"Template error: Invalid namespace '{namespace}'\n"
                        f"Available namespaces:\n"
                    )
                    for ns in sorted(variables.keys()):
                        if isinstance(variables[ns], dict):
                            error_msg += f"  - {ns}\n"
                    raise TemplateError(error_msg)

                # Handle invalid attribute access
                if len(parts) > 2:
                    try:
                        current = variables[namespace]
                        for part in parts[1:-1]:
                            current = current[part]
                        error_msg = (
                            f"Template error: Invalid attribute '{parts[-1]}' on {type(current).__name__}\n"
                            f"Type of '{'.'.join(parts[:-1])}' is '{type(current).__name__}'"
                        )
                        raise TemplateError(error_msg)
                    except (KeyError, AttributeError):
                        pass

                # Handle undefined variable in namespace
                error_msg = (
                    f"Template error: Undefined variable '{var_path}'\n"
                    f"Available variables in '{namespace}' namespace:\n"
                )
                if namespace in variables and isinstance(variables[namespace], dict):
                    for key in sorted(variables[namespace].keys()):
                        error_msg += f"  - {key}\n"
                raise TemplateError(error_msg)

            # Handle root level undefined variable
            error_msg = f"Template error: Undefined variable '{var_path}'\n"
            if variables:
                error_msg += "Available variables:\n"
                for key in sorted(variables.keys()):
                    error_msg += f"  - {key}\n"
            raise TemplateError(error_msg)

        except TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error: {str(e)}")
        except Exception as e:
            raise TemplateError(f"Error processing template: {str(e)}")

    def process_value(self, value: Any, variables: Dict[str, Any]) -> Any:
        """Process a value that may contain templates.

        Args:
            value: The value to process
            variables: Dictionary of variables to use in template processing

        Returns:
            Any: The processed value
        """
        if isinstance(value, str):
            return self.process_template(value, variables)
        elif isinstance(value, dict):
            return {k: self.process_value(v, variables) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.process_value(item, variables) for item in value]
        return value 