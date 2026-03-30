"""
Command-line interface for the workflow engine.
"""

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from . import __version__  # Import version
from .engine import WorkflowEngine
from .exceptions import WorkflowError
from .validator import WorkflowValidator
from .visualize import generate_mermaid, generate_text
from .workspace import get_workspace_info


class WorkflowArgumentParser(argparse.ArgumentParser):
    """Custom argument parser that handles workflow parameters."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow_params = []

    def error(self, message):
        """Custom error handling for workflow parameters."""
        if "unrecognized arguments" in message:
            # Check if the unrecognized argument is a parameter
            args = message.split(": ")[-1].split()
            for arg in args:
                # Skip standard flags like --version, --help
                if arg in ["--version", "--help"]:
                    super().error(message)
                    return
                if "=" in arg:
                    self.workflow_params.append(arg)
                else:
                    # If it's not a parameter, raise an error
                    print(
                        f"Invalid parameter format: {arg}\nParameters must be in the format: name=value",
                        file=sys.stderr,
                    )
                    sys.exit(1)
        else:
            super().error(message)

    def parse_args(self, args=None, namespace=None):
        """Parse arguments and collect workflow parameters."""
        self.workflow_params = []
        args = super().parse_args(args, namespace)
        if hasattr(args, "params"):
            args.params.extend(self.workflow_params)
        return args


def parse_params(args_list: List[str]) -> Dict[str, str]:
    """Parse command line parameters."""
    result = {}
    for arg in args_list:
        try:
            name, value = arg.split("=", 1)
            # Remove leading '--' if present
            name = name.lstrip("-")
            result[name.strip()] = value.strip()
        except ValueError:
            raise ValueError(
                f"Invalid parameter format: {arg}\nParameters must be in the format: name=value"
            )
    return result


def _get_watch_files(workflow_path: str) -> List[Path]:
    """Get the list of files to watch: workflow file plus any imports."""
    files = [Path(workflow_path).resolve()]
    try:
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)
        if isinstance(workflow, dict):
            for imp in workflow.get("imports", []):
                if isinstance(imp, str):
                    imp_path = imp
                elif isinstance(imp, dict):
                    imp_path = imp.get("path", "")
                else:
                    continue
                if imp_path:
                    resolved = (Path(workflow_path).parent / imp_path).resolve()
                    if resolved.exists():
                        files.append(resolved)
    except (yaml.YAMLError, OSError):
        pass
    return files


def _get_mtimes(files: List[Path]) -> Dict[str, float]:
    """Get modification times for a list of files."""
    mtimes = {}
    for f in files:
        try:
            mtimes[str(f)] = f.stat().st_mtime
        except OSError:
            pass
    return mtimes


def _run_with_watch(args) -> None:
    """Run a workflow in watch mode, re-executing on file changes."""
    watch_files = _get_watch_files(args.workflow)
    mtimes = _get_mtimes(watch_files)

    print(f"Watching {len(watch_files)} file(s) for changes. Press Ctrl+C to stop.\n")

    # First run
    try:
        _run_workflow_impl(args)
    except SystemExit:
        pass  # Don't exit on workflow errors in watch mode

    try:
        while True:
            time.sleep(1.5)
            new_mtimes = _get_mtimes(watch_files)
            if new_mtimes != mtimes:
                mtimes = new_mtimes
                # Re-scan imports (they may have changed)
                watch_files = _get_watch_files(args.workflow)
                mtimes = _get_mtimes(watch_files)

                now = datetime.now().strftime("%H:%M:%S")
                print(f"\n{'=' * 60}")
                print(f"  Re-running at {now} (file changed)")
                print(f"{'=' * 60}\n")

                try:
                    _run_workflow_impl(args)
                except SystemExit:
                    pass  # Don't exit on workflow errors in watch mode
    except KeyboardInterrupt:
        print("\nWatch mode stopped.")


def run_workflow(args):
    """Run a workflow."""
    if getattr(args, "watch", False):
        return _run_with_watch(args)

    _run_workflow_impl(args)


def _run_workflow_impl(args):
    """Run a workflow once (implementation used by both normal and watch mode)."""
    try:
        try:
            param_dict = parse_params(args.params)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        # If resuming, check the existing workspace and load metadata first
        resume_from = None
        metadata = None
        if args.resume and args.workspace:
            workspace_path = Path(args.workspace)
            if workspace_path.exists():
                metadata_path = workspace_path / ".workflow_metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path) as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Cannot resume: Invalid metadata file format - {str(e)}"
                        )
                    except OSError as e:
                        raise ValueError(
                            f"Cannot resume: Failed to read metadata file - {str(e)}"
                        )

                    # Ensure execution_state exists
                    if "execution_state" not in metadata:
                        raise ValueError(
                            "Cannot resume: Invalid metadata format - missing execution_state"
                        )

                    # Ensure retry_state exists
                    if "retry_state" not in metadata["execution_state"]:
                        metadata["execution_state"]["retry_state"] = {}

                    # Check if workflow is in failed state
                    if metadata["execution_state"].get("status") == "failed":
                        failed_step = metadata["execution_state"].get("failed_step")
                        if failed_step:
                            resume_from = failed_step["step_name"]
                            print(
                                f"Found failed workflow state, resuming from step: {resume_from}"
                            )
                        else:
                            raise ValueError("No failed step found to resume from.")
                    else:
                        raise ValueError(
                            "Cannot resume: workflow is not in failed state"
                        )
                else:
                    raise ValueError("Cannot resume: No workflow metadata found")
            else:
                raise ValueError("Cannot resume: Workspace directory not found")

        # Create workflow engine with loaded metadata
        engine = WorkflowEngine(
            workflow=args.workflow,
            workspace=args.workspace,
            base_dir=args.base_dir,
            metadata=metadata,  # Pass loaded metadata to engine
            dry_run=getattr(args, "dry_run", False),
        )

        # When using structured output, redirect all console logging to stderr
        # so only the JSON/YAML goes to stdout
        fmt = getattr(args, "format", "text")
        if fmt in ("json", "yaml"):
            for handler in logging.getLogger().handlers:
                if (
                    isinstance(handler, logging.StreamHandler)
                    and handler.stream is sys.stdout
                ):
                    handler.stream = sys.stderr

        # Update parameters
        if param_dict and not getattr(args, "dry_run", False):
            print(
                "Parameters provided:",
                file=sys.stderr if fmt in ("json", "yaml") else sys.stdout,
            )
            for name, value in param_dict.items():
                print(
                    f"  {name}: {value}",
                    file=sys.stderr if fmt in ("json", "yaml") else sys.stdout,
                )

        # Parse skip steps
        skip_step_list = []
        if args.skip_steps:
            skip_step_list = [step.strip() for step in args.skip_steps.split(",")]
            print(f"Skipping steps: {', '.join(skip_step_list)}")

        # Handle start-from and resume logic
        start_from_step = None

        # Check start-from first (takes precedence)
        if args.start_from:
            start_from_step = args.start_from
            print(f"Starting workflow from step: {start_from_step}")

        # Run workflow with appropriate parameters
        results = engine.run(
            param_dict,
            resume_from=resume_from,
            start_from=start_from_step,
            skip_steps=skip_step_list,
            flow=args.flow,
        )

        # In dry-run mode, the engine already printed the summary
        if not getattr(args, "dry_run", False):
            fmt = getattr(args, "format", "text")
            output_file = getattr(args, "output", None)

            if fmt in ("json", "yaml"):
                # Build structured result
                structured = {
                    "status": "success",
                    "workflow": engine.workflow.get("name", ""),
                    "workspace": str(engine.workspace),
                    "outputs": {},
                }

                # Extract step outputs
                if results and results.get("outputs"):
                    for step_name, step_data in results["outputs"].items():
                        if isinstance(step_data, dict) and "result" in step_data:
                            structured["outputs"][step_name] = step_data["result"]
                        else:
                            structured["outputs"][step_name] = step_data

                if fmt == "json":
                    import json as json_module

                    formatted = json_module.dumps(structured, indent=2, default=str)
                else:
                    formatted = yaml.dump(structured, default_flow_style=False)

                if output_file:
                    with open(output_file, "w") as f:
                        f.write(formatted)
                    print(f"Output written to: {output_file}", file=sys.stderr)
                else:
                    print(formatted)
            else:
                # Existing text output
                # Print completion status
                print("\n=== Workflow Status ===")
                if resume_from:
                    print(
                        f"✓ Workflow resumed from '{resume_from}' and completed successfully"
                    )
                elif start_from_step:
                    print(
                        f"✓ Workflow started from '{start_from_step}' and completed successfully"
                    )
                else:
                    print("✓ Workflow completed successfully")

                if skip_step_list:
                    print(f"• Skipped steps: {', '.join(skip_step_list)}")
                if args.flow:
                    print(f"• Flow executed: {args.flow}")

                # Print step outputs in a clean format
                if results.get("outputs"):
                    print("=== Step Outputs ===")
                    first_step = True
                    for step_name, output_container in results["outputs"].items():
                        output_value = output_container.get("result")
                        if output_value is None or (
                            isinstance(output_value, str) and not output_value.strip()
                        ):
                            continue
                        if first_step:
                            print(f"• {step_name}:")
                            first_step = False
                        else:
                            print(f"\n• {step_name}:")
                        if isinstance(output_value, str) and "\n" in output_value:
                            print(output_value)
                        elif isinstance(output_value, (dict, list)):
                            print(
                                yaml.dump(
                                    output_value,
                                    indent=2,
                                    default_flow_style=False,
                                )
                            )
                        else:
                            print(f"  {output_value}")

                print("\n=== Workspace Info ===")
                print(f"• Location: {engine.workspace}")
                run_number = engine.state.metadata.get("run_number", "unknown")
                print(f"• Run number: {run_number}")

    except (WorkflowError, Exception) as e:
        fmt = getattr(args, "format", "text")
        output_file = getattr(args, "output", None)

        if fmt in ("json", "yaml"):
            structured = {
                "status": "failed",
                "error": str(e),
            }

            if fmt == "json":
                import json as json_module

                formatted = json_module.dumps(structured, indent=2, default=str)
            else:
                formatted = yaml.dump(structured, default_flow_style=False)

            if output_file:
                with open(output_file, "w") as f:
                    f.write(formatted)
                print(f"Output written to: {output_file}", file=sys.stderr)
            else:
                print(formatted)
            sys.exit(1)
        else:
            if isinstance(e, WorkflowError):
                print(f"Workflow error: {str(e)}", file=sys.stderr)
            else:
                print(f"Error: {str(e)}", file=sys.stderr)
            sys.exit(1)


def list_workflows(args):
    """List available workflows."""
    workflow_dir = Path(args.base_dir)
    if not workflow_dir.exists():
        print(f"Directory not found: {workflow_dir}", file=sys.stderr)
        sys.exit(1)

    print("\nAvailable workflows:")
    # Recursively find all .yaml files
    found = False
    for workflow in sorted(workflow_dir.rglob("*.yaml")):
        try:
            # Try to load the file to verify it's a valid workflow
            with open(workflow) as f:
                content = yaml.safe_load(f)

                # Handle both top-level workflow and direct steps format
                if isinstance(content, dict):
                    if "workflow" in content:
                        content = content["workflow"]

                    # Check if it's a valid workflow file
                    if "steps" in content:
                        name = content.get("usage", {}).get("name") or workflow.stem
                        desc = content.get("usage", {}).get(
                            "description", "No description available"
                        )
                        print(f"\n- {workflow.relative_to(workflow_dir)}")
                        print(f"  Name: {name}")
                        print(f"  Description: {desc}")
                        found = True

        except (yaml.YAMLError, OSError):
            # Skip files that can't be parsed as YAML
            continue

    if not found:
        print(
            "No workflow files found. Workflows should be YAML files containing 'steps' section."
        )
        print(
            f"\nMake sure you have workflow YAML files in the '{workflow_dir}' directory."
        )
        print("You can specify a different directory with --base-dir option.")
    print()


def validate_workflow(args):
    """Validate a workflow file."""
    fmt = getattr(args, "format", "text")
    strict = getattr(args, "strict", False)

    validator = WorkflowValidator(args.workflow)
    result = validator.validate()
    # Use the parsed workflow from the validator (None if YAML was invalid)
    parsed_wf = validator._workflow

    if fmt == "json":
        print(json.dumps(result.to_dict(), indent=2))
        if not result.is_valid or (strict and result.warnings):
            sys.exit(1)
        return

    # --- Human-readable output ---
    print(f"\nValidating: {args.workflow}\n")

    # YAML syntax
    syntax_errors = [
        i
        for i in result.issues
        if "YAML syntax" in i.message
        or "File not found" in i.message
        or "Cannot read" in i.message
    ]
    if not syntax_errors:
        print("  \u2713 YAML syntax OK")
    else:
        for issue in syntax_errors:
            _print_issue(issue)

    # Only continue printing structural details when YAML is valid
    if parsed_wf is not None and isinstance(parsed_wf, dict):
        struct_issues = [
            i
            for i in result.issues
            if i not in syntax_errors and i.step is None and i.level == "error"
        ]
        if not struct_issues:
            print("  \u2713 Structure OK")
        else:
            for issue in struct_issues:
                _print_issue(issue)

        # Step uniqueness summary
        steps = parsed_wf.get("steps") or []
        step_count = len(steps) if isinstance(steps, (list, dict)) else 0

        dup_issues = [i for i in result.issues if "Duplicate step name" in i.message]
        if not dup_issues and step_count > 0:
            print(f"  \u2713 {step_count} step(s), all names unique")
        elif dup_issues:
            for issue in dup_issues:
                _print_issue(issue)

        # Flow references
        flow_ref_issues = [
            i
            for i in result.issues
            if "Flow '" in i.message
            and (
                "references step" in i.message
                or "definition must be" in i.message
                or "must have a 'steps'" in i.message
            )
        ]
        if not flow_ref_issues and parsed_wf.get("flows"):
            print("  \u2713 All flow references valid")
        else:
            for issue in flow_ref_issues:
                _print_issue(issue)

        # Per-step issues (task type warnings, double-result, param refs, missing task)
        already_shown = set(
            id(i) for i in syntax_errors + struct_issues + dup_issues + flow_ref_issues
        )
        step_issues = [i for i in result.issues if id(i) not in already_shown]
        for issue in step_issues:
            _print_issue(issue)

    print()

    error_count = len(result.errors)
    warning_count = len(result.warnings)

    effective_errors = error_count + (warning_count if strict else 0)

    if effective_errors == 0:
        if warning_count == 0:
            print("Validation passed with no issues.")
        else:
            plural_w = "warning" if warning_count == 1 else "warnings"
            print(f"Validation passed with 0 errors, {warning_count} {plural_w}.")
    else:
        plural_e = "error" if error_count == 1 else "errors"
        plural_w = "warning" if warning_count == 1 else "warnings"
        if strict and warning_count > 0:
            print(
                f"Validation failed (strict): {error_count} {plural_e}, {warning_count} {plural_w} (treated as errors)."
            )
        else:
            print(
                f"Validation failed: {error_count} {plural_e}, {warning_count} {plural_w}."
            )
        sys.exit(1)


def _print_issue(issue):
    """Print a single ValidationIssue in human-readable format."""
    if issue.level == "error":
        symbol = "\u2717"
    elif issue.level == "warning":
        symbol = "\u26a0"
    else:
        symbol = "\u2139"

    location = ""
    if issue.line:
        location = f"  (line {issue.line})"

    print(f"  {symbol} {issue.message}{location}")
    if issue.hint:
        print(f"    Hint: {issue.hint}")


def visualize_workflow(args):
    """Visualize a workflow as a diagram."""
    try:
        with open(args.workflow) as f:
            workflow = yaml.safe_load(f)

        fmt = getattr(args, "format", "text")
        if fmt == "mermaid":
            output = generate_mermaid(workflow, flow=args.flow)
        else:
            output = generate_text(workflow, flow=args.flow)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
            print(f"Diagram written to: {args.output}")
        else:
            print(output)
    except (yaml.YAMLError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def list_workspaces(args):
    """List workflow run directories."""
    base_dir_path = Path(args.base_dir)
    if not base_dir_path.exists():
        print(f"Base directory not found: {base_dir_path}", file=sys.stderr)
        sys.exit(1)

    # Get all run directories
    runs = []
    pattern = f"*_run_*" if not args.workflow else f"{args.workflow}_run_*"

    for run_dir in base_dir_path.glob(pattern):
        if run_dir.is_dir():
            try:
                info = get_workspace_info(run_dir)
                runs.append(
                    {
                        "name": run_dir.name,
                        "created": datetime.fromisoformat(info["created_at"]),
                        "size": info["size"],
                        "files": info["files"],
                    }
                )
            except (OSError, KeyError, ValueError) as e:
                print(f"Warning: Could not get info for {run_dir}: {e}")

    # Sort by creation time
    runs.sort(key=lambda x: x["created"], reverse=True)

    if not runs:
        print("No workflow runs found.")
        return

    print("\nWorkflow runs:")
    for run in runs:
        size_mb = run["size"] / (1024 * 1024)
        age = datetime.now() - run["created"]
        print(f"- {run['name']}")
        print(f"  Created: {run['created'].isoformat()} ({age.days} days ago)")
        print(f"  Size: {size_mb:.1f} MB")
        print(f"  Files: {run['files']}")
    print()


def clean_workspaces(args):
    """Clean up old workflow runs."""
    base_dir_path = Path(args.base_dir)
    if not base_dir_path.exists():
        print(f"Base directory not found: {base_dir_path}", file=sys.stderr)
        sys.exit(1)

    cutoff = datetime.now() - timedelta(days=args.older_than)
    pattern = f"*_run_*" if not args.workflow else f"{args.workflow}_run_*"

    to_delete = []
    for run_dir in base_dir_path.glob(pattern):
        if run_dir.is_dir():
            try:
                info = get_workspace_info(run_dir)
                created = datetime.fromisoformat(info["created_at"])
                if created < cutoff:
                    to_delete.append((run_dir, info))
            except (OSError, KeyError, ValueError) as e:
                print(f"Warning: Could not process {run_dir}: {e}", file=sys.stderr)

    if not to_delete:
        print("No old workflow runs to clean up.")
        return

    print("\nWorkflow runs to remove:")
    total_size = 0
    for run_dir, info in to_delete:
        size_mb = info["size"] / (1024 * 1024)
        total_size += info["size"]
        age = datetime.now() - datetime.fromisoformat(info["created_at"])
        print(f"- {run_dir.name}")
        print(f"  Age: {age.days} days")
        print(f"  Size: {size_mb:.1f} MB")

    total_size_mb = total_size / (1024 * 1024)
    print(f"\nTotal space to be freed: {total_size_mb:.1f} MB")

    if not args.dry_run:
        for run_dir, _ in to_delete:
            try:
                shutil.rmtree(run_dir)
                print(f"Removed: {run_dir}")
            except OSError as e:
                print(f"Error removing {run_dir}: {e}")
    else:
        print("\nDry run - no files were deleted")


def remove_workspaces(args):
    """Remove specific workflow runs."""
    base_dir_path = Path(args.base_dir)
    if not base_dir_path.exists():
        print(f"Base directory not found: {base_dir_path}", file=sys.stderr)
        sys.exit(1)

    to_remove = []
    for run_name in args.runs:
        run_dir = base_dir_path / run_name
        if not run_dir.exists():
            print(f"Warning: Run directory not found: {run_dir}")
            continue
        if not run_dir.is_dir():
            print(f"Warning: Not a directory: {run_dir}", file=sys.stderr)
            continue
        to_remove.append(run_dir)

    if not to_remove:
        print("No valid run directories to remove.")
        return

    print("\nWorkflow runs to remove:")
    total_size = 0
    for run_dir in to_remove:
        try:
            info = get_workspace_info(run_dir)
            size_mb = info["size"] / (1024 * 1024)
            total_size += info["size"]
            print(f"- {run_dir.name}")
            print(f"  Size: {size_mb:.1f} MB")
            print(f"  Files: {info['files']}")
        except (OSError, KeyError, ValueError) as e:
            print(f"Warning: Could not get info for {run_dir}: {e}")

    total_size_mb = total_size / (1024 * 1024)
    print(f"\nTotal space to be freed: {total_size_mb:.1f} MB")

    if not args.force:
        response = input("\nAre you sure you want to remove these runs? [y/N] ")
        if response.lower() != "y":
            print("Operation cancelled.")
            return

    for run_dir in to_remove:
        try:
            shutil.rmtree(run_dir)
            print(f"Removed: {run_dir}")
        except OSError as e:
            print(f"Error removing {run_dir}: {e}")


def init_project(args):
    """Initialize a new project with example workflows."""
    try:
        # Create target directory if it doesn't exist
        target_dir = Path(args.dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Find examples directory relative to this file's location
        # Assumes cli.py is in src/yaml_workflow/ and examples is in src/yaml_workflow/examples
        base_path = Path(__file__).parent
        examples_dir = base_path / "examples"  # Try direct relative path first

        # Fallback: If not found directly, try navigating up (e.g., running from source root)
        if not examples_dir.is_dir():
            project_root = base_path.parent  # src/yaml_workflow
            if (
                project_root.name == "yaml_workflow"
                and (project_root.parent / "src").exists()
            ):
                # If running from src/yaml_workflow, go up twice for project root
                examples_dir = (
                    project_root.parent / "src" / "yaml_workflow" / "examples"
                )
            else:
                # Assume current structure: src/yaml_workflow/cli.py -> src/yaml_workflow/examples
                pass  # Keep original examples_dir = base_path / "examples"

        if not examples_dir.is_dir():
            print(
                f"Error: Examples directory not found. Looked near: {base_path}",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.example:
            # Copy specific example
            example_file = examples_dir / f"{args.example}.yaml"
            if not example_file.exists():
                print(
                    f"Example '{args.example}' not found in {examples_dir}",
                    file=sys.stderr,
                )
                sys.exit(1)
            shutil.copy2(example_file, target_dir)
            print(
                f"Initialized project with example '{example_file.name}' in: {target_dir}"
            )
        else:
            # Copy all examples
            copied_any = False
            for example in examples_dir.glob("*.yaml"):
                shutil.copy2(example, target_dir)
                copied_any = True

            if not copied_any:
                print(
                    f"Warning: No example YAML files found in {examples_dir}",
                    file=sys.stderr,
                )
            else:
                print(f"Initialized project with examples in: {target_dir}")

    except OSError as e:
        print(f"Error initializing project: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = WorkflowArgumentParser(description="YAML Workflow Engine CLI")
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.description = f"""YAML Workflow Engine CLI v{__version__}

