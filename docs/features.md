# Features

YAML Workflow provides a rich set of features for building and executing workflows. This document outlines the key features and their usage.

## Core Features

### YAML-Driven Configuration

Define workflows using simple YAML syntax:

```yaml
name: data_processing
description: Process and transform data files
version: "1.0.0"

steps:
  - name: read_data
    task: read_file
    params:
      file_path: input.csv

  - name: transform
    task: python
    params:
      function: transform_data
      params:
        data: "{{ read_data.output }}"
```

### Dynamic Variable Resolution

Use Jinja2 templates for dynamic values. For comprehensive documentation on templating features and best practices, see the [Templating Guide](guide/templating.md).

```yaml
steps:
  - name: generate_report
    task: template
    params:
      template: |
        Report generated on {{ now() }}
        Data processed: {{ input_file }}
        Results: {{ previous_step.output }}
      variables:
        input_file: data.csv
```

### Flow Control

Define multiple execution paths:

```yaml
flows:
  default: process_all
  definitions:
    - process_all: [validate, transform, save]
    - validate_only: [validate]
    - transform_only: [transform]
```

## Task System

### Built-in Tasks

Basic Tasks:
- Echo (`echo`)
- Hello World (`hello_world`)
- Add Numbers (`add_numbers`)
- Join Strings (`join_strings`)
- Create Greeting (`create_greeting`)
- Fail (for testing) (`fail`)

File Operations:
- Read File (`read_file`)
- Write File (`write_file`)
- Append File (`append_file`)
- Copy File (`copy_file`)
- Move File (`move_file`)
- Delete File (`delete_file`)
- Read JSON (`read_json`)
- Write JSON (`write_json`)
- Read YAML (`read_yaml`)
- Write YAML (`write_yaml`)

Other Tasks:
- Shell Command Execution (`shell`)
- Python Function Execution (`python`)
- Template Rendering (`template`)
- Batch Processing (`batch`)

### Custom Task Creation

Create your own task types:

```python
from yaml_workflow.tasks import register_task

@register_task("custom_task")
def custom_task_handler(step, context, workspace):
    """
    Custom task implementation.
    
    Args:
        step (dict): Step configuration from YAML
        context (dict): Workflow context
        workspace (Path): Workspace directory
    
    Returns:
        Any: Task result
    """
    params = step.get("params", {})
    # Process inputs and perform task
    return {"result": "Task completed"}
```

### Task Features

1. **Parameter Management**
   - Type validation
   - Automatic conversion
   - Output capturing

2. **Error Handling**
   - Retry mechanisms
   - Error recovery
   - Custom error actions

3. **Progress Tracking**
   - Step completion
   - Time estimation
   - Resource monitoring

## Parallel Processing

### Batch Operations

Process items in parallel:

```yaml
steps:
  - name: process_files
    task: batch
    params:
      iterate_over: ["file1.txt", "file2.txt"]
      parallel: true
      max_workers: 4
      processing_task:
        task: shell
        params:
          command: "echo 'Processing {{ item }}'"
```

### Worker Management

- Dynamic worker allocation
- Resource limiting
- Progress monitoring

## State Management

### Persistence

- Workflow state tracking
- Step output storage
- Variable persistence

### Resume Capability

- Restart from failures
- Skip completed steps
- State validation

## Template System

### Variable Substitution

```yaml
steps:
  - name: create_file
    task: write_file
    params:
      content: "Hello, {{ user }}!"
      file_path: "{{ output_dir }}/greeting.txt"
```

### Built-in Functions

- Date/time manipulation
- String operations
- Math functions
- Path handling

### Custom Functions

Register custom template functions:

```python
from yaml_workflow.template import register_function

@register_function
def custom_format(value, format_spec):
    return format(value, format_spec)
```

## Error Handling

### Retry Mechanism

```yaml
steps:
  - name: api_call
    task: shell
    retry:
      max_attempts: 3
      delay: 5
      backoff: 2
    params:
      command: "curl http://api.example.com"
```

### Error Actions

- Skip failed steps
- Retry with backoff
- Custom error handlers
- Notification integration

## Logging and Monitoring

### Log Levels

- DEBUG: Detailed debugging
- INFO: General information
- WARNING: Potential issues
- ERROR: Error conditions

### Output Formats

- Text logs
- JSON structured
- Custom formatters

### Monitoring

- Progress tracking
- Resource usage
- Performance metrics
- Status reporting

## Security Features

### Environment Isolation

- Workspace containment
- Environment variable control
- Resource limitations

### Credential Management

- Secure variable handling
- Environment variable integration
- Token management

## Development Tools

### CLI Tools

- Workflow validation
- State inspection
- Log analysis
- Performance profiling

### Testing Support

- Mock tasks
- State simulation
- Error injection
- Performance testing

## Best Practices

1. **Workflow Design**
   - Modular steps
   - Clear dependencies
   - Error handling
   - Progress tracking

2. **Resource Management**
   - Worker pools
   - Memory usage
   - File handles
   - Network connections

3. **Error Handling**
   - Retry strategies
   - Fallback options
   - Clean up
   - Logging

4. **Security**
   - Credential protection
   - Input validation
   - Resource limits
   - Audit logging 