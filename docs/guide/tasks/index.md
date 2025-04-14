# Task Types

YAML Workflow provides several types of tasks that can be used in your workflows. Each task type serves a specific purpose and has its own set of parameters and capabilities.

## Basic Tasks

Simple utility tasks for common operations:

- `echo`: Print a message to the console
- `fail`: Deliberately fail a workflow (useful for testing)
- `hello_world`: Simple greeting task
- `add_numbers`: Add two numbers together
- `join_strings`: Concatenate strings
- `create_greeting`: Create a customized greeting

Example:
```yaml
steps:
  - name: greet
    task: echo
    inputs:
      message: "Hello, World!"

  - name: add
    task: add_numbers
    inputs:
      a: 5
      b: 3
    outputs: result
```

## File Operations

Tasks for working with files and directories:

- `write_file`: Write content to a file
- `read_file`: Read content from a file
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

Example:
```yaml
steps:
  - name: process_data
    task: shell
    command: |
      python process.py \
        --input {{ input_file }} \
        --output {{ output_file }}
    outputs:
      result: $(cat {{ output_file }})
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

Example:
```yaml
steps:
  - name: process_data
    task: python
    code: |
      import json
      
      # Process data
      data = json.loads(input_data)
      result = {
          'count': len(data),
          'sum': sum(data)
      }
      
      # Return results
      return result
    inputs:
      input_data: "{{ previous_step.output }}"
    outputs: processing_result
```

## Batch Processing

Process data in batches:

- `batch`: Process items in batches with configurable size and parallelism

Example:
```yaml
steps:
  - name: process_items
    task: batch
    inputs:
      items: ["item1", "item2", "item3", "item4"]
      batch_size: 2
      parallel: true
      task:
        type: shell
        command: "process_item.sh {{ item }}"
    outputs: batch_results
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