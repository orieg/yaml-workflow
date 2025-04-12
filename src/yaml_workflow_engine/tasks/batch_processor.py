"""
Batch processing tasks for handling multiple items in parallel with resume capability.
"""

import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Iterator
from datetime import datetime

from . import register_task, get_task_handler
from .base import get_task_logger

def chunk_iterator(items: List[Any], chunk_size: int) -> Iterator[List[Any]]:
    """
    Split a list of items into chunks.
    
    Args:
        items: List of items to chunk
        chunk_size: Size of each chunk
        
    Returns:
        Iterator[List[Any]]: Iterator yielding chunks of items
    """
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

class BatchProcessor:
    """Handles batch processing of items with resume capability."""
    
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
            Tuple[Set[str], Set[str]]: Sets of processed and failed items
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
            processed: Set of successfully processed items
            failed: Set of failed items
        """
        with open(self.processed_file, 'w') as f:
            json.dump(list(processed), f)
            
        with open(self.failed_file, 'w') as f:
            json.dump(list(failed), f)
            
    def process_item(
        self,
        item: Any,
        task_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[bool, Any]:
        """
        Process a single item using the specified task.
        
        Args:
            item: Item to process
            task_config: Task configuration including task type and function
            context: Workflow context
            
        Returns:
            Tuple[bool, Any]: Success status and task result
        """
        try:
            self.logger.info(f"Processing item: {item}")
            
            # Get task handler
            task_type = task_config.get('task')
            if not task_type:
                raise ValueError("task parameter is required in processing_config")
                
            task_handler = get_task_handler(task_type)
            if not task_handler:
                raise ValueError(f"Task handler not found: {task_type}")
            
            # Prepare task step configuration
            step = {
                'name': f'process_{item}',
                'task': task_type,
                'function': task_config.get('function', 'process'),
                'inputs': {
                    **task_config.get('inputs', {}),
                    'item': item  # Add current item to inputs
                }
            }
            
            # Execute task
            result = task_handler(step, context, self.workspace)
            self.logger.info(f"Successfully processed: {item}")
            return True, result
            
        except Exception as e:
            self.logger.error(f"Failed to process {item}: {str(e)}")
            return False, str(e)

@register_task("batch_processor")
def process_batch(
    step: Dict[str, Any],
    context: Dict[str, Any],
    workspace: Path
) -> Dict[str, List[Any]]:
    """
    Process a batch of items in parallel with resume capability.
    
    Args:
        step: Step configuration
        context: Workflow context
        workspace: Workspace directory
        
    Returns:
        Dict[str, List[Any]]: Dictionary containing lists of processed, failed, and skipped items
    """
    # Get step configuration
    parallel = step.get('parallel', False)
    resume_state = step.get('resume_state', False)
    iterate_over = step.get('iterate_over', [])
    
    # Get parallel processing settings
    parallel_settings = step.get('parallel_settings', {})
    max_workers = parallel_settings.get('max_workers', 4)
    chunk_size = parallel_settings.get('chunk_size', len(iterate_over))  # Default to all items if not specified
    
    # Get processing task configuration
    processing_config = step.get('processing_task', {})
    if not processing_config:
        raise ValueError("processing_task configuration is required")
    
    # Initialize batch processor
    processor = BatchProcessor(workspace, step.get('name', 'batch_processor'))
    
    # Load previous state if resuming
    processed_items, failed_items = processor.load_state() if resume_state else (set(), set())
    
    # Track items and results
    newly_processed = []
    newly_failed = []
    skipped = []
    results = []
    
    # Filter out already processed items
    remaining_items = [
        item for item in iterate_over 
        if str(item) not in processed_items
    ]
    
    # Add skipped items to tracking
    skipped.extend([
        item for item in iterate_over 
        if str(item) in processed_items
    ])
    
    # Process items in chunks
    for chunk in chunk_iterator(remaining_items, chunk_size):
        processor.logger.info(f"Processing chunk of {len(chunk)} items")
        
        if parallel and len(chunk) > 1:
            # Parallel processing of chunk
            with ThreadPoolExecutor(max_workers=min(max_workers, len(chunk))) as executor:
                future_to_item = {}
                
                # Submit jobs for chunk
                for item in chunk:
                    future = executor.submit(
                        processor.process_item,
                        item,
                        processing_config,
                        context
                    )
                    future_to_item[future] = (item, str(item))
                    
                # Process results as they complete
                for future in as_completed(future_to_item):
                    item, item_id = future_to_item[future]
                    try:
                        success, result = future.result()
                        if success:
                            newly_processed.append(item)
                            results.append(result)
                            processed_items.add(item_id)
                        else:
                            newly_failed.append(item)
                            failed_items.add(item_id)
                    except Exception as e:
                        processor.logger.error(f"Error processing {item}: {str(e)}")
                        newly_failed.append(item)
                        failed_items.add(item_id)
        else:
            # Sequential processing of chunk
            for item in chunk:
                item_id = str(item)
                success, result = processor.process_item(item, processing_config, context)
                if success:
                    newly_processed.append(item)
                    results.append(result)
                    processed_items.add(item_id)
                else:
                    newly_failed.append(item)
                    failed_items.add(item_id)
                    
        # Save state after each chunk
        if resume_state:
            processor.save_state(processed_items, failed_items)
            processor.logger.info(
                f"Chunk complete. "
                f"Total processed: {len(processed_items)}, "
                f"Total failed: {len(failed_items)}, "
                f"Total skipped: {len(skipped)}"
            )
        
    # Return results
    return {
        'processed_items': newly_processed,
        'failed_items': newly_failed,
        'skipped_items': skipped,
        'results': results
    } 