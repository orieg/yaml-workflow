"""
Batch processing tasks for handling multiple files in parallel with resume capability.
"""

import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime

from . import register_task
from .base import get_task_logger

class BatchProcessor:
    """Handles batch processing of files with resume capability."""
    
    def __init__(self, workspace: Path, name: str):
        """
        Initialize the batch processor.
        
        Args:
            workspace: Workspace directory
            name: Name of the processing task
        """
        self.workspace = workspace
        self.name = name
        self.logger = get_task_logger(workspace, name)
        
        # Create state directory
        self.state_dir = workspace / "state"
        self.state_dir.mkdir(exist_ok=True)
        
        # State file paths
        self.state_file = self.state_dir / f"{name}_state.json"
        self.processed_file = self.state_dir / f"{name}_processed.json"
        self.failed_file = self.state_dir / f"{name}_failed.json"
        
    def load_state(self) -> Tuple[Set[str], Set[str]]:
        """
        Load the processing state from files.
        
        Returns:
            Tuple[Set[str], Set[str]]: Sets of processed and failed files
        """
        processed = set()
        failed = set()
        
        if self.processed_file.exists():
            with open(self.processed_file) as f:
                processed = set(json.load(f))
                
        if self.failed_file.exists():
            with open(self.failed_file) as f:
                failed = set(json.load(f))
                
        return processed, failed
        
    def save_state(self, processed: Set[str], failed: Set[str]) -> None:
        """
        Save the processing state to files.
        
        Args:
            processed: Set of successfully processed files
            failed: Set of failed files
        """
        with open(self.processed_file, 'w') as f:
            json.dump(list(processed), f)
            
        with open(self.failed_file, 'w') as f:
            json.dump(list(failed), f)
            
    def process_file(self, file_path: str, config: Dict[str, Any], output_dir: str) -> bool:
        """
        Process a single file.
        
        Args:
            file_path: Path to the input file
            config: Processing configuration
            output_dir: Output directory
            
        Returns:
            bool: True if processing was successful
        """
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Create output path
            input_path = Path(file_path)
            rel_path = input_path.relative_to(input_path.parent.parent)
            output_path = Path(output_dir) / rel_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # TODO: Implement actual file processing logic here
            # This is just a placeholder that copies the file
            if config.get('validate', True):
                # Validate file
                if not input_path.exists():
                    raise FileNotFoundError(f"Input file not found: {file_path}")
                    
            if config.get('transform', True):
                # Transform file
                with open(input_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())
                    
            if config.get('compress', False):
                # Compress file
                pass
                
            self.logger.info(f"Successfully processed: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {str(e)}")
            return False

@register_task("batch_processor")
def process_file_batch(
    step: Dict[str, Any],
    context: Dict[str, Any],
    workspace: Path
) -> Dict[str, List[str]]:
    """
    Process a batch of files in parallel with resume capability.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        Dict[str, List[str]]: Dictionary containing lists of processed, failed, and skipped files
    """
    # Get step configuration
    parallel = step.get('parallel', False)
    resume_state = step.get('resume_state', False)
    iterate_over = step.get('iterate_over', [])
    max_workers = step.get('parallel_settings', {}).get('max_workers', 4)
    
    # Get input parameters
    inputs = step.get('inputs', {})
    output_dir = inputs.get('output_dir')
    config = inputs.get('processing_config', {})
    
    if not output_dir:
        raise ValueError("output_dir is required")
    
    # Initialize batch processor
    processor = BatchProcessor(workspace, step.get('name', 'batch_processor'))
    
    # Load previous state if resuming
    processed_files, failed_files = processor.load_state() if resume_state else (set(), set())
    
    # Track newly processed files
    newly_processed = set()
    newly_failed = set()
    skipped = set()
    
    # Process files
    if parallel and len(iterate_over) > 1:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}
            
            # Submit jobs
            for file_path in iterate_over:
                if file_path in processed_files:
                    skipped.add(file_path)
                    continue
                    
                future = executor.submit(
                    processor.process_file,
                    file_path,
                    config,
                    output_dir
                )
                future_to_file[future] = file_path
                
            # Process results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    success = future.result()
                    if success:
                        newly_processed.add(file_path)
                    else:
                        newly_failed.add(file_path)
                except Exception as e:
                    processor.logger.error(f"Error processing {file_path}: {str(e)}")
                    newly_failed.add(file_path)
    else:
        # Sequential processing
        for file_path in iterate_over:
            if file_path in processed_files:
                skipped.add(file_path)
                continue
                
            if processor.process_file(file_path, config, output_dir):
                newly_processed.add(file_path)
            else:
                newly_failed.add(file_path)
                
    # Update and save state
    processed_files.update(newly_processed)
    failed_files.update(newly_failed)
    if resume_state:
        processor.save_state(processed_files, failed_files)
        
    # Return results
    return {
        'processed_files': list(newly_processed),
        'failed_files': list(newly_failed),
        'skipped_files': list(skipped)
    } 