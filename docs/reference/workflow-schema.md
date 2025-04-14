# Workflow Schema Reference

This document provides a complete reference of the workflow file schema.

## Top-Level Structure

```yaml
# Required fields
name: string                 # Workflow name
steps: array                 # List of workflow steps

# Optional fields
description: string         # Workflow description
version: string            # Schema version (default: "1.0")
env: object               # Environment variables
params: object            # Parameter definitions
flows: object            # Flow definitions
```

## Complete Schema

```yaml
# Workflow metadata
name: string
description: string
version: string  # Semantic version

# Environment variables
env:
  KEY: string | "${ENV_VAR}" | "${ENV_VAR:-default}"

# Parameter definitions
params:
  parameter_name:
    type: string | integer | float | boolean | array | object
    description: string
    required: boolean
    default: any
    choices: array        # For enum parameters
    min: number          # For numeric parameters
    max: number          # For numeric parameters
    pattern: string      # Regex pattern for string validation
    validate:            # Custom validation rules
      - rule_name
    transform:           # Transformation rules
      - transform_name

# Flow definitions
flows:
  default: string        # Default flow name
  definitions:
    - flow_name: array   # List of step names

# Workflow steps
steps:
  - name: string        # Step name (required)
    task: string        # Task type (required)
    description: string # Step description
    condition: string   # Jinja2 expression
    params: object      # Task-specific parameters
    retry:
      max_attempts: integer
      delay: integer
      backoff_factor: float
      retry_on: array
    on_error:
      action: continue | abort | retry
      message: string
      output: any
    output_var: string  # Variable to store output
```

## Task-Specific Schemas

### Shell Task

```yaml
task: shell
command: string
shell: string      # Optional, default: /bin/sh
cwd: string        # Working directory
env: object        # Additional environment variables
timeout: integer   # Timeout in seconds
```

### HTTP Request Task

```yaml
task: http_request
params:
  url: string
  method: GET | POST | PUT | DELETE | PATCH
  headers: object
  params: object   # Query parameters
  data: any        # Request body
  json: object     # JSON request body
  files: object    # File uploads
  timeout: integer
  verify_ssl: boolean
  auth:
    type: basic | bearer
    username: string  # For basic auth
    password: string  # For basic auth
    token: string    # For bearer auth
```

### File Tasks

```yaml
# File check
task: file_check
params:
  path: string
  required: boolean
  readable: boolean
  writable: boolean
  extension: string

# Write file
task: write_file
params:
  file_path: string
  content: string
  mode: string
  encoding: string

# Write JSON
task: write_json
params:
  file_path: string
  data: any
  indent: integer
  encoding: string

# Write YAML
task: write_yaml
params:
  file_path: string
  data: any
  default_flow_style: boolean
  encoding: string
```

## Template Variables

### Built-in Variables

```yaml
{{ workflow_dir }}        # Workflow directory
{{ run_id }}             # Unique run ID
{{ current_timestamp }}  # Current time
{{ env.VAR_NAME }}      # Environment variable
{{ params.PARAM_NAME }} # Parameter value
{{ steps.STEP_NAME }}   # Step information
{{ prev_step }}         # Previous step information
```

### Step Information

```yaml
steps.STEP_NAME:
  output: any           # Step output
  success: boolean      # Step success status
  error: string        # Error message if failed
  duration: float      # Step duration in seconds
  start_time: string   # Step start time
  end_time: string     # Step end time
```

## Workspace Configuration

```yaml
# .yaml-workflow.yaml
project:
  name: string
  description: string

defaults:
  env: object
  retry: object
  temp_dir: string

tasks:
  task_type:
    timeout: integer
    retry: object
    other_defaults: any
``` 