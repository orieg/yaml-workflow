"""
Command-line interface for the workflow engine.
"""

import argparse
import logging
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WorkflowEngine
from .exceptions import WorkflowError
from .workspace import get_workspace_info

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="YAML Workflow Engine")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow", help="Path to workflow YAML file")
    run_parser.add_argument(
        "--workspace",
        "-w",
        help="Custom workspace directory (default: runs/<workflow>)"
    )
    run_parser.add_argument(
        "--base-dir",
        "-b",
        default="runs",
        help="Base directory for workflow runs (default: runs)"
    )
    run_parser.add_argument(
        "params",
        nargs="*",
        help="Input parameters in the format name=value"
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available workflows")
    list_parser.add_argument(
        "--directory",
        "-d",
        default="workflows",
        help="Directory containing workflow files (default: workflows)"
    )
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a workflow")
    validate_parser.add_argument("workflow", help="Path to workflow YAML file")
    
    # Workspace commands
    ws_parser = subparsers.add_parser("workspace", help="Workspace management commands")
    ws_subparsers = ws_parser.add_subparsers(dest="ws_command", help="Workspace command")
    
    # workspace list
    ws_list = ws_subparsers.add_parser("list", help="List workflow run directories")
    ws_list.add_argument(
        "--base-dir",
        "-b",
        default="runs",
        help="Base directory for workflow runs (default: runs)"
    )
    ws_list.add_argument(
        "--workflow",
        "-w",
        help="Filter by workflow name"
    )
    
    # workspace clean
    ws_clean = ws_subparsers.add_parser("clean", help="Clean up old workflow runs")
    ws_clean.add_argument(
        "--base-dir",
        "-b",
        default="runs",
        help="Base directory for workflow runs (default: runs)"
    )
    ws_clean.add_argument(
        "--older-than",
        "-o",
        type=int,
        default=30,
        help="Remove runs older than N days (default: 30)"
    )
    ws_clean.add_argument(
        "--workflow",
        "-w",
        help="Clean only runs of this workflow"
    )
    ws_clean.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    # workspace remove
    ws_remove = ws_subparsers.add_parser("remove", help="Remove specific workflow runs")
    ws_remove.add_argument(
        "runs",
        nargs="+",
        help="Run directories to remove (relative to base-dir)"
    )
    ws_remove.add_argument(
        "--base-dir",
        "-b",
        default="runs",
        help="Base directory for workflow runs (default: runs)"
    )
    ws_remove.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Don't ask for confirmation"
    )
    
    return parser.parse_args()

def parse_params(params: List[str]) -> Dict[str, str]:
    """Parse command line parameters."""
    result = {}
    for param in params:
        try:
            name, value = param.split("=", 1)
            result[name] = value
        except ValueError:
            print(f"Invalid parameter format: {param}")
            print("Parameters must be in the format: name=value")
            sys.exit(1)
    return result

def run_workflow(args: argparse.Namespace) -> None:
    """Run a workflow."""
    try:
        # Parse parameters
        params = parse_params(args.params)
        
        # Create and run workflow
        engine = WorkflowEngine(
            workflow_file=args.workflow,
            workspace=args.workspace,
            base_dir=args.base_dir
        )
        results = engine.run(params)
        
        # Print results
        print("\nWorkflow completed successfully!")
        print("Results:", results)
        
    except WorkflowError as e:
        print(f"Workflow error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

def list_workflows(args: argparse.Namespace) -> None:
    """List available workflows in the specified directory."""
    workflow_dir = Path(args.directory)
    if not workflow_dir.exists():
        print(f"Error: Directory not found: {workflow_dir}")
        sys.exit(1)
        
    print("\nAvailable workflows:")
    for workflow in workflow_dir.glob("*.yaml"):
        print(f"- {workflow.relative_to(workflow_dir)}")
    print()

def validate_workflow(args: argparse.Namespace) -> None:
    """Validate a workflow file."""
    try:
        # Just try to create the engine, which will validate the workflow
        WorkflowEngine(args.workflow)
        print(f"Workflow is valid: {args.workflow}")
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)

def list_workspaces(args: argparse.Namespace) -> None:
    """List workflow run directories."""
    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        sys.exit(1)
    
    # Get all run directories
    runs = []
    pattern = f"*_run_*" if not args.workflow else f"{args.workflow}_run_*"
    
    for run_dir in base_dir.glob(pattern):
        if run_dir.is_dir():
            try:
                info = get_workspace_info(run_dir)
                runs.append({
                    "name": run_dir.name,
                    "created": datetime.fromisoformat(info["created_at"]),
                    "size": info["size"],
                    "files": info["files"]
                })
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

def clean_workspaces(args: argparse.Namespace) -> None:
    """Clean up old workflow runs."""
    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        sys.exit(1)
    
    cutoff = datetime.now() - timedelta(days=args.older_than)
    pattern = f"*_run_*" if not args.workflow else f"{args.workflow}_run_*"
    
    to_delete = []
    for run_dir in base_dir.glob(pattern):
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

def remove_workspaces(args: argparse.Namespace) -> None:
    """Remove specific workflow runs."""
    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"Error: Base directory not found: {base_dir}")
        sys.exit(1)
    
    to_remove = []
    for run_name in args.runs:
        run_dir = base_dir / run_name
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
        confirm = input("\nAre you sure you want to remove these runs? [y/N] ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    for run_dir in to_remove:
        try:
            shutil.rmtree(run_dir)
            print(f"Removed: {run_dir}")
        except Exception as e:
            print(f"Error removing {run_dir}: {e}")

def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()
    
    if args.command == "run":
        run_workflow(args)
    elif args.command == "list":
        list_workflows(args)
    elif args.command == "validate":
        validate_workflow(args)
    elif args.command == "workspace":
        if args.ws_command == "list":
            list_workspaces(args)
        elif args.ws_command == "clean":
            clean_workspaces(args)
        elif args.ws_command == "remove":
            remove_workspaces(args)
        else:
            print("Error: No workspace command specified")
            print("Use 'workspace --help' for usage information")
            sys.exit(1)
    else:
        print("Error: No command specified")
        print("Use --help for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main() 