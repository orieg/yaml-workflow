"""
Command-line interface for the YAML Workflow Engine
"""

import argparse
import json
import logging
import sys
from typing import List, Optional

from .engine import run_workflow
from . import __version__

def parse_key_value(arg: str) -> tuple:
    """Parse a key=value argument."""
    try:
        key, value = arg.split('=', 1)
        return key, value
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid key=value pair: {arg}")

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YAML Workflow Engine - Execute workflows defined in YAML files"
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Run command
    run_parser = subparsers.add_parser(
        'run',
        help='Run a workflow'
    )
    run_parser.add_argument(
        'workflow_file',
        help='Path to the workflow YAML file'
    )
    run_parser.add_argument(
        'params',
        nargs='*',
        type=parse_key_value,
        help='Runtime parameters in key=value format'
    )
    
    # List command (for future use)
    list_parser = subparsers.add_parser(
        'list',
        help='List available workflows in a directory'
    )
    list_parser.add_argument(
        'directory',
        nargs='?',
        default='workflows',
        help='Directory containing workflow files (default: workflows)'
    )
    
    # Validate command (for future use)
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate a workflow file without running it'
    )
    validate_parser.add_argument(
        'workflow_file',
        help='Path to the workflow YAML file to validate'
    )

    return parser.parse_args(args)

def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=level, format=format_str)

def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI."""
    try:
        parsed_args = parse_args(args)
        setup_logging(parsed_args.verbose)
        
        if parsed_args.command == 'run':
            # Convert params list of tuples to dictionary
            runtime_inputs = dict(parsed_args.params or [])
            
            # Run the workflow
            final_context = run_workflow(parsed_args.workflow_file, runtime_inputs)
            
            # Print final outputs
            logging.info("Final workflow outputs:")
            for key, value in final_context.items():
                logging.info(f"  {key}: {value}")
                
        elif parsed_args.command == 'list':
            # TODO: Implement workflow listing
            logging.info(f"Listing workflows in {parsed_args.directory}")
            
        elif parsed_args.command == 'validate':
            # TODO: Implement workflow validation
            logging.info(f"Validating workflow file: {parsed_args.workflow_file}")
        
        return 0
        
    except Exception as e:
        logging.error(str(e))
        if parsed_args.verbose:
            logging.exception("Detailed error information:")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 