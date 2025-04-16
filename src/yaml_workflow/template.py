"""Template engine implementation for YAML workflow."""

from typing import Any, Dict, List, Optional
from jinja2 import Environment, StrictUndefined, Template, UndefinedError, TemplateSyntaxError

from .exceptions import TemplateError


class TemplateEngine:
    """Template engine for processing Jinja2 templates with workflow context."""
    
    def __init__(self) -> None:
        """Initialize template engine with strict undefined handling."""
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=True
        )
    
    def process_template(self, template: str, context: Dict[str, Any]) -> str:
        """Process template with workflow context.
        
        Args:
            template: Template string to process
            context: Context dictionary containing variables
            
        Returns:
            str: Processed template string
            
        Raises:
            TemplateError: If template processing fails
        """
        try:
            template_obj = self.env.from_string(template)
            return template_obj.render(**context)
        except UndefinedError as e:
            # Extract variable name from error message
            error_str = str(e)
            if "'is undefined'" in error_str:
                # Handle direct undefined variable
                var_parts = error_str.split("'")
                var_name = var_parts[1] if len(var_parts) > 1 else "unknown"
            else:
                # Handle attribute error
                var_parts = template.split("{{")[1].split("}}")[0].strip().split(".")
                var_name = ".".join(var_parts)
            
            namespace = var_name.split('.')[0] if '.' in var_name else None
            
            # Get available variables with types
            available = self._get_variables_with_types(context)
            
            # Build helpful error message
            msg = f"Variable '{var_name}' is undefined."
            if namespace and namespace in available:
                msg += f"\nAvailable variables in '{namespace}' namespace: {available[namespace]}"
            msg += f"\nAll available variables: {available}"
            
            raise TemplateError(msg)
        except TemplateSyntaxError as e:
            # Provide line and column information for syntax errors
            msg = f"Template syntax error at line {e.lineno}"
            if e.filename:
                msg += f" in {e.filename}"
            msg += f": {e.message}"
            raise TemplateError(msg)
        except Exception as e:
            raise TemplateError(f"Failed to process template '{template}': {str(e)}")
            
    def process_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Process any value that might contain templates.
        
        Args:
            value: Value to process
            context: Context dictionary containing variables
            
        Returns:
            Any: Processed value
        """
        if isinstance(value, str) and ("{{" in value or "{%" in value):
            return self.process_template(value, context)
        elif isinstance(value, dict):
            return {k: self.process_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.process_value(v, context) for v in value]
        return value
    
    def get_available_variables(self, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get list of available variables in context.
        
        Args:
            context: Context dictionary containing variables
            
        Returns:
            Dict[str, List[str]]: Dictionary of available variables by namespace
        """
        return {
            "args": list(context.get("args", {}).keys()),
            "env": list(context.get("env", {}).keys()),
            "steps": list(context.get("steps", {}).keys()),
            "root": [k for k in context.keys() if k not in ["args", "env", "steps"]]
        }
    
    def _get_variables_with_types(self, context: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Get available variables with their types.
        
        Args:
            context: Context dictionary containing variables
            
        Returns:
            Dict[str, Dict[str, str]]: Dictionary of variables and their types by namespace
        """
        def get_type_info(value: Any) -> str:
            if isinstance(value, dict):
                return f"dict[{len(value)} items]"
            elif isinstance(value, list):
                return f"list[{len(value)} items]"
            elif isinstance(value, str):
                return f"str[{len(value)} chars]"
            return type(value).__name__
        
        result = {}
        
        # Get args variables with types
        if "args" in context:
            result["args"] = {
                k: get_type_info(v) for k, v in context["args"].items()
            }
            
        # Get env variables with types
        if "env" in context:
            result["env"] = {
                k: get_type_info(v) for k, v in context["env"].items()
            }
            
        # Get step outputs with types
        if "steps" in context:
            result["steps"] = {
                k: get_type_info(v) for k, v in context["steps"].items()
            }
            
        # Get root variables with types
        result["root"] = {
            k: get_type_info(v) for k, v in context.items()
            if k not in ["args", "env", "steps"]
        }
        
        return result 