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
import yaml

from .engine import WorkflowEngine
from .exceptions import WorkflowError
from .workspace import get_workspace_info

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(description="YAML Workflow Engine CLI")
    
    # Add subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow", help="Path to workflow YAML file")
    run_parser.add_argument("--workspace", help="Custom workspace directory")
    run_parser.add_argument("--base-dir", default="runs", help="Base directory for workflow runs")
    run_parser.add_argument("--resume", action="store_true", help="Resume workflow from last failed step")
    run_parser.add_argument("--start-from", help="Start workflow execution from specified step")
    run_parser.add_argument("--skip-steps", help="Comma-separated list of steps to skip during execution")
    run_parser.add_argument("--flow", help="Name of the flow to execute (default: use flow specified in workflow file)")
    # Add -- before params to handle parameters after flags
    run_parser.add_argument("params", nargs="*", help="Workflow parameters in key=value format", default=[])
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available workflows")
    list_parser.add_argument("--base-dir", default="workflows", help="Base directory containing workflows")
    
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
    
    return parser

def parse_params(params: Optional[List[str]]) -> Dict[str, str]:
    """Parse command line parameters."""
    if not params:
        return {}
        
    result = {}
    for param in params:
        try:
            name, value = param.split("=", 1)
            result[name.strip()] = value.strip()
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
        
        # Create workflow engine
        engine = WorkflowEngine(
            workflow_file=args.workflow,
            workspace=args.workspace,
            base_dir=args.base_dir
        )
        
        # Parse skip steps
        skip_steps = []
        if args.skip_steps:
            skip_steps = [step.strip() for step in args.skip_steps.split(',')]
            print(f"Skipping steps: {', '.join(skip_steps)}")
        
        # Handle start-from and resume logic
        start_from = None
        resume_from = None
        
        # Check start-from first (takes precedence)
        if args.start_from:
            start_from = args.start_from
            print(f"Starting workflow from step: {start_from}")
        # Check resume flag - only if workflow is in failed state
        elif args.resume:
            try:
                state = engine.state
                if state.metadata['execution_state']['status'] == 'failed':
                    failed_step = state.metadata['execution_state']['failed_step']
                    if failed_step:
                        resume_from = failed_step['step_name']
                        print(f"Resuming workflow from failed step: {resume_from}")
                    else:
                        print("No failed step found to resume from.")
                        sys.exit(1)
                elif state.metadata['execution_state']['status'] == 'completed':
                    print("Cannot resume: Workflow is already completed. Use --start-from to run from a specific step.")
                    sys.exit(1)
                else:
                    print("Cannot resume: No failed workflow found.")
                    sys.exit(1)
            except Exception as e:
                print(f"Cannot resume: Could not determine workflow state: {e}")
                sys.exit(1)
        
        # Run workflow with appropriate parameters
        results = engine.run(
            params,
            resume_from=resume_from,
            start_from=start_from,
            skip_steps=skip_steps,
            flow=args.flow
        )
        
        # Print results
        if resume_from:
            print(f"\nWorkflow resumed from failed step '{resume_from}' and completed successfully!")
        elif start_from:
            print(f"\nWorkflow started from step '{start_from}' and completed successfully!")
        else:
            print("\nWorkflow completed successfully!")
        if skip_steps:
            print(f"Skipped steps: {', '.join(skip_steps)}")
        if args.flow:
            print(f"Flow executed: {args.flow}")
        print("Results:", results)
        
    except WorkflowError as e:
        print(f"Workflow error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

def list_workflows(args: argparse.Namespace) -> None:
    """List available workflows in the specified directory."""
    workflow_dir = Path(args.base_dir)
    if not workflow_dir.exists():
        print(f"Error: Directory not found: {workflow_dir}")
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
                        desc = content.get("usage", {}).get("description", "No description available")
                        print(f"\n- {workflow.relative_to(workflow_dir)}")
                        print(f"  Name: {name}")
                        print(f"  Description: {desc}")
                        found = True
                        
        except Exception as e:
            # Skip files that can't be parsed as YAML
            continue
    
    if not found:
        print("No workflow files found. Workflows should be YAML files containing 'steps' section.")
        print(f"\nMake sure you have workflow YAML files in the '{workflow_dir}' directory.")
        print("You can specify a different directory with --base-dir option.")
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
    parser = create_parser()
    
    try:
        # First try to parse with standard format (params before flags)
        try:
            args = parser.parse_args()
        except SystemExit as e:
            if e.code == 2:
                # If that fails, try to parse with -- format
                argv = sys.argv[1:]
                try:
                    split_idx = argv.index('--')
                    # Parse everything before --
                    args = parser.parse_args(argv[:split_idx])
                    # Get parameters after --
                    if args.command == "run":
                        args.params = argv[split_idx + 1:]
                except ValueError:
                    # If no -- found, show helpful error message
                    cmd_line = ' '.join(sys.argv)
                    if any('=' in arg for arg in sys.argv) and any(arg.startswith('--') for arg in sys.argv):
                        print("\nError: Parameters must either:")
                        print("  1. Come before flags:")
                        print("     yaml-workflow run workflow.yaml param1=value1 param2=value2 --resume")
                        print("\n  2. Or be separated with --:")
                        print("     yaml-workflow run workflow.yaml --resume -- param1=value1 param2=value2")
                        print("\nYour command:")
                        print(f"  {cmd_line}")
                        print("\nPlease use one of the formats above.")
                    sys.exit(2)
            else:
                raise
        
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
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 