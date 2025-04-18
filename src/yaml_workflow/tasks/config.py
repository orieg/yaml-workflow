"""
Configuration classes for task handlers with namespace support.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import UndefinedError

from ..exceptions import TemplateError
from ..template import TemplateEngine


class TaskConfig:
    """Configuration class for task handlers with namespace support."""

    def __init__(self, step: Dict[str, Any], context: Dict[str, Any], workspace: Path):
        """
        Initialize task configuration.

        Args:
            step: Step configuration from workflow
            context: Execution context with namespaces
            workspace: Workspace path
        """
        self.step = step  # Store the full step configuration
        self.name = step.get("name")
        self.type = step.get("task")
        self.inputs = step.get("inputs", {})
        self._context = context
        self.workspace = workspace
        self._processed_inputs: Dict[str, Any] = {}
        self._template_engine = TemplateEngine()

    def get_variable(self, name: str, namespace: Optional[str] = None) -> Any:
        """
        Get a variable with namespace support.

        Args:
            name: Variable name
            namespace: Optional namespace (args, env, steps)

        Returns:
            Any: Variable value if found
        """
        if namespace:
            return self._context.get(namespace, {}).get(name)
        return self._context.get(name)

    def get_available_variables(self) -> Dict[str, List[str]]:
        """
        Get available variables by namespace.

        Returns:
            Dict[str, List[str]]: Available variables in each namespace
        """
        return {
            "args": list(self._context.get("args", {}).keys()),
            "env": list(self._context.get("env", {}).keys()),
            "steps": list(self._context.get("steps", {}).keys()),
            "root": [
                k for k in self._context.keys() if k not in ["args", "env", "steps"]
            ],
        }

    def process_inputs(self) -> Dict[str, Any]:
        """
        Process task inputs with template resolution.

        Recursively processes all string values in the inputs dictionary,
        including nested dictionaries and lists.

        Returns:
            Dict[str, Any]: Processed inputs with resolved templates
        """
        if not self._processed_inputs:
            # Create a flattened context for template processing
            template_context = {
                "args": self._context.get("args", {}),
                "env": self._context.get("env", {}),
                "steps": self._context.get("steps", {}),
                **{
                    k: v
                    for k, v in self._context.items()
                    if k not in ["args", "env", "steps"]
                },
            }

            self._processed_inputs = self._process_value(self.inputs, template_context)
        return self._processed_inputs

    def _process_value(self, value: Any, template_context: Dict[str, Any]) -> Any:
        """
        Recursively process a value with template resolution.

        Args:
            value: Value to process
            template_context: Template context for variable resolution

        Returns:
            Any: Processed value with resolved templates
        """
        if isinstance(value, str):
            try:
                result = self._template_engine.process_template(value, template_context)
                # Try to convert string results back to their original type
                if result == "True":
                    return True
                elif result == "False":
                    return False
                try:
                    # First try to evaluate as a Python literal (for lists, dicts, etc.)
                    import ast

                    try:
                        return ast.literal_eval(result)
                    except (ValueError, SyntaxError):
                        # If not a valid Python literal, try numeric conversion
                        if "." in result:
                            return float(result)
                        return int(result)
                except (ValueError, TypeError, SyntaxError):
                    return result
            except UndefinedError as e:
                error_msg = str(e)
                namespace = self._get_undefined_namespace(error_msg)
                available = self.get_available_variables()
                raise TemplateError(
                    f"Template error: Undefined variable in namespace '{namespace}'. "
                    f"Error: {error_msg}. Available variables in '{namespace}' namespace: {available[namespace]}"
                )
        elif isinstance(value, dict):
            return {
                k: self._process_value(v, template_context) for k, v in value.items()
            }
        elif isinstance(value, list):
            return [self._process_value(item, template_context) for item in value]
        return value

    def _get_undefined_namespace(self, error_msg: str) -> str:
        """
        Extract namespace from undefined variable error.

        Args:
            error_msg: Error message from UndefinedError

        Returns:
            str: Namespace name or 'root' if not found
        """
        # Check for direct variable access pattern (e.g., args.undefined)
        for namespace in ["args", "env", "steps"]:
            if f"{namespace}." in error_msg:
                return namespace

        # Check for dictionary access pattern (e.g., 'dict object' has no attribute 'undefined')
        # Extract the undefined attribute name from the error message
        match = re.search(r"no attribute '(\w+)'", error_msg)
        if match:
            undefined_attr = match.group(1)
            # Find which namespace was trying to access this attribute
            for namespace in ["args", "env", "steps"]:
                if namespace in self._context:
                    template_str = next(
                        (
                            v
                            for v in self.inputs.values()
                            if isinstance(v, str)
                            and f"{namespace}.{undefined_attr}" in v
                        ),
                        "",
                    )
                    if template_str:
                        return namespace

        return "root"
