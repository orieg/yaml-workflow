"""
Command-line interface for the workflow engine.
"""

import argparse
import importlib.resources
import json
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from . import __version__  # Import version
from .engine import WorkflowEngine
from .exceptions import WorkflowError
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


def run_workflow(args):
    """Run a workflow."""
    try:
        try:
            param_dict = parse_params(args.params)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

        # If resuming, check the existing workspace first
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
                    except Exception as e:
                        raise ValueError(
                            f"Cannot resume: Failed to read metadata file - {str(e)}"
                        )

                    if metadata.get("execution_state", {}).get("status") == "failed":
                        failed_step = metadata["execution_state"].get("failed_step")
                        if failed_step:
                            print(
                                f"Found failed workflow state, resuming from step: {failed_step['step_name']}"
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

        # Create workflow engine
        engine = WorkflowEngine(
            workflow=args.workflow, workspace=args.workspace, base_dir=args.base_dir
        )

        # Parse skip steps
        skip_step_list = []
        if args.skip_steps:
            skip_step_list = [step.strip() for step in args.skip_steps.split(",")]
            print(f"Skipping steps: {', '.join(skip_step_list)}")

        # Handle start-from and resume logic
        start_from_step = None
        resume_from = None

        # Check start-from first (takes precedence)
        if args.start_from:
            start_from_step = args.start_from
            print(f"Starting workflow from step: {start_from_step}")
        # Check resume flag - only if workflow is in failed state
        elif args.resume:
            state = engine.state
            if state.metadata["execution_state"]["status"] == "failed":
                failed_step = state.metadata["execution_state"]["failed_step"]
                if failed_step:
                    resume_from = failed_step["step_name"]
                    print(f"Resuming workflow from failed step: {resume_from}")
                else:
                    raise ValueError("No failed step found to resume from.")
            else:
                raise ValueError("Cannot resume: workflow is not in failed state")

        # Run workflow with appropriate parameters
        results = engine.run(
            param_dict,
            resume_from=resume_from,
            start_from=start_from_step,
            skip_steps=skip_step_list,
            flow=args.flow,
        )

        # Print completion status
        print("\n=== Workflow Status ===")
        if resume_from:
            print(f"✓ Workflow resumed from '{resume_from}' and completed successfully")
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
            print("\n=== Step Outputs ===")
            for step_name, output in results["outputs"].items():
                # Skip empty outputs or None values
                if output is None or (isinstance(output, str) and not output.strip()):
                    continue
                print(f"\n• {step_name}:")
                if isinstance(output, (dict, list)):
                    formatted_output = json.dumps(output, indent=2)
                    print("  " + formatted_output.replace("\n", "\n  "))
                else:
                    print("  " + str(output).replace("\n", "\n  "))

        print("\n=== Workspace Info ===")
        print(f"• Location: {engine.workspace}")
        # Get run number from the workspace metadata
        run_number = engine.state.metadata.get("run_number", "unknown")
        print(f"• Run number: {run_number}")

    except WorkflowError as e:
        print(f"Workflow error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
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

        except Exception:
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
    try:
        # Just try to create the engine, which will validate the workflow
        WorkflowEngine(args.workflow)
        print("Workflow validation successful")
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
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
            except Exception as e:
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
            except Exception as e:
                print(f"Warning: Could not process {run_dir}: {e}")

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
            except Exception as e:
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
            print(f"Warning: Not a directory: {run_dir}")
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
        except Exception as e:
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
        except Exception as e:
            print(f"Error removing {run_dir}: {e}")


def init_project(args):
    """Initialize a new project with example workflows."""
    try:
        # Create target directory if it doesn't exist
        target_dir = Path(args.dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Get examples directory from package
        examples_dir = Path(__file__).parent / "examples"

        if args.example:
            # Copy specific example
            example_file = examples_dir / f"{args.example}.yaml"
            if not example_file.exists():
                print(f"Example '{args.example}' not found", file=sys.stderr)
                sys.exit(1)
            shutil.copy2(example_file, target_dir)
            print(f"Initialized project with example: {args.example}")
        else:
            # Copy all examples
            for example in examples_dir.glob("*.yaml"):
                shutil.copy2(example, target_dir)
            print(f"Initialized project with examples in: {target_dir}")

    except Exception as e:
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
  workspace          Workspace management commands
  init               Initialize a new project with example workflows
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
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
