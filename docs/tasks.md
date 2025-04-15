# Task Types

YAML Workflow supports several built-in task types for different use cases. Each task type has specific parameters and capabilities.

## Basic Tasks

These are simple utility tasks for common operations:

```yaml
# Echo a message
- name: echo_step
  task: echo
  params:
    message: "Hello, World!"

# Add two numbers
- name: add_numbers_step
  task: add_numbers
  params:
    a: 5
    b: 3

# Join strings
- name: join_strings_step
  task: join_strings
  params:
    strings: ["Hello", "World"]
    separator: ", "

# Create a greeting using a template
- name: greeting_step
  task: create_greeting
  params:
    template: "Welcome, {{ name }}!"
    name: "Alice"

# Deliberately fail a task (useful for testing)
- name: fail_step
  task: fail
  params:
    message: "Custom failure message"
```

## File Tasks

Tasks for file operations with support for various formats:

```yaml
# Write a file
- name: write_file_step
  task: write_file
  params:
    file_path: output.txt
    content: "File content"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Write JSON file
- name: write_json_step
  task: write_json
  params:
    file_path: data.json
    data: {"key": "value"}
    indent: 2  # Optional, defaults to 2

# Write YAML file
- name: write_yaml_step
  task: write_yaml
  params:
    file_path: config.yaml
    data: {"key": "value"}

# Read a file
- name: read_file_step
  task: read_file
  params:
    file_path: input.txt
    encoding: "utf-8"  # Optional, defaults to utf-8

# Read JSON file
- name: read_json_step
  task: read_json
  params:
    file_path: data.json

# Read YAML file
- name: read_yaml_step
  task: read_yaml
  params:
    file_path: config.yaml

# Append to a file
- name: append_file_step
  task: append_file
  params:
    file_path: log.txt
    content: "New log entry"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Copy a file
- name: copy_file_step
  task: copy_file
  params:
    source: source.txt
    destination: backup.txt

# Move a file
- name: move_file_step
  task: move_file
  params:
    source: old_location.txt
    destination: new_location.txt

# Delete a file
- name: delete_file_step
  task: delete_file
  params:
    file_path: unnecessary.txt
```

## Template Tasks

Tasks for rendering templates using Jinja2. For detailed information about templating capabilities, syntax, and best practices, see the [Templating Guide](guide/templating.md).

```yaml
- name: render_template_step
  task: template
  params:
    template: |
      Hello, {{ name }}!
      This is a template with {{ variable }} substitution.
    output: output.txt
    variables:
      name: "Alice"
      variable: "dynamic"
```

## Shell Tasks

Tasks for executing shell commands:

```yaml
- name: shell_step
  task: shell
  params:
    command: "echo 'Processing {{ item }}'"
    working_dir: "/path/to/dir"  # Optional
    env:  # Optional environment variables
      KEY: "value"
    shell: "/bin/bash"  # Optional, defaults to system shell
```

## Python Tasks

Tasks for executing Python code:

```yaml
- name: python_step
  task: python
  params:
    function: "module.submodule.function_name"
    params:  # Parameters passed to the function
      param1: "value1"
      param2: "value2"
    import_from: "path/to/python/file.py"  # Optional
```

## Batch Tasks

Tasks for processing items in batches:

```yaml
- name: batch_step
  task: batch
  params:
    iterate_over: ["item1", "item2", "item3"]
    batch_size: 2  # Optional, defaults to processing all items at once
    parallel: true  # Optional, defaults to false
    max_workers: 4  # Optional, only used when parallel is true
    processing_task:  # Task to execute for each item
      task: shell
      params:
        command: "echo 'Processing {{ item }}'"
```

## Custom Tasks

You can create custom tasks by registering them with the task registry:

```python
from yaml_workflow.tasks import register_task

@register_task("my_custom_task")
def my_custom_task_handler(step, context, workspace):
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

Then use them in your workflow:
```yaml
- name: custom_step
  task: my_custom_task
  params:
    param1: value1
    param2: value2
```

## Task Context and Variables

All tasks have access to:
- Template variable substitution using Jinja2 syntax
- Workspace path resolution for file operations
- Error handling and logging
- Task retry mechanisms (when configured)
- Previous task outputs via context

Example using context and variables:
```yaml
- name: template_with_context
  task: template
  params:
    template: |
      Previous task output: {{ previous_task.output }}
      Current workspace: {{ workspace }}
      Environment variable: {{ env.MY_VAR }}
    variables:
      custom_var: "value"
``` 