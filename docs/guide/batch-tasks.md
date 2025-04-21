# Batch Task Processing

This guide covers how to effectively use batch processing capabilities in YAML Workflow to handle large datasets and long-running operations.

## Overview

Batch processing allows you to:
- Process large datasets in manageable chunks
- Track progress and maintain state between runs
- Handle errors gracefully with standardized error handling
- Process items in parallel for improved performance
- Resume processing from the last successful point
- Access batch-specific context variables

## Basic Batch Processing

Here's a simple example of a batch processing workflow:

```yaml
name: process-items
description: Process a list of items in batches
version: '1.0'

args:
  items:
    type: list
    description: List of items to process
    default: ["item1", "item2", "item3", "item4", "item5"]
  chunk_size:
    type: integer
    description: Size of each batch
    default: 2

steps:
  process_items:
    name: process_items
    task: batch
    inputs:
      items: "{{ args.items }}"
      chunk_size: "{{ args.chunk_size }}"
      max_workers: 2  # Process up to 2 chunks in parallel
      task:  # Task configuration for processing each item
        task: python_code 
        inputs:
          code: |
            # Access item via batch namespace
            echo "Processing item {{ batch.item }} ({{ batch.index + 1 }}/{{ batch.total }})"
            ./process.sh "{{ batch.item }}"
```

## Batch Context

Each item in a batch has access to these context variables:

- `batch.item`: The current item being processed
- `batch.index`: Zero-based index of the current item
- `batch.total`: Total number of items in the batch
- `batch.name`: Name of the batch task

Example using batch context:

```yaml
steps:
  process_files:
    name: process_files
    task: batch
    inputs:
      items: "{{ args.files }}"
      task:
        task: python_code
        inputs:
          code: |
            # Access batch context
            current_file = batch['item']
            progress = f"{batch['index'] + 1}/{batch['total']}"
            task_name = batch['name']
            
            print(f"[{task_name}] Processing {current_file} ({progress})")
            result = process_file(current_file)
```

## Error Handling

Batch tasks use standardized error handling:

```yaml
steps:
  process_with_retries:
    name: process_with_retries
    task: batch
    inputs:
      items: "{{ args.items }}"
      retry:
        max_attempts: 3
        delay: 5
      task:
        task: python_code
        inputs:
          code: "./process.sh {{ batch.item }}"
          
  handle_results:
    name: handle_results
    task: python_code
    inputs:
      code: |
        results = steps['process_with_retries']['results']
        
        # Check each result
        for result in results:
          if 'error' in result:
            print(f"Item {result['index']} failed: {result['error']}")
          else:
            print(f"Item {result['index']} succeeded: {result['result']}")
```

## State Tracking

The batch processor maintains detailed state information:

```yaml
steps:
  process_items:
    name: process_items
    task: batch
    inputs:
      items: "{{ args.items }}"
      task:
        task: python_code
        inputs:
          code: |
            # Process item and update state
            result = process_item(batch['item'])
            
            # Results are automatically tracked
            return {
              'item': batch['item'],
              'status': 'completed',
              'output': result
            }
            
  check_progress:
    name: check_progress
    task: python_code
    inputs:
      code: |
        batch_results = steps['process_items']['results']
        
        # Analyze results
        completed = [r for r in batch_results if 'result' in r]
        failed = [r for r in batch_results if 'error' in r]
        
        print(f"Completed: {len(completed)}/{len(batch_results)}")
        print(f"Failed: {len(failed)}/{len(batch_results)}")
```

## Performance Optimization

Optimize batch processing with these features:

```yaml
steps:
  optimized_processing:
    name: optimized_processing
    task: batch
    inputs:
      items: "{{ args.items }}"
      chunk_size: 10          # Process 10 items at a time
      max_workers: 4          # Use 4 parallel workers
      retry:
        max_attempts: 3       # Retry failed items up to 3 times
        delay: 5              # Wait 5 seconds between retries
      task:
        task: python_code
        inputs:
          code: "./process.sh {{ batch.item }}"
          timeout: 300        # Timeout after 5 minutes
          working_dir: "{{ env.WORKSPACE }}/{{ batch.item }}"
```

## Best Practices

1. **Chunk Size**:
   - Balance memory usage and performance
   - Consider item processing complexity
   - Test with different sizes for optimization

2. **Error Handling**:
   - Always implement retry mechanisms
   - Use standardized error handling
   - Track failed items for analysis
   - Provide meaningful error messages

3. **State Management**:
   - Use the built-in state tracking
   - Monitor progress regularly
   - Implement proper cleanup
   - Handle interruptions gracefully

4. **Performance**:
   - Use appropriate chunk sizes
   - Enable parallel processing when suitable
   - Monitor resource usage
   - Set reasonable timeouts

5. **Context Usage**:
   - Use batch context variables
   - Maintain namespace isolation
   - Follow variable naming conventions
   - Document context requirements

## Complete Example

Here's a comprehensive batch processing workflow:

```yaml
name: process-dataset
description: Process a large dataset with full features
version: '1.0'

args:
  input_files:
    type: list
    description: Files to process
  chunk_size:
    type: integer
    default: 10
  max_workers:
    type: integer
    default: 4

env:
  WORKSPACE: "/data/processing"
  API_KEY: "{{ args.api_key }}"

steps:
  validate_inputs:
    name: validate_inputs
    task: python_code
    inputs:
      code: |
        files = args['input_files']
        if not files:
          raise TaskExecutionError("No input files provided")
        result = [f for f in files if os.path.exists(f)]
        
  process_files:
    name: process_files
    task: batch
    inputs:
      items: "{{ steps.validate_inputs.result }}"
      chunk_size: "{{ args.chunk_size }}"
      max_workers: "{{ args.max_workers }}"
      retry:
        max_attempts: 3
        delay: 5
      task:
        task: python_code
        inputs:
          command: |
            echo "[{{ batch.index + 1 }}/{{ batch.total }}] Processing {{ batch.item }}"
            ./process.sh \
              --input "{{ batch.item }}" \
              --output "{{ env.WORKSPACE }}/output/{{ batch.index }}" \
              --api-key "{{ env.API_KEY }}"
          working_dir: "{{ env.WORKSPACE }}"
          timeout: 300
          
  generate_report:
    name: generate_report
    task: python_code
    inputs:
      code: |
        results = steps['process_files']['results']
        
        # Analyze results
        completed = [r for r in results if 'result' in r]
        failed = [r for r in results if 'error' in r]
        
        # Generate report
        report = {
          'total': len(results),
          'completed': len(completed),
          'failed': len(failed),
          'success_rate': len(completed) / len(results) * 100,
          'failed_items': [r['item'] for r in failed]
        }
        
        # Save report
        with open('report.json', 'w') as f:
          json.dump(report, f, indent=2)
        
        result = report
```

This documentation provides a comprehensive guide to batch processing capabilities, focusing on real-world usage patterns and best practices. 