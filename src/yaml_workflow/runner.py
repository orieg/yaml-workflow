import io  # Add io import
import json
import logging
import os
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout  # Add contextlib imports
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .step import Step
from .tasks import TaskConfig, get_task_handler
from .template import TemplateEngine, TemplateError

logger = logging.getLogger(__name__)


def run_workflow(
    workflow_file: Path | str,
    args: dict | None = None,
    workspace_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    config_file: Path | str | None = None,
) -> dict:
    """Runs a workflow defined in a YAML file.

    Args:
        workflow_file: Path to the workflow YAML file.
        args: Dictionary of arguments to pass to the workflow.
        workspace_dir: Directory for temporary files and logs.
        output_dir: Directory for final output files.
        config_file: Path to a custom configuration file.

    Returns:
        A dictionary containing the workflow result:
            {"success": bool, "message": str, "stdout": str, "stderr": str}
    """
    workflow_file = Path(workflow_file)
    if not workflow_file.exists():
        return {
            "success": False,
            "message": f"Workflow file not found: {workflow_file}",
            "stdout": "",
            "stderr": "",
        }

    _workspace_dir = Path(workspace_dir) if workspace_dir else Path(".")
    _output_dir = Path(output_dir) if output_dir else _workspace_dir / "output"
    log_dir = _workspace_dir / "logs"

    # Create directories if they don't exist
    _workspace_dir.mkdir(parents=True, exist_ok=True)
    _output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # --- Setup Logging ---
    log_file = (
        log_dir
        / f"workflow_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}.log"
    )
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s.%(funcName)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add handler to the root logger to capture logs from all modules
    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicate logs if run multiple times
    # Note: This is simplistic; consider more robust handler management
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)  # Capture DEBUG level and above in the file

    # Add a basic console handler for INFO level
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # console_handler.setFormatter(formatter)
    # root_logger.addHandler(console_handler)
    # --- End Logging Setup ---

    logger.info(f"Starting workflow: {workflow_file.name}")
    logger.info(f"Workspace: {_workspace_dir}")
    logger.info(f"Output Dir: {_output_dir}")
    logger.info(f"Arguments: {args}")

    try:
        with open(workflow_file, "r") as f:
            workflow_data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading workflow file: {e}")
        return {
            "success": False,
            "message": f"Error loading workflow file: {e}",
            "stdout": "",
            "stderr": str(e),
        }

    workflow_name = workflow_data.get("name", "Unnamed Workflow")
    workflow_steps = workflow_data.get("steps", [])

    context = {
        "workflow_name": workflow_name,
        "workspace": str(_workspace_dir),
        "output": str(_output_dir),
        "args": args or {},
        "steps": {},
        "env": os.environ.copy(),
    }

    template_engine = TemplateEngine()

    final_status = {
        "success": True,
        "message": "Workflow completed successfully",
        "stdout": "",
        "stderr": "",
    }
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Redirect stdout/stderr for the duration of step execution
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        for i, step_data in enumerate(workflow_steps):
            step_name = step_data.get("name", f"step_{i+1}")
            logger.info(
                f"--- Running Step: {step_name} ({i+1}/{len(workflow_steps)}) ---"
            )
            context["current_step"] = step_name

            step = Step(
                step_data, context, _workspace_dir, _output_dir, template_engine
            )

            try:
                should_run = step.evaluate_condition()
                if not should_run:
                    logger.info(f"Skipping step: {step_name} due to condition.")
                    context["steps"][step_name] = {"skipped": True, "result": None}
                    continue

                logger.debug(f"Step '{step_name}' inputs before render: {step.inputs}")
                rendered_inputs = step.render_inputs()
                logger.debug(
                    f"Step '{step_name}' inputs after render: {rendered_inputs}"
                )

                task_func = get_task_handler(step.task)
                if not task_func:
                    raise ValueError(f"Unknown task type: {step.task}")

                logger.debug(f"Executing task: {step.task} for step: {step_name}")

                task_config = TaskConfig(
                    step=step_data,
                    context=context,
                    workspace=_workspace_dir,
                )
                result = task_func(task_config)
                logger.info(f"Step '{step_name}' completed successfully.")
                logger.debug(f"Step '{step_name}' result: {result}")
                context["steps"][step_name] = {"skipped": False, "result": result}

            except TemplateError as e:
                logger.error(
                    f"Template error in step '{step_name}': {e}", exc_info=True
                )
                step_error_status = step.handle_error(e, context)
                if step_error_status["success"] is False:
                    # Only update final_status and break if action was 'fail'
                    final_status = step_error_status
                    logger.error(
                        f"Workflow aborted due to error in step '{step_name}'."
                    )
                    break
                else:
                    # Action was 'continue', log warning but don't change final_status message
                    logger.warning(
                        f"Step '{step_name}' failed but workflow continues: {step_error_status['message']}"
                    )
                    context["steps"][step_name] = {
                        "skipped": False,
                        "error": str(e),  # Log the original error for the step
                        "result": None,
                    }
                    # Keep final_status['success'] = True and original message

            except Exception as e:
                logger.error(f"Error executing step '{step_name}': {e}", exc_info=True)
                step_error_status = step.handle_error(e, context)
                if step_error_status["success"] is False:
                    # Only update final_status and break if action was 'fail'
                    final_status = step_error_status
                    logger.error(
                        f"Workflow aborted due to error in step '{step_name}'."
                    )
                    break
                else:
                    # Action was 'continue', log warning but don't change final_status message
                    logger.warning(
                        f"Step '{step_name}' failed but workflow continues: {step_error_status['message']}"
                    )
                    context["steps"][step_name] = {
                        "skipped": False,
                        "error": str(e),  # Log the original error for the step
                        "result": None,
                    }
                    # Keep final_status['success'] = True and original message

            finally:
                del context["current_step"]  # Clean up current step context

        if final_status["success"]:
            logger.info("Workflow finished successfully.")
        else:
            logger.error(f"Workflow finished with errors: {final_status['message']}")

    # Capture stdout/stderr after the context manager exits
    final_status["stdout"] = stdout_capture.getvalue()
    final_status["stderr"] = stderr_capture.getvalue()

    # --- Cleanup Logging ---
    # It might be better to close/remove handlers if the runner is long-lived
    # For simple script execution, this might not be strictly necessary
    # root_logger.removeHandler(file_handler)
    # root_logger.removeHandler(console_handler)
    # file_handler.close()
    # --- End Cleanup Logging ---

    return final_status


# Helper function (consider moving to utils)
def find_latest_log(log_dir: Path) -> Path | None:
    log_files = list(log_dir.glob("workflow_*.log"))
    if not log_files:
        return None
    return max(log_files, key=lambda p: p.stat().st_mtime)
