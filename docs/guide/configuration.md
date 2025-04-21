# Configuration Guide

This guide explains how to configure YAML Workflow for your needs.

## Workflow Configuration

### Basic Structure

A workflow file consists of these main sections:

```yaml
name: My Workflow
description: A description of what this workflow does

# Optional version for compatibility
version: "1.0"

# Optional environment variables
env:
  DEBUG: "true"
  TEMP_DIR: "./temp"

# Parameter definitions
params:
  input_file:
    description: Input file to process
    type: string
    required: true
  batch_size:
    description: Number of items to process at once
    type: integer
    default: 100

# Optional flow definitions
flows:
  default: main_flow
  definitions:
    - main_flow: [validate, process, report]
    - cleanup: [archive, cleanup]

# Workflow steps
steps:
  - name: validate
    task: file_check
    params:
      path: "{{ args.input_file }}"
  - name: process_data
    task: python_code
    description: Processes input data based on environment.
    inputs:
      data_source: "{{ args.source }}"
  - name: process_batch
    task: batch
    inputs:
      # Input items to process
      # Assuming get_items returns the list directly as its result
      items: "{{ steps.get_items.result }}"
      
      # Processing configuration
      chunk_size: 10
      max_workers: 4
      
      # Processing task
      task:
        task: python_code
        inputs:
          code: "process_item()"
      
      # Optional argument name for items (defaults to "item")
      arg_name: data_item

### Accessing Step Results

   The results of completed steps are stored in the `steps` namespace. All results are nested under a `result` key for consistency and to avoid potential name collisions.

   ```yaml
   # Example Step
   - name: process_data
     task: some_task
     # ... other params ...

   # Accessing results in a later step
   - name: use_result
     task: another_task
     inputs:
       # If process_data returns a single value (e.g., a string or number)
       input_value: "{{ steps.process_data.result }}"

       # If process_data returns a dictionary (e.g., {'status': 'ok', 'file_path': '/path/to/file'})
       status_from_prev: "{{ steps.process_data.result.status }}"
       path_from_prev: "{{ steps.process_data.result.file_path }}"
   ```

### Batch Processing

Configure batch processing tasks:

```yaml
# Example Batch Processing Step Configuration (Replace with actual example if available)
steps:
  - name: process_batch_example
    task: batch_processor # Or relevant batch task type
    inputs:
      items: "{{ steps.get_items.result }}" # Assuming get_items returns a list
      chunk_size: 10
      # ... other batch parameters ...
      task: # The task to run on each item/chunk
        task: python_code 
        # ... sub-task inputs ... 
```

### Template Variables

Available template variables are organized in namespaces:

1.  **Arguments (`args`)**: Access parameters passed to the workflow.
    ```yaml
    {{ args.input_file }}      # Access parameter value
    {{ args.mode }}           # Access parameter with default
    ```

2.  **Environment Variables (`env`)**: Access environment variables.
    ```yaml
    {{ env.API_KEY }}        # Environment variable
    {{ env.DEBUG }}         # Environment variable with default
    ```

3.  **Step Results (`steps`)**: Access results from previous steps.
    ```yaml
    # Access the entire result (if it's a single value or you need the whole dict)
    {{ steps.previous_step.result }}

    # Access a specific key if the result is a dictionary
    {{ steps.previous_step.result.specific_key }}

    # Access the status of a step (completed, failed, skipped) - accessed directly
    {{ steps.previous_step.status }} 
    ```
    *Note: Step status is accessed directly via `steps.STEP_NAME.status`, not nested under `result`.*

4.  **Built-in Variables (`workflow`)**: Access workflow metadata.
    ```yaml
    {{ workflow.name }}          # Workflow name
    {{ workflow.workspace }}     # Workspace directory
    {{ workflow.run_id }}        # Unique run ID
    {{ workflow.timestamp }}     # Current time
    ``` 

# Use StrictUndefined to catch missing variables
settings:
  error_handling:
    undefined_variables: strict

steps:
  - name: task_with_potential_error
    task: python_code # Use python_code for example
    inputs:
      code: |
        # This will raise TemplateError if 'args.maybe_missing' is not provided
        value = "{{ args.maybe_missing }}"
        result = value.upper() 