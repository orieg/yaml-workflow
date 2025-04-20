import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Remove old import
# from .template import TemplateError, render_template
# Import TemplateEngine
from .template import TemplateEngine, TemplateError

logger = logging.getLogger(__name__)


class Step:
    """Represents a single step in the workflow."""

    def __init__(
        self,
        step_data: dict,
        context: dict,
        workspace_dir: Path,
        output_dir: Path,
        template_engine: TemplateEngine,  # Add template_engine parameter
    ):
        self.data = step_data
        self.context = context
        self.workspace_dir = workspace_dir
        self.output_dir = output_dir
        self.template_engine = template_engine  # Store the engine instance
        self.name = step_data.get("name", "Unnamed Step")
        self.task = step_data.get("task", "")
        self.inputs = step_data.get("inputs", {})
        self.condition = step_data.get("condition")

        # Normalize on_error
        on_error_config = step_data.get("on_error", {})  # Default to empty dict
        if isinstance(on_error_config, str):
            # If it's just a string (like 'continue'), normalize it
            self.on_error = {"action": on_error_config}
        elif isinstance(on_error_config, dict):
            self.on_error = on_error_config
        else:
            # Invalid type, default to standard failure
            logger.warning(
                f"Invalid type for on_error in step '{self.name}': "
                f"{type(on_error_config).__name__}. Defaulting to 'fail'."
            )
            self.on_error = {}

    def evaluate_condition(self) -> bool:
        """Evaluate the step's condition."""
        if not self.condition:
            return True
        try:
            # Use the stored template engine instance
            resolved_condition = self.template_engine.process_template(
                str(self.condition), self.context
            )
            # Ensure strict boolean interpretation
            return str(resolved_condition).strip().lower() == "true"
        except TemplateError as e:
            logger.warning(
                f"Could not resolve condition for step '{self.name}': {e}. Skipping step."
            )
            return False
        except Exception as e:
            logger.warning(
                f"Unexpected error evaluating condition for step '{self.name}': {e}. Skipping step."
            )
            return False

    def render_inputs(self) -> dict:
        """Render input values using the template engine."""
        try:
            # Use the stored template engine instance
            return self.template_engine.process_value(self.inputs, self.context)
        except TemplateError as e:
            logger.error(f"Template error rendering inputs for step '{self.name}': {e}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error rendering inputs for step '{self.name}': {e}"
            )
            raise TemplateError(
                f"Unexpected error rendering inputs: {e}", original_error=e
            )

    def handle_error(self, error: Exception, context: dict) -> dict:
        """Handle errors based on the on_error configuration."""
        action = self.on_error.get("action", "fail")
        message_template = self.on_error.get("message")

        # Ensure error and step name are in context for message rendering
        error_context = {**context, "error": str(error), "name": self.name}

        final_message = f"Error in step '{self.name}': {error}"
        if message_template:
            try:
                # Use the stored template engine instance
                final_message = self.template_engine.process_template(
                    message_template, error_context
                )
            except Exception as template_err:
                logger.warning(
                    f"Failed to render custom error message for step '{self.name}': {template_err}"
                )
                final_message = f"Error in step '{self.name}': {error} (failed to render custom message)"

        if action == "continue":
            logger.warning(
                f"Step '{self.name}' failed but workflow continues: {final_message}"
            )
            return {"success": True, "message": final_message}  # Indicate handled
        else:  # Default to fail
            logger.error(f"Step '{self.name}' failed: {final_message}")
            return {"success": False, "message": final_message}
