# Task Types

YAML Workflow provides several types of tasks that can be used in your workflows. Each task type serves a specific purpose and has its own set of parameters and capabilities.

## Common Task Properties

Every task in YAML Workflow supports these properties:

```yaml
steps:
  - name: task_name          # Required: Unique name for the task
    task: task_type         # Required: Type of task to execute
    description: string     # Optional: Description of what the task does
    inputs: {}             # Optional: Task-specific input parameters
    outputs: string/object  # Optional: Where to store task results
    condition: string      # Optional: Condition for task execution
    retry:                 # Optional: Retry configuration
      max_attempts: int    # Number of retry attempts
      delay: int          # Delay between retries in seconds
      backoff: float      # Exponential backoff multiplier
    on_error:             # Optional: Error handling configuration
      action: string      # One of: fail, continue, retry
      message: string     # Custom error message
      next: string        # Next task to execute on error
    timeout: int          # Optional: Task timeout in seconds
    depends_on: []        # Optional: List of task dependencies
```

## Basic Tasks

Simple utility tasks for common operations:

- `echo`: Print a message to the console
  ```yaml
  task: echo
  inputs:
    message: string       # Required: Message to print
    level: string        # Optional: Log level (info, warning, error)
  ```

- `fail`: Deliberately fail a workflow (useful for testing)
  ```yaml
  task: fail
  inputs:
    message: string      # Optional: Custom failure message
    code: int           # Optional: Exit code (default: 1)
  ```

- `add_numbers`: Add two numbers together
  ```yaml
  task: add_numbers
  inputs:
    a: number          # Required: First number
    b: number          # Required: Second number
  outputs: sum         # Result of a + b
  ```

- `join_strings`: Concatenate strings
  ```yaml
  task: join_strings
  inputs:
    strings: [string]  # Required: List of strings to join
    separator: string  # Optional: Separator (default: '')
  outputs: result     # Joined string
  ```

## File Operations

Tasks for working with files and directories:

- `write_file`: Write content to a file
  ```yaml
  task: write_file
  inputs:
    file_path: string   # Required: Path to write to
    content: string     # Required: Content to write
    mode: string        # Optional: Write mode (w, a, default: w)
    encoding: string    # Optional: File encoding (default: utf-8)
  ```

- `read_file`: Read content from a file
  ```yaml
  task: read_file
  inputs:
    file_path: string   # Required: Path to read from
    encoding: string    # Optional: File encoding (default: utf-8)
  outputs: content     # File contents
  ```

- `append_file`: Append content to a file
- `copy_file`: Copy a file to another location
- `move_file`: Move/rename a file
- `delete_file`: Delete a file

Example:
```yaml
steps:
  - name: write_config
    task: write_file
    inputs:
      file_path: config.json
      content: |
        {
          "setting": "value"
        }

  - name: read_data
    task: read_file
    inputs:
      file_path: data.txt
    outputs: file_content
```

## Shell Commands

Execute shell commands and scripts:

- `shell`: Run shell commands with variable substitution
  ```yaml
  task: shell
  inputs:
    command: string     # Required: Command to execute
    cwd: string        # Optional: Working directory
    env: object        # Optional: Additional environment variables
    shell: string      # Optional: Shell to use (default: /bin/sh)
  outputs:
    stdout: string     # Command standard output
    stderr: string     # Command standard error
    exit_code: int     # Command exit code
  ```

## Template Processing

Tasks for template rendering and text processing:

- `template`: Render a template with variable substitution

Example:
```yaml
steps:
  - name: generate_report
    task: template
    template: |
      # Report for {{ date }}
      
      Total records: {{ count }}
      Status: {{ status }}
    output: report.md
```

## Python Integration

Execute Python code within workflows:

- `python`: Run Python code with access to workflow context
  ```yaml
  task: python
  inputs:
    code: string       # Required: Python code to execute
    globals: object    # Optional: Global variables
    locals: object     # Optional: Local variables
    packages: [string] # Optional: Additional packages to import
  outputs: result     # Return value from Python code
  ```

## Batch Processing

Process data in batches:

- `batch`: Process items in batches with configurable size and parallelism
  ```yaml
  task: batch
  inputs:
    items: [any]       # Required: List of items to process
    batch_size: int    # Optional: Items per batch (default: 10)
    parallel: bool     # Optional: Process in parallel (default: false)
    max_workers: int   # Optional: Max parallel workers (default: 4)
    task:             # Required: Task configuration to run for each item
      type: string    # Task type to execute
      inputs: object  # Task inputs (item available as {{ item }})
  outputs:
    results: [any]    # List of task results
    failed: [any]     # List of failed items
  ```

## Task Features

All tasks support these common features:

1. **Variable Substitution**
   - Use `{{ variable }}` syntax to reference variables
   - Access step outputs, environment variables, and parameters

2. **Output Capture**
   - Store task results in variables
   - Use outputs in subsequent steps

3. **Error Handling**
   - Configure retry behavior
   - Define error handling steps
   - Set custom error messages

4. **Conditional Execution**
   - Run tasks based on conditions
   - Skip tasks when conditions aren't met

See the specific task documentation for detailed parameter lists and usage examples.

## Data Processing

### `write_json`
Writes data as JSON to a file.

```yaml
- name: save_json
  task: write_json
  params:
    file_path: "output/data.json"
    data: "{{ process_result }}"
    indent: 2
```

### `write_yaml`
Writes data as YAML to a file.

```yaml
- name: save_yaml
  task: write_yaml
  params:
    file_path: "output/config.yaml"
    data: "{{ config_data }}"
```

## HTTP Operations

### `http_request`
Makes HTTP requests.

```yaml
- name: fetch_data
  task: http_request
  params:
    url: "https://api.example.com/data"
    method: GET
    headers:
      Authorization: "Bearer {{ api_token }}"
```

## Creating Custom Tasks

You can create custom tasks by:

1. Creating a Python class that inherits from `BaseTask`
2. Implementing the required methods
3. Registering the task with the engine

Example:
```python
from yaml_workflow.tasks import BaseTask

class CustomTask(BaseTask):
    def run(self, params):
        # Task implementation
        pass

# Register the task
register_task("custom_task", CustomTask) 
```

## Error Handling

Tasks can be configured to handle errors in different ways:

1. **Retry Configuration**
   ```yaml
   retry:
     max_attempts: 3        # Maximum number of attempts
     delay: 5              # Delay between attempts (seconds)
     backoff: 2           # Exponential backoff multiplier
     on_error: [string]   # Retry only on specific errors
   ```

2. **Error Actions**
   ```yaml
   on_error:
     action: continue     # continue, fail, or retry
     message: string      # Custom error message
     next: cleanup       # Next task to execute on error
   ```

3. **Conditional Execution**
   ```yaml
   condition: "{{ prev_step.success and input_file }}"
   ```

## Task Dependencies

Tasks can specify dependencies using the `depends_on` property:

```yaml
steps:
  - name: first_task
    task: echo
    inputs:
      message: "First"

  - name: second_task
    task: echo
    inputs:
      message: "Second"
    depends_on: [first_task]

  - name: parallel_task
    task: echo
    inputs:
      message: "Can run in parallel with second_task"
    depends_on: [first_task]
```

Dependencies can be:
- Single task: `depends_on: task_name`
- Multiple tasks: `depends_on: [task1, task2]`
- Conditional: `depends_on: "{{ success_of_task }}"` 