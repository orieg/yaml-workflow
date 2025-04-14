"""
Batch processing tasks for handling multiple items in parallel with resume capability.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from jinja2 import Template

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
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


class BatchProcessor:
    """Handles batch processing of items with resume capability."""

    def __init__(self, workspace: Union[str, Path], name: str):
        """
        Initialize the batch processor.

        Args:
            workspace: Workspace directory (str or Path)
            name: Name of the processing task
        """
        self.workspace = Path(workspace) if isinstance(workspace, str) else workspace
        self.name = name
        self.logger = get_task_logger(self.workspace, name)

        # State file path in workspace root
        self.state_file = self.workspace / "batch_state.json"

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
        progress_callback: Optional[Callable[[str, float], None]] = None,
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
                # Render command template with batch context
                template = Template(task_config["command"])
                step["command"] = template.render(
                    item=item,
                    batch_index=task_config.get("batch_index", 0),
                    batch=task_config.get("batch", []),
                    **context,
                )

            # Add template and output for template tasks
            if "template" in task_config:
                step["template"] = task_config["template"]

            if "output" in task_config:
                # Render output template with batch context
                template = Template(task_config["output"])
                step["output"] = str(
                    self.workspace
                    / template.render(
                        item=item,
                        batch_index=task_config.get("batch_index", 0),
                        batch=task_config.get("batch", []),
                        **context,
                    )
                )

            # Add file output path if specified
            if "file_output" in task_config:
                template = Template(task_config["file_output"])
                step["file_output"] = str(
                    self.workspace
                    / template.render(
                        item=item,
                        batch_index=task_config.get("batch_index", 0),
                        batch=task_config.get("batch", []),
                        **context,
                    )
                )

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
            result = task_handler(step, batch_context, str(self.workspace))

            # Call progress callback if provided
            if progress_callback:
                progress_callback(str(item), result)

            self.logger.info(f"Successfully processed: {item}")
            return True, result

        except Exception as e:
            self.logger.error(f"Failed to process {item}: {str(e)}")
            return False, str(e)

    def process_batch(
        self,
        items: List[Any],
        task_config: Dict[str, Any],
        context: Dict[str, Any],
        chunk_size: int = 10,
        max_workers: Optional[int] = None,
        resume_state: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        error_handler: Optional[Callable[[str, Any, Exception], None]] = None,
        aggregator: Optional[Callable[[List[Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a batch of items.

        Args:
            items: List of items to process
            task_config: Task configuration
            context: Workflow context
            chunk_size: Size of chunks for parallel processing
            max_workers: Maximum number of worker threads
            resume_state: Whether to load and save state
            progress_callback: Optional callback for progress updates
            error_handler: Optional callback for error handling
            aggregator: Optional function to aggregate results

        Returns:
            Dict[str, Any]: Processing results including:
                - processed_items: List of successfully processed items' results
                - failed_items: List of failed items
                - results: Dict mapping item IDs to their results
                - aggregated_result: Result of aggregation if specified
        """
        self.logger.info(f"Starting batch processing of {len(items)} items")

        # Initialize tracking sets
        processed_items: Set[str] = set()
        failed_items: Set[str] = set()
        results: Dict[str, Any] = {}

        # Load state if resuming
        if resume_state:
            processed_items, failed_items = self.load_state()
            self.logger.info(
                f"Loaded state: {len(processed_items)} processed, {len(failed_items)} failed"
            )

        # Filter out already processed items
        remaining_items = [
            item
            for item in items
            if str(item) not in processed_items and str(item) not in failed_items
        ]

        if not remaining_items:
            self.logger.info("No items to process")
            return {
                "processed_items": list(processed_items),
                "failed_items": list(failed_items),
                "results": results,
                "aggregated_result": None,
            }

        self.logger.info(f"Processing {len(remaining_items)} remaining items")
        total_items = len(remaining_items)
        processed_count = 0

        # Process items in chunks
        for chunk_index, chunk in enumerate(
            chunk_iterator(remaining_items, chunk_size)
        ):
            self.logger.info(f"Processing chunk {chunk_index + 1}")

            # Update task config with batch information
            batch_config = {**task_config, "batch_index": chunk_index, "batch": chunk}

            # Process chunk in parallel if max_workers specified
            if max_workers:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self.process_item,
                            item,
                            batch_config,
                            context,
                            progress_callback,
                        ): item
                        for item in chunk
                    }

                    for future in as_completed(futures):
                        item = futures[future]
                        try:
                            success, result = future.result()
                            if success:
                                processed_items.add(str(item))
                                results[str(item)] = result
                                processed_count += 1
                                if progress_callback:
                                    progress_callback(
                                        str(item), processed_count / total_items
                                    )
                            else:
                                failed_items.add(str(item))
                                if error_handler:
                                    error_handler(str(item), item, Exception(result))
                        except Exception as e:
                            failed_items.add(str(item))
                            if error_handler:
                                error_handler(str(item), item, e)
            else:
                # Process chunk sequentially
                for item in chunk:
                    success, result = self.process_item(
                        item, batch_config, context, progress_callback
                    )
                    if success:
                        processed_items.add(str(item))
                        results[str(item)] = result
                        processed_count += 1
                        if progress_callback:
                            progress_callback(str(item), processed_count / total_items)
                    else:
                        failed_items.add(str(item))
                        if error_handler:
                            error_handler(str(item), item, Exception(result))

            # Save state after each chunk if resuming
            if resume_state:
                self.save_state(processed_items, failed_items)

        # Aggregate results if specified
        aggregated_result = None
        if aggregator and results:
            try:
                aggregated_result = aggregator(
                    [results[str(item)] for item in items if str(item) in results]
                )
            except Exception as e:
                self.logger.error(f"Failed to aggregate results: {str(e)}")

        # Return results with actual values instead of just IDs
        processed_results = []
        for item in items:
            item_str = str(item)
            if item_str in processed_items:
                result = results[item_str]
                # Handle different result formats
                if isinstance(result, dict) and "result" in result:
                    processed_results.append(result["result"])
                else:
                    processed_results.append(result)

        return {
            "processed_items": processed_results,
            "failed_items": list(failed_items),
            "results": results,
            "aggregated_result": aggregated_result,
        }


