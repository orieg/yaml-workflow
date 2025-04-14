# Built-in Tasks

The YAML Workflow Engine comes with several built-in tasks that cover common use cases.

## File Operations

### `file_check`
Checks if a file exists and has the required permissions.

```yaml
- name: check_input
  task: file_check
  params:
    path: "data/input.csv"
    required: true
    readable: true
```

### `write_file`
Writes content to a file.

```yaml
- name: save_output
  task: write_file
  params:
    file_path: "output/result.txt"
    content: "{{ process_result }}"
```

## Shell Commands

### `shell`
Executes shell commands.

```yaml
- name: process_data
  task: shell
  command: python process.py --input {{ input_file }} --output {{ output_file }}
```

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

## Task Features

All tasks support these common features:

### Conditions
```yaml
- name: optional_step
  task: shell
  command: echo "Running optional step"
  condition: "{{ env.DEBUG == 'true' }}"
```

### Error Handling
```yaml
- name: critical_step
  task: shell
  command: python important_process.py
  retry:
    max_attempts: 3
    delay: 5
  on_error: abort
```

### Output Capture
```yaml
- name: get_version
  task: shell
  command: git describe --tags
  output_var: current_version
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