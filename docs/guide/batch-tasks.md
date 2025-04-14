# Batch Task Processing

This guide covers how to effectively use batch processing capabilities in YAML Workflow to handle large datasets and long-running operations.

## Overview

Batch processing allows you to:
- Process large datasets in manageable chunks
- Track progress and maintain state between runs
- Handle errors gracefully with retry mechanisms
- Process items in parallel for improved performance
- Resume processing from the last successful point

## Basic Batch Processing

Here's a simple example of a batch processing workflow:

```yaml
name: process-numbers
description: Process a list of numbers in batches
version: '1.0'

params:
  numbers:
    type: list
    description: List of numbers to process
    default: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  batch_size:
    type: integer
    description: Size of each batch
    default: 3

steps:
  split_into_batches:
    type: python
    inputs:
      code: |
        numbers = params['numbers']
        batch_size = params['batch_size']
        batches = [numbers[i:i + batch_size] for i in range(0, len(numbers), batch_size)]
        result = batches

  process_batches:
    type: python
    for_each: "{{ steps.split_into_batches.result }}"
    inputs:
      operation: multiply
      item: "{{ item }}"
      factor: 2
    retry:
      max_attempts: 3
      delay: 5
```

## Chunk Processing

Chunk processing helps manage memory usage and processing time by breaking large datasets into smaller pieces:

```yaml
steps:
  read_large_dataset:
    type: python
    inputs:
      code: |
        # Example: Reading a large dataset in chunks
        chunk_size = 1000
        total_chunks = len(data) // chunk_size + 1
        chunks = []
        for i in range(total_chunks):
          start = i * chunk_size
          end = start + chunk_size
          chunks.append(data[start:end])
        result = chunks

  process_chunks:
    type: python
    for_each: "{{ steps.read_large_dataset.result }}"
    inputs:
      operation: custom
      handler: process_chunk
      item: "{{ item }}"
```

## State Management

The workflow engine maintains state between runs, allowing for resumption of interrupted processing:

```yaml
steps:
  track_progress:
    type: python
    inputs:
      code: |
        # Store progress in context
        context['processed_count'] = context.get('processed_count', 0) + len(item)
        context['total_items'] = len(params['numbers'])
        result = {
          'processed': context['processed_count'],
          'total': context['total_items'],
          'progress': f"{(context['processed_count'] / context['total_items']) * 100:.2f}%"
        }
```

## Progress Tracking

Monitor batch processing progress using built-in tracking capabilities:

```yaml
steps:
  process_with_progress:
    type: python
    for_each: "{{ steps.split_into_batches.result }}"
    inputs:
      operation: custom
      handler: process_items
      item: "{{ item }}"
      on_progress: |
        def update_progress(items_processed, total_items):
          print(f"Progress: {items_processed}/{total_items} items processed")
```

## Error Handling

Implement robust error handling for batch operations:

```yaml
steps:
  process_with_error_handling:
    type: python
    for_each: "{{ steps.split_into_batches.result }}"
    inputs:
      operation: custom
      handler: process_batch
      item: "{{ item }}"
    retry:
      max_attempts: 3
      delay: 5
    on_error:
      action: continue
      save_error: true
      
  handle_failed_items:
    type: python
    if: "{{ steps.process_with_error_handling.failed_items|length > 0 }}"
    inputs:
      code: |
        failed_items = steps['process_with_error_handling']['failed_items']
        print(f"Failed items: {failed_items}")
        # Handle failed items (e.g., save to error log, notify, etc.)
```

## Parallel Processing

Leverage parallel processing for improved performance:

```yaml
steps:
  parallel_process:
    type: python
    for_each: "{{ steps.split_into_batches.result }}"
    parallel:
      max_parallel: 4  # Process up to 4 batches simultaneously
    inputs:
      operation: custom
      handler: process_batch
      item: "{{ item }}"
```

## Best Practices

1. **Chunk Size**: Choose appropriate chunk sizes based on:
   - Available memory
   - Processing complexity
   - Required processing time
   
2. **State Management**:
   - Store progress information in the context
   - Use checkpoints for long-running operations
   - Implement resume capabilities

3. **Error Handling**:
   - Implement retry mechanisms
   - Log failed items
   - Provide cleanup steps

4. **Performance**:
   - Use parallel processing when appropriate
   - Monitor resource usage
   - Optimize batch sizes based on performance metrics

5. **Monitoring**:
   - Track progress regularly
   - Log important metrics
   - Implement alerting for failures

## Example: Complete Batch Processing Workflow

Here's a complete example combining all the features:

```yaml
name: process-dataset
description: Process a large dataset with full features
version: '1.0'

params:
  input_data:
    type: list
    description: Data to process
  chunk_size:
    type: integer
    default: 1000
  max_parallel:
    type: integer
    default: 4

steps:
  prepare_chunks:
    type: python
    inputs:
      code: |
        data = params['input_data']
        chunk_size = params['chunk_size']
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
        result = chunks

  process_chunks:
    type: python
    for_each: "{{ steps.prepare_chunks.result }}"
    parallel:
      max_parallel: "{{ params.max_parallel }}"
    inputs:
      operation: custom
      handler: process_chunk
      item: "{{ item }}"
    retry:
      max_attempts: 3
      delay: 5
    on_error:
      action: continue
      save_error: true

  track_progress:
    type: python
    inputs:
      code: |
        processed = len(steps['process_chunks']['completed_items'])
        total = len(params['input_data'])
        failed = len(steps['process_chunks']['failed_items'])
        result = {
          'processed': processed,
          'total': total,
          'failed': failed,
          'success_rate': f"{((processed - failed) / total) * 100:.2f}%"
        }

  handle_failures:
    type: python
    if: "{{ steps.process_chunks.failed_items|length > 0 }}"
    inputs:
      code: |
        failed_items = steps['process_chunks']['failed_items']
        # Log failures and send notifications
        result = {
          'failed_count': len(failed_items),
          'failed_items': failed_items
        }
```

This documentation provides a comprehensive guide to batch processing capabilities, focusing on real-world usage patterns and best practices. 