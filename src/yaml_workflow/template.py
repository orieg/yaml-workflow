"""Template engine implementation using Jinja2."""
from typing import Any, Dict, Iterator, Tuple
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
                # print(f"DEBUG: Accessing key '{key}' with value: {self[key]}")
                return self[key]
            # If the key doesn't exist, try to get it as a method
            if key in dir(dict):
                # print(f"DEBUG: Accessing dict method '{key}' on AttrDict")
                method = getattr(super(), key)
                # If it's a callable method, call it immediately
                if callable(method):
                    result = method()
                    # print(f"DEBUG: Method result: {result}")
                    return result
                return method
            # print(f"DEBUG: Key '{key}' not found")
            raise KeyError(key)
        except KeyError as e:
            # print(f"DEBUG: KeyError accessing '{key}': {str(e)}")
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

    def process_template(self, template_str: str, variables: Dict[str, Any] = None) -> str:
        """Process a template string with the given variables.
        
        Args:
            template_str (str): The template string to process.
            variables (dict, optional): Variables to use in template processing.
                Defaults to None.
        
        Returns:
            str: The processed template string.
        
        Raises:
            TemplateError: If there is an error processing the template.
        """
        try:
            # Create a new template with the configured environment
            template = self.env.from_string(template_str)
            
            # Convert variables to AttrDict for proper attribute access
            context = AttrDict(variables or {})
            # print(f"\nDEBUG: Template context:")
            # for k, v in context.items():
            #     print(f"  {k}: {type(v)} = {v}")
            # if 'args' in context:
            #     print("\nDEBUG: Args content:")
            #     for k, v in context['args'].items():
            #         print(f"  {k}: {type(v)} = {v}")
            
            # Process the template with the wrapped variables
            return template.render(**context)

        except UndefinedError as e:
            # Extract the undefined variable name from the error message
            error_msg = str(e)
            if "'is undefined'" in error_msg:
                var_name = error_msg.split("'")[1]
            else:
                # Handle attribute error (e.g., 'dict object' has no attribute 'nonexistent')
                var_parts = error_msg.split("'")
                if len(var_parts) >= 2:
                    var_name = var_parts[-2]
                else:
                    var_name = "unknown"

            # Get available variables in the relevant namespace
            if variables:
                # Extract namespace from template string
                for line in template_str.split('\n'):
                    if var_name in line:
                        # Look for namespace.variable pattern
                        parts = line.split('.')
                        if len(parts) > 1:
                            namespace = parts[0].split('{')[-1].strip()
                            var_name = f"{namespace}.{var_name}"
                            if namespace in variables:
                                error_msg = (
                                    f"Undefined variable '{var_name}'.\n"
                                    f"Available variables in '{namespace}' namespace:\n"
                                )
                                for key in sorted(variables[namespace].keys()):
                                    error_msg += f"  - {namespace}.{key}\n"
                                raise TemplateError(error_msg)
                            break

            # If no namespace found or no variables provided
            error_msg = f"Undefined variable '{var_name}'.\nAvailable variables:\n"
            if variables:
                for key in sorted(variables.keys()):
                    error_msg += f"  - {key}\n"
            raise TemplateError(error_msg)

        except TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error: {str(e)}")
        except Exception as e:
            # print(f"\nDEBUG: Exception during template processing: {type(e)} - {str(e)}")
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