Commands:
  run                 Run a workflow
  list               List available workflows
  validate           Validate a workflow file
  visualize          Visualize a workflow as a Mermaid diagram
  workspace          Workspace management commands
  init               Initialize a new project with example workflows
  serve              Start web dashboard for monitoring and triggering workflows
  serve-mcp          Start MCP server exposing workflows as tools
"""
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a workflow", add_help=True)
    run_parser.add_argument("workflow", help="Path to workflow file")
    run_parser.add_argument("--workspace", help="Custom workspace directory")
    run_parser.add_argument(
        "--base-dir", default="runs", help="Base directory for workflow runs"
    )
    run_parser.add_argument(
        "--resume", action="store_true", help="Resume workflow from last failed step"
    )
    run_parser.add_argument(
        "--start-from", help="Start workflow execution from specified step"
    )
    run_parser.add_argument(
        "--skip-steps", help="Comma-separated list of steps to skip during execution"
    )
    run_parser.add_argument(
        "--flow",
        help="Name of the flow to execute (default: use flow specified in workflow file)",
    )
    run_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Validate and preview workflow without executing tasks",
    )
    run_parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="Watch workflow file for changes and re-run automatically",
    )
    run_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format: text (default), json, or yaml",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        help="Write output to file instead of stdout",
    )
    run_parser.add_argument(
        "params", nargs="*", help="Parameters in the format name=value or --name=value"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List available workflows")
    list_parser.add_argument(
        "--base-dir", default="workflows", help="Base directory containing workflows"
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a workflow file")
    validate_parser.add_argument("workflow", help="Path to workflow file")
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (non-zero exit if any warnings)",
    )
    validate_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json (machine-readable)",
    )

    # Visualize command
    visualize_parser = subparsers.add_parser(
        "visualize", help="Visualize a workflow as a diagram"
    )
    visualize_parser.add_argument("workflow", help="Path to workflow file")
    visualize_parser.add_argument("--flow", help="Flow name to visualize")
    visualize_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "mermaid"],
        default="text",
        help="Output format: text (ASCII, default) or mermaid",
    )
    visualize_parser.add_argument(
        "--output", "-o", help="Output file (default: stdout)"
    )

    # Workspace commands
    workspace_parser = subparsers.add_parser(
        "workspace", help="Workspace management commands"
    )
    workspace_subparsers = workspace_parser.add_subparsers(
        dest="workspace_command", help="Workspace commands"
    )

    # Workspace list command
    workspace_list_parser = workspace_subparsers.add_parser(
        "list", help="List workflow run directories"
    )
    workspace_list_parser.add_argument(
        "--base-dir", "-b", default="runs", help="Base directory for workflow runs"
    )
    workspace_list_parser.add_argument(
        "--workflow", "-w", help="Filter by workflow name"
    )

    # Workspace clean command
    workspace_clean_parser = workspace_subparsers.add_parser(
        "clean", help="Clean up old workflow runs"
    )
    workspace_clean_parser.add_argument(
        "--base-dir", "-b", default="runs", help="Base directory for workflow runs"
    )
    workspace_clean_parser.add_argument(
        "--older-than", "-o", type=int, default=30, help="Remove runs older than N days"
    )
    workspace_clean_parser.add_argument(
        "--workflow", "-w", help="Clean only runs of this workflow"
    )
    workspace_clean_parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    # Workspace remove command
    workspace_remove_parser = workspace_subparsers.add_parser(
        "remove", help="Remove specific workflow runs"
    )
    workspace_remove_parser.add_argument(
        "runs", nargs="+", help="Names of runs to remove"
    )
    workspace_remove_parser.add_argument(
        "--base-dir", "-b", default="runs", help="Base directory for workflow runs"
    )
    workspace_remove_parser.add_argument(
        "--force", "-f", action="store_true", help="Don't ask for confirmation"
    )

    # Init command
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new project with example workflows"
    )
    init_parser.add_argument(
        "--dir", default="workflows", help="Directory to create workflows in"
    )
    init_parser.add_argument("--example", help="Specific example workflow to copy")

    # Serve command (web dashboard)
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start web dashboard for monitoring and triggering workflows",
    )
    serve_parser.add_argument(
        "--dir",
        default="workflows",
        help="Directory containing workflow YAML files (default: workflows)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--base-dir",
        default="runs",
        help="Base directory for workflow runs (default: runs)",
    )

    # MCP Server command
    mcp_parser = subparsers.add_parser(
        "serve-mcp",
        help="Start MCP server exposing workflows as tools",
    )
    mcp_parser.add_argument(
        "--dir",
        default="workflows",
        help="Directory containing workflow YAML files (default: workflows)",
    )
    mcp_parser.add_argument(
        "--base-dir",
        default="runs",
        help="Base directory for workflow runs (default: runs)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "run":
            run_workflow(args)
        elif args.command == "list":
            list_workflows(args)
        elif args.command == "validate":
            validate_workflow(args)
        elif args.command == "visualize":
            visualize_workflow(args)
        elif args.command == "workspace":
            if args.workspace_command == "list":
                list_workspaces(args)
            elif args.workspace_command == "clean":
                clean_workspaces(args)
            elif args.workspace_command == "remove":
                remove_workspaces(args)
            else:
                workspace_parser.print_help()
                sys.exit(1)
        elif args.command == "init":
            init_project(args)
        elif args.command == "serve":
            try:
                import uvicorn

                from .serve.app import create_app
            except ImportError:
                print(
                    "Web dashboard requires FastAPI and uvicorn.\n"
                    "Install with: pip install 'yaml-workflow[serve]'",
                    file=sys.stderr,
                )
                sys.exit(1)
            app = create_app(workflow_dir=args.dir, base_dir=args.base_dir)
            print(f"Starting yaml-workflow dashboard at http://{args.host}:{args.port}")
            uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        elif args.command == "serve-mcp":
            import asyncio

            try:
                from .mcp_server import serve
            except ImportError:
                print(
                    "MCP server requires the 'mcp' package.\n"
                    "Install it with: pip install 'yaml-workflow[mcp]'",
                    file=sys.stderr,
                )
                sys.exit(1)
            asyncio.run(serve(args.dir, base_dir=args.base_dir))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # Top-level catch-all for unexpected errors
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
