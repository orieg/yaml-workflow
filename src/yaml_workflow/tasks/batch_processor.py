"""
Batch processing tasks for handling multiple items in parallel with resume capability.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from jinja2 import Template, StrictUndefined, UndefinedError

from ..exceptions import TemplateError
from . import get_task_handler, register_task
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
    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than 0")
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


def resolve_template(template_str: str, context: Dict[str, Any], item: Any = None, batch_index: int = 0, batch: List[Any] = None) -> str:
    """Resolve a template string with batch context.
    
    Args:
        template_str: Template string to resolve
        context: Base context dictionary
        item: Current batch item
        batch_index: Current batch index
        batch: Current batch list
        
    Returns:
        str: Resolved template string
        
    Raises:
        TemplateError: If template resolution fails
    """
    try:
        template = Template(template_str, undefined=StrictUndefined)
        batch_context = {
            **context,
            "item": item,
            "batch_index": batch_index,
            "batch": batch or [],
        }
        return template.render(**batch_context)
    except UndefinedError as e:
        available = {
            "args": list(context["args"].keys()) if "args" in context else [],
            "env": list(context["env"].keys()) if "env" in context else [],
            "steps": list(context["steps"].keys()) if "steps" in context else [],
            "batch": ["item", "batch_index", "batch"]
        }
        raise TemplateError(
            f"Failed to resolve variable in template '{template_str}': {str(e)}. "
            f"Available variables: {available}"
        )
    except Exception as e:
        raise TemplateError(f"Failed to render template: {str(e)}")


class BatchProcessor:
    """Handles batch processing of items with state management."""

    def __init__(self, workspace: Union[str, Path], name: str):
        """Initialize batch processor.

        Args:
            workspace: Path to workspace directory
            name: Name of the batch processor (used for state files)
        """
        self.workspace = Path(workspace) if isinstance(workspace, str) else workspace
        self.name = name
        self.logger = logging.getLogger(__name__)
        self.state_dir = self.workspace / ".batch_state"
        self.state_file = self.state_dir / f"{name}_state.json"

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Tuple[Set[str], Set[str]]:
        """
        Load the processing state from state file.

        Returns:
            Tuple[Set[str], Set[str]]: Sets of processed and failed items
        """
        processed = set()
        failed = set()

        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    processed = set(state.get("processed", []))
                    failed = set(state.get("failed", []))
                    self.logger.info(
                        f"Loaded state: {len(processed)} processed, {len(failed)} failed"
                    )
            except Exception as e:
                self.logger.error(f"Failed to load state: {str(e)}")

        return processed, failed

    def save_state(self, processed: Set[str], failed: Set[str]) -> None:
        """
        Save the processing state to state file.

        Args:
            processed: Set of successfully processed items
            failed: Set of failed items
        """
        try:
            state = {
                "processed": list(processed),
                "failed": list(failed),
                "timestamp": datetime.now().isoformat(),
            }

            # Write state atomically using a temporary file
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(state, f)
            temp_file.rename(self.state_file)

        except Exception as e:
            self.logger.error(f"Failed to save state: {str(e)}")

    def process_item(
        self,
        item: Any,
        task_config: Dict[str, Any],
        context: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[bool, Any]:
        """
        Process a single item using the specified task.

        Args:
            item: Item to process
            task_config: Task configuration including task type and function
            context: Workflow context
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple[bool, Any]: Success status and task result
        
        Raises:
            TemplateError: If template resolution fails
            ValueError: If task configuration is invalid
        """
        try:
            self.logger.info(f"Processing item: {item}")

            # Get task handler
            task_type = task_config.get("task")
            if not task_type:
                raise ValueError("task parameter is required in processing_config")

            task_handler = get_task_handler(task_type)
            if not task_handler:
                raise ValueError(f"Task handler not found: {task_type}")

            # Prepare task step configuration
            step = {"name": f"process_{item}", "task": task_type}

            # Copy all task configuration to step
            for key, value in task_config.items():
                if key != "batch_index" and key != "batch":
                    step[key] = value

            # Add function if specified
            if "function" in task_config:
                step["function"] = task_config["function"]

            # Add command for shell tasks
            if "command" in task_config:
                step["command"] = resolve_template(
                    task_config["command"],
                    context,
                    item,
                    task_config.get("batch_index", 0),
                    task_config.get("batch", [])
                )

            # Add template and output for template tasks
            if "template" in task_config:
                step["template"] = task_config["template"]

            if "output" in task_config:
                output_path = resolve_template(
                    task_config["output"],
                    context,
                    item,
                    task_config.get("batch_index", 0),
                    task_config.get("batch", [])
                )
                step["output"] = str(self.workspace / output_path)

            # Add file output path if specified
            if "file_output" in task_config:
                file_output_path = resolve_template(
                    task_config["file_output"],
                    context,
                    item,
                    task_config.get("batch_index", 0),
                    task_config.get("batch", [])
                )
                step["file_output"] = str(self.workspace / file_output_path)

            # Add inputs if any
            step["inputs"] = {
                **(task_config.get("inputs", {})),
                "item": item,  # Add current item to inputs
            }

            # Update context with batch information
            batch_context = {
                **context,
                "item": item,
                "batch_index": task_config.get("batch_index", 0),
                "batch": task_config.get("batch", []),
                "previous_batch_result": task_config.get("previous_batch_result"),
                "workspace": str(self.workspace),  # Ensure workspace is available
            }

            # Execute task
            result = task_handler(step, batch_context, self.workspace)

            # Call progress callback if provided
            if progress_callback:
                current = task_config.get("batch_index", 0) + 1
                total = len(task_config.get("batch", []))
                progress_callback(current, total)

            self.logger.info(f"Successfully processed: {item}")
            return True, result

        except Exception as e:
            self.logger.error(f"Failed to process item {item}: {str(e)}")
            return False, str(e)

    def process_batch(
        self,
        items: List[Any],
        task_config: Dict[str, Any],
        context: Dict[str, Any],
        chunk_size: int = 10,
        max_workers: Optional[int] = None,
        resume_state: bool = False,
        progress_callback: Optional[Callable[[Any, float], None]] = None,
        error_handler: Optional[Callable[[str, Any, Exception], None]] = None,
        aggregator: Optional[Callable[[List[Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """Process a batch of items in parallel with state management.

        Args:
            items: List of items to process
            task_config: Task configuration
            context: Workflow context
            chunk_size: Number of items to process in each chunk
            max_workers: Maximum number of worker threads
            resume_state: Whether to resume from previous state
            progress_callback: Optional callback for progress updates
            error_handler: Optional callback for error handling
            aggregator: Optional function to aggregate results

        Returns:
            Dict containing processing results and statistics

        Raises:
            TemplateError: If template resolution fails
            ValueError: If configuration is invalid
        """
        if not items:
            return {
                "processed": [],
                "failed": [],
                "results": [],
                "stats": {},
                "processed_items": [],  # For backward compatibility
                "failed_items": [],     # For backward compatibility
                "aggregated_result": None  # For backward compatibility
            }

        # Validate chunk size
        if chunk_size <= 0:
            raise ValueError("Chunk size must be greater than 0")

        # Load previous state if resuming
        processed, failed = self.load_state() if resume_state else (set(), set())
        results: List[Any] = []
        total_items = len(items)
        completed = 0
        aggregated_result = None  # Store the final aggregated result
        item_results = {}  # Map items to their results

        try:
            # Process items in chunks
            for chunk_index, chunk in enumerate(chunk_iterator(items, chunk_size)):
                chunk_results = []
                chunk_failed = []

                # Update task config with chunk information
                chunk_task_config = {
                    **task_config,
                    "batch": chunk,
                    "batch_index": chunk_index,
                    "previous_batch_result": results[-chunk_size:] if results else None,
                }

                # Process chunk in parallel with limited workers
                with ThreadPoolExecutor(max_workers=max_workers or chunk_size) as executor:
                    # Create a mapping of futures to items
                    futures = {}
                    for item in chunk:
                        if str(item) not in processed and str(item) not in failed:
                            future = executor.submit(
                                self.process_item, item, chunk_task_config, context, progress_callback
                            )
                            futures[future] = item

                    # Process completed futures
                    for future in as_completed(futures):
                        item = futures[future]
                        try:
                            success, result = future.result()
                            if success:
                                chunk_results.append(result)
                                processed.add(str(item))
                                item_results[str(item)] = result
                            else:
                                chunk_failed.append(item)
                                failed.add(str(item))
                        except Exception as e:
                            self.logger.error(f"Failed to process item {item}: {str(e)}")
                            if error_handler:
                                error_handler(str(item), item, e)
                            chunk_failed.append(item)
                            failed.add(str(item))

                        # Update progress
                        completed += 1
                        if progress_callback:
                            progress = completed / total_items * 100
                            progress_callback(item, progress)

                # Save state after each chunk
                self.save_state(processed, failed)

                # Aggregate chunk results if needed
                if aggregator and chunk_results:
                    try:
                        chunk_result = aggregator(chunk_results)
                        results.append(chunk_result)
                        # Store the last aggregated result
                        aggregated_result = chunk_result
                    except Exception as e:
                        self.logger.error(f"Failed to aggregate chunk results: {str(e)}")
                        if error_handler:
                            error_handler("aggregation", chunk_results, e)
                else:
                    results.extend(chunk_results)

            # Calculate statistics
            stats = {
                "total": total_items,
                "processed": len(processed),
                "failed": len(failed),
                "success_rate": len(processed) / total_items * 100 if total_items > 0 else 0,
                "chunks": (total_items + chunk_size - 1) // chunk_size,
                "completed_at": datetime.now().isoformat(),
            }

            # Create a list of results in the same order as input items
            processed_results = []
            for item in items:
                if str(item) in processed:
                    processed_results.append(item_results[str(item)])

            return {
                "processed": list(processed),
                "failed": list(failed),
                "results": results,
                "stats": stats,
                "processed_items": processed_results,  # Contains results in original item order
                "failed_items": list(failed),
                "aggregated_result": aggregated_result
            }

        except ValueError as e:
            self.logger.error(f"Invalid configuration: {str(e)}")
            raise  # Re-raise ValueError as is
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            raise TemplateError(f"Batch processing failed: {str(e)}")


@register_task("batch_processor")
def process_batch(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Union[str, Path]
) -> Dict[str, Any]:
    """Process a batch of items using the specified task.

    Args:
        step: Step configuration including:
            - items: List of items to process (or iterate_over for backward compatibility)
            - task: Task type to use for processing
            - chunk_size: Optional size of chunks for parallel processing
            - max_workers: Optional maximum number of worker threads
            - resume: Optional flag to resume from previous state
        context: Workflow context
        workspace: Workspace directory

    Returns:
        Dict containing processing results and statistics

    Raises:
        TemplateError: If template resolution fails
        ValueError: If required configuration is missing
    """
    try:
        # Get required parameters - support both new 'items' and legacy 'iterate_over'
        items = step.get("items") or step.get("iterate_over")
        if not items:
            raise ValueError("items parameter (or iterate_over for backward compatibility) is required")

        # Get task configuration - support both new style and legacy
        task_config = step.copy()
        if "processing_task" in step:
            # Legacy format - merge processing_task into main config
            task_config.update(step["processing_task"])
            
        # Get optional parameters with defaults
        chunk_size = step.get("chunk_size", 10)
        max_workers = step.get("max_workers")
        resume = step.get("resume", False) or step.get("resume_state", False)

        # Create processor instance
        processor = BatchProcessor(workspace, step.get("name", "batch_processor"))

        # Process items
        result = processor.process_batch(
            items=items,
            task_config=task_config,
            context=context,
            chunk_size=chunk_size,
            max_workers=max_workers,
            resume_state=resume,
            progress_callback=step.get("progress_callback"),
            error_handler=step.get("error_handler"),
            aggregator=step.get("aggregator"),
        )

        return result

    except Exception as e:
        if isinstance(e, (ValueError, TemplateError)):
            raise
        raise TemplateError(f"Batch processing failed: {str(e)}")
