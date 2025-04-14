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
      path: "{{ input_file }}"
```

### Environment Variables

Environment variables can be defined in several ways:

1. In the workflow file:
```yaml
env:
  API_URL: "https://api.example.com"
  DEBUG: "true"
```

2. Using environment variables:
```yaml
env:
  API_KEY: "${API_KEY}"  # From system environment
  DEBUG: "${DEBUG:-false}"  # With default value
```

3. From a .env file in the workspace:
```
API_KEY=your-api-key
DEBUG=true
```

### Parameters

Parameters make workflows reusable and configurable:

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

2. Task parameters:
```yaml
  params:
    input: "{{ input_file }}"
    output: "{{ output_file }}"
```

3. Conditions:
```yaml
  condition: "{{ prev_step.success and input_file }}"
```

4. Error handling:
```yaml
  retry:
    max_attempts: 3
    delay: 5
  on_error:
    action: continue
    message: "Processing failed, continuing..."
```

5. Output capture:
```yaml
  output_var: process_result
```

### Template Variables

Available template variables:

1. Parameters:
```yaml
{{ input_file }}  # Access parameter
{{ params.input_file }}  # Full parameter object
```

2. Environment:
```yaml
{{ env.API_KEY }}  # Environment variable
```

3. Step outputs:
```yaml
{{ steps.process_data.output }}  # Step output
{{ prev_step.output }}  # Previous step
```

4. Built-in variables:
```yaml
{{ workflow_dir }}  # Workflow directory
{{ run_id }}  # Unique run ID
{{ current_timestamp }}  # Current time
```

### Workspace Configuration

Create `.yaml-workflow.yaml` in your project root:

```yaml
# Project-level settings
project:
  name: my-project
  description: Project description

# Default settings for all workflows
defaults:
  env:
    DEBUG: false
  retry:
    max_attempts: 3
  temp_dir: .workflow/temp

# Task-specific defaults
tasks:
  shell:
    timeout: 300
  http_request:
    retry:
      max_attempts: 5
``` 