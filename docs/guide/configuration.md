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
  - name: process_batch
    task: batch
    inputs:
      # Input items to process
      items: "{{ steps.get_items.output }}"
      
      # Processing configuration
      chunk_size: 10
      max_workers: 4
      
      # Processing task
      task:
        task: python
        inputs:
          code: "process_item()"
      
      # Optional argument name for items (defaults to "item")
      arg_name: data_item
```

### Environment Variables

Environment variables are accessed using the `env` namespace:

1. In the workflow file:
```yaml
env:
  API_URL: "https://api.example.com"
  DEBUG: "true"
```

2. Using environment variables:
```yaml
steps:
  - name: api_call
    task: http
    params:
      url: "{{ env.API_URL }}"
      debug: "{{ env.DEBUG }}"
```

3. From a .env file in the workspace:
```
API_KEY=your-api-key
DEBUG=true
```

### Parameters

Parameters are accessed using the `args` namespace:

```yaml
params:
  # Simple string parameter
  name:
    type: string
    required: true
    description: Your name

  # Number with validation
  age:
    type: integer
    min: 0
    max: 150
    default: 30

  # Enum parameter
  mode:
    type: string
    choices: [fast, accurate]
    default: accurate

  # File parameter
  config_file:
    type: string
    description: Path to config file
    validate:
      - file_exists
      - is_readable

# Using parameters in steps
steps:
  - name: greet
    task: python
    params:
      name: "{{ args.name }}"
      mode: "{{ args.mode }}"
```

### Flow Control

Flows allow organizing steps into logical groups:

```yaml
flows:
  # Default flow to run
  default: process

  # Flow definitions
  definitions:
    - process: [validate, transform, save]
    - validate: [validate]
    - cleanup: [archive, cleanup]
```

Run specific flows using:
```bash
yaml-workflow run workflow.yaml --flow validate
```

### Step Configuration

Each step can have:

1. Basic properties:
```yaml
- name: process_data
  task: shell
  description: Process input data
```

2. Task parameters with error handling:
```yaml
  params:
    input: "{{ args.input_file }}"
    output: "{{ args.output_file }}"
  error_handling:
    undefined_variables: strict  # Raises error for undefined variables
    show_available: true        # Shows available variables in error messages
```

3. Conditions with proper variable access:
```yaml
  condition: "{{ steps.previous_step.status == 'completed' and args.input_file }}"
```

4. Error handling with retries:
```yaml
  retry:
    max_attempts: 3
    delay: 5
  on_error:
    action: continue
    message: "Processing failed: {{ error }}"
    notify: "{{ env.ADMIN_EMAIL }}"
```

5. Output capture and access:
```yaml
  outputs:
    - result
    - metadata
  # Access in later steps
  # {{ steps.process_data.outputs.result }}
  # {{ steps.process_data.outputs.metadata }}
```

### Batch Processing

Configure batch processing tasks:

```yaml
steps:
  - name: process_batch
    task: batch_processor
    params:
      # Input items to process
      items: "{{ steps.get_items.output }}"
      
      # Processing configuration
      chunk_size: 10
      max_workers: 4
      
      # Processing task
      task: python
      function: process_item
      
      # Error handling
      on_error: continue
      error_handler: log_error
      
      # Result handling
      aggregator: combine_results
      
      # State management
      resume: true
```

### Template Variables

Available template variables are organized in namespaces:

1. Arguments (Parameters):
```yaml
{{ args.input_file }}      # Access parameter value
{{ args.mode }}           # Access parameter with default
```

2. Environment Variables:
```yaml
{{ env.API_KEY }}        # Environment variable
{{ env.DEBUG }}         # Environment variable with default
```

3. Step Outputs:
```yaml
{{ steps.process.output }}         # Direct output
{{ steps.process.outputs.result }} # Named output
{{ steps.process.status }}        # Step status
{{ steps.process.error }}         # Error message if failed
```

4. Built-in Variables:
```yaml
{{ workflow.name }}          # Workflow name
{{ workflow.workspace }}     # Workspace directory
{{ workflow.run_id }}        # Unique run ID
{{ workflow.timestamp }}     # Current time
```

### Error Handling

Improved error messages help diagnose issues:

1. Undefined Variables:
```
TemplateError: Variable 'result' is undefined. Available variables:
- args: [input_file, mode, batch_size]
- env: [API_KEY, DEBUG]
- steps: [validate, process]
```

2. Invalid Access:
```
TemplateError: Invalid step attribute 'results'. Valid attributes:
- output: Raw step output
- outputs: Named outputs
- status: Step status
- error: Error message
- timestamp: Execution time
```

### Workspace Configuration

Create `.yaml-workflow.yaml` in your project root:

```yaml
# Project-level settings
project:
  name: my-project
  description: Project description

# Default settings
defaults:
  error_handling:
    undefined_variables: strict
    show_available: true
  
  batch_processing:
    chunk_size: 10
    max_workers: 4
    resume: true
``` 