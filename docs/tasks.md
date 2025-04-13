# Task Types

YAML Workflow supports several built-in task types for different use cases.

## Template Tasks
```yaml
- name: render_template
  task: template
  template: |
    Hello, {{ name }}!
    This is a template with {{ variable }} substitution.
  output: output.txt
```

## Shell Tasks
```yaml
- name: run_command
  task: shell
  command: "echo 'Processing {{ item }}'"
```

## File Tasks
```yaml
- name: write_file
  task: write_file
  inputs:
    file_path: output.txt
    content: "File content"

- name: read_file
  task: read_file
  inputs:
    file_path: input.txt
```

## Batch Tasks
```yaml
- name: process_batch
  task: batch
  iterate_over: ["item1", "item2", "item3"]
  batch_size: 2
  processing_task:
    task: shell
    command: "echo 'Processing {{ item }}'"
```

## Python Tasks
```yaml
- name: python_task
  task: python
  function: process_data
  inputs:
    data: ["item1", "item2"]
    operation: "transform"
```

## Custom Tasks

You can create custom tasks by registering them with the task registry:

```python
from yaml_workflow.tasks import register_task

@register_task("my_custom_task")
def my_custom_task_handler(step, context, workspace):
    inputs = step.get("inputs", {})
    # Process inputs and perform task
    return {"result": "Task completed"}
```

Then use them in your workflow:
```yaml
- name: custom_step
  task: my_custom_task
  inputs:
    param1: value1
    param2: value2
``` 