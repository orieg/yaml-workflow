"""Template engine implementation using Jinja2."""
from functools import lru_cache
import hashlib
from typing import Any, Dict, Optional
from jinja2 import Environment, StrictUndefined, Template, TemplateError as Jinja2TemplateError
from jinja2.exceptions import UndefinedError, TemplateSyntaxError

from .exceptions import TemplateError


class TemplateEngine:
    """Process Jinja2 templates with caching."""

    def __init__(self, cache_size: int = 128):
        """Initialize the template engine.

        Args:
            cache_size: Maximum number of templates to cache
        """
        self.env = Environment(undefined=StrictUndefined)
        self._compile_template = lru_cache(maxsize=cache_size)(self._compile_template_uncached)

    def _hash_template(self, template_str: str) -> str:
        """Create a hash for the template string.

        Args:
            template_str: Template string to hash

        Returns:
            str: Hash of the template string
        """
        return hashlib.sha256(template_str.encode()).hexdigest()

    def _compile_template_uncached(self, template_hash: str, template_str: str) -> Template:
        """Compile a template string into a Template object.

        Args:
            template_hash: Hash of the template string
            template_str: Template string to compile

        Returns:
            Template: Compiled template
        """
        try:
            return self.env.from_string(template_str)
        except TemplateSyntaxError as e:
            raise TemplateError(f"Template syntax error at line {e.lineno}: {str(e)}")
        except Jinja2TemplateError as e:
            raise TemplateError(f"Failed to compile template: {str(e)}")

    def _get_variables_with_types(self, variables: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Get variables with their types.

        Args:
            variables: Dictionary of variables
            prefix: Prefix for nested variables

        Returns:
            Dict[str, str]: Dictionary mapping variable names to their types
        """
        result = {}
        for key, value in variables.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                result[full_key] = f"dict[{len(value)} items]"
                nested = self._get_variables_with_types(value, f"{full_key}.")
                result.update(nested)
            elif isinstance(value, str):
                result[full_key] = f"str[{len(value)}]"
            else:
                result[full_key] = type(value).__name__
        return result

    def get_available_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Get available variables.

        Args:
            variables: Dictionary of variables

        Returns:
            Dict[str, Any]: Dictionary of available variables
        """
        root_vars = {
            "workflow_name": variables.get("workflow_name", ""),
            "workspace": variables.get("workspace", ""),
            "run_number": variables.get("run_number", ""),
            "timestamp": variables.get("timestamp", ""),
            "workflow_file": variables.get("workflow_file", "")
        }
        return {
            "args": variables.get("args", {}),
            "env": variables.get("env", {}),
            "steps": variables.get("steps", {}),
            "root": root_vars
        }

    def get_variables_with_types(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """Get variables with their types.

        Args:
            variables: Dictionary of variables

        Returns:
            Dict[str, str]: Dictionary mapping variable names to their types
        """
        return self._get_variables_with_types(variables)

    def process_template(self, template_str: str, variables: Dict[str, Any]) -> str:
        """Process a template string with the given variables.

        Args:
            template_str: The template string to process
            variables: Dictionary of variables to use in template processing

        Returns:
            str: The processed template string

        Raises:
            TemplateError: If there is an error processing the template
        """
        try:
            template_hash = self._hash_template(template_str)
            template = self._compile_template(template_hash, template_str)
            return template.render(**variables)
        except UndefinedError as e:
            # Clear cache for failed templates
            self._compile_template.cache_clear()
            
            # Extract variable name from error message
            error_str = str(e)
            if "'is undefined'" in error_str:
                # Handle direct undefined variable
                var_parts = error_str.split("'")
                var_name = var_parts[1] if len(var_parts) > 1 else "unknown"
            else:
                # Handle attribute error
                var_parts = template_str.split("{{")[1].split("}}")[0].strip().split(".")
                var_name = ".".join(var_parts)

            namespace = var_name.split('.')[0] if '.' in var_name else None

            # Get available variables with types
            available = self._get_variables_with_types(variables)

            # Build helpful error message
            msg = f"Variable '{var_name}' is undefined."
            if namespace and namespace in variables:
                namespace_vars = self._get_variables_with_types(variables[namespace])
                msg += f"\nAvailable variables in '{namespace}' namespace:"
                for var, type_name in namespace_vars.items():
                    msg += f"\n  '{var}': '{type_name}'"

            msg += "\nAll available variables:"
            for var, type_name in available.items():
                msg += f"\n  '{var}': '{type_name}'"

            raise TemplateError(msg)
        except TemplateSyntaxError as e:
            # Clear cache for failed templates
            self._compile_template.cache_clear()
            raise TemplateError(f"Template syntax error at line {e.lineno}: {str(e)}")

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

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._compile_template.cache_clear()

    def get_cache_info(self) -> Dict[str, int]:
        """Get information about the template cache.

        Returns:
            Dict[str, int]: Dictionary with cache statistics
        """
        info = self._compile_template.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize
        } 