@register_task("batch_processor")
def process_batch(
    step: Dict[str, Any], context: Dict[str, Any], workspace: Union[str, Path]
) -> Dict[str, Any]:
    """Task handler for batch processing.

    Args:
        step: Step configuration including items and processing task
        context: Execution context
        workspace: Path to workspace directory

    Returns:
        Dictionary containing processing results

    Raises:
        ValueError: If required configuration is missing or invalid
        RuntimeError: If batch processing fails
    """
    # Validate inputs
    items = step.get("iterate_over")
    if not items:
        raise ValueError("'iterate_over' is required in step configuration")

    processing_task = step.get("processing_task")
    if not processing_task:
        raise ValueError("'processing_task' is required in step configuration")
    if not isinstance(processing_task, dict):
        raise ValueError("'processing_task' must be a dictionary")

    # Get configuration with defaults
    parallel_settings = step.get("parallel_settings", {})
    if not isinstance(parallel_settings, dict):
        raise ValueError("'parallel_settings' must be a dictionary")

    chunk_size = parallel_settings.get("chunk_size", 10)
    if not isinstance(chunk_size, int) or chunk_size < 1:
        raise ValueError("'chunk_size' must be a positive integer")

    max_workers = parallel_settings.get("max_workers")
    if max_workers is not None and (
        not isinstance(max_workers, int) or max_workers < 1
    ):
        raise ValueError("'max_workers' must be a positive integer or None")

    resume = step.get("resume_state", False)
    if not isinstance(resume, bool):
        raise ValueError("'resume_state' must be a boolean")

    # Get progress callback and error handler
    progress_callback = step.get("progress_callback")
    error_handler = step.get("error_handler")
    aggregator = step.get("aggregator")

    # Create processor and process batch
    try:
        processor = BatchProcessor(workspace, step.get("name", "batch_task"))
        return processor.process_batch(
            items=items,
            task_config=processing_task,
            context=context,
            chunk_size=chunk_size,
            max_workers=max_workers,
            resume_state=resume,
            progress_callback=progress_callback,
            error_handler=error_handler,
            aggregator=aggregator,
        )
    except Exception as e:
        raise RuntimeError(f"Batch processing failed: {str(e)}")
