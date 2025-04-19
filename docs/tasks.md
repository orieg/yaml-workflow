# Task Types

YAML Workflow supports several built-in task types for different use cases. Each task type has specific inputs and capabilities.

## Task Configuration

All tasks use a standardized configuration format and share common features:

```yaml
name: task_name        # Name of the task (required)
task: task_type       # Type of task to execute (required)
inputs:               # Task-specific inputs (required)
  input1: value1
  input2: value2
retry:                # Optional retry configuration
  max_attempts: 3     # Number of retry attempts
  delay: 5           # Delay between retries in seconds
```

### Namespace Support

Tasks have access to variables in different namespaces through the TaskConfig interface:

- `args`: Command-line arguments and workflow parameters
- `env`: Environment variables
- `steps`: Results from previous steps
- `batch`: Batch processing context (in batch tasks)
- `current`: Information about the current task

Example using namespaces:
```yaml
name: example_step
task: shell
inputs:
  command: |
    echo "Arguments: {{ args.input }}"
    echo "Environment: {{ env.PATH }}"
    echo "Previous step: {{ steps.prev_step.result }}"
    echo "Current task: {{ steps.current.name }}"
  working_dir: "{{ env.WORKSPACE }}"
```

### Error Handling

Tasks use standardized error handling through TaskConfig:

- `TaskExecutionError`: Raised for task execution failures
  - Contains step name and original error
  - Provides execution context
  - Includes available variables
- `TemplateError`: Raised for template resolution failures
  - Shows undefined variable details
  - Lists available variables by namespace
  - Provides template context

Example error messages:
```
TaskExecutionError in step 'read_file': Failed to read file '/path/to/missing.txt'
  Step: read_file
  Original error: [Errno 2] No such file or directory
  Available variables:
    args: input_file, encoding
    env: WORKSPACE, PATH
    steps: previous_step

TemplateError in step 'process_data': Failed to resolve template
  Template: {{ undefined_var }}
  Error: Variable 'undefined_var' is undefined
  Available variables:
    args: input, output
    env: API_KEY
    steps: previous_step.result
```

## Basic Tasks

These are simple utility tasks for common operations:

```yaml
# Echo a message
- name: echo_step
  task: echo
  inputs:
    message: "Hello, {{ args.name }}!"

# Add two numbers
- name: add_numbers_step
  task: add_numbers
  inputs:
    a: "{{ args.first }}"
    b: "{{ args.second }}"

# Join strings
- name: join_strings_step
  task: join_strings
  inputs:
    strings: ["{{ args.greeting }}", "{{ args.name }}"]
    separator: ", "

# Create a greeting using a template
- name: greeting_step
  task: create_greeting
  inputs:
    template: "Welcome, {{ args.name }}!"
    name: "{{ args.user }}"

# Deliberately fail a task (useful for testing)
- name: fail_step
  task: fail
  inputs:
    message: "Custom failure message"
```

## File Tasks

Tasks for file operations with support for various formats:

```yaml
# Write a file
- name: write_file_step
  task: write_file
  inputs:
    file_path: "{{ args.output_dir }}/output.txt"
    content: "{{ steps.previous.result.content }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Write JSON file
- name: write_json_step
  task: write_json
  inputs:
    file_path: "data.json"
    data: 
      key: "{{ args.value }}"
      timestamp: "{{ env.TIMESTAMP }}"
    indent: 2  # Optional, defaults to 2

# Write YAML file
- name: write_yaml_step
  task: write_yaml
  inputs:
    file_path: "config.yaml"
    data: 
      settings: "{{ steps.load_settings.result }}"

# Read a file
- name: read_file_step
  task: read_file
  inputs:
    file_path: "{{ args.input_file }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Read JSON file
- name: read_json_step
  task: read_json
  inputs:
    file_path: "{{ env.CONFIG_PATH }}"

# Read YAML file
- name: read_yaml_step
  task: read_yaml
  inputs:
    file_path: "{{ args.config_file }}"

# Append to a file
- name: append_file_step
  task: append_file
  inputs:
    file_path: "{{ env.LOG_FILE }}"
    content: "{{ steps.process.result }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Copy a file
- name: copy_file_step
  task: copy_file
  inputs:
    source: "{{ steps.download.result.output_file }}"
    destination: "{{ env.BACKUP_DIR }}/{{ args.filename }}"

# Move a file
- name: move_file_step
  task: move_file
  inputs:
    source: "{{ steps.process.result.temp_file }}"
    destination: "{{ args.output_dir }}/final.txt"

# Delete a file
- name: delete_file_step
  task: delete_file
  inputs:
    file_path: "{{ steps.process.result.temp_file }}"
```

## Template Tasks

Tasks for rendering templates using Jinja2. For detailed information about templating capabilities, syntax, and best practices, see the [Templating Guide](guide/templating.md).

```yaml
- name: render_template_step
  task: template
  inputs:
    template: |
      Hello, {{ args.name }}!
      Environment: {{ env.ENVIRONMENT }}
      Previous Result: {{ steps.process.result }}
    output: "{{ args.output_file }}"
```

## Shell Tasks

Tasks for executing shell commands with full namespace support:

```yaml
- name: shell_step
  task: shell
  inputs:
    command: |
      echo "Processing {{ batch.item }}"
      export DEBUG="{{ env.DEBUG }}"
      ./process.sh "{{ args.input_file }}"
    working_dir: "{{ env.WORKSPACE }}/{{ args.project }}"  # Optional
    env:  # Optional environment variables
      API_KEY: "{{ env.API_KEY }}"
      DEBUG: "{{ args.verbose }}"
    timeout: 300  # Optional timeout in seconds
```

## Python Tasks

Tasks for executing Python code with full namespace access:

```yaml
name: python_step
task: python
inputs:
  code: |
    # Access variables through namespaces
    input_data = args['data']
    api_key = env['API_KEY']
    prev_result = steps['previous']['result']
    
    # In batch tasks, access batch context
    if 'batch' in locals():
        item = batch['item']
        index = batch['index']
        total = batch['total']
    
    # Process data
    result = process_data(input_data, api_key)
    
    # Return value becomes available in steps namespace
    result = {
        'processed': result,
        'timestamp': datetime.now().isoformat()
    }
```

## Batch Tasks

Tasks for processing items in batches with proper error handling and state tracking:

```yaml
name: batch_step
task: batch
inputs:
  items: "{{ args.items }}"  # List of items to process
  chunk_size: 10            # Optional, process 10 items at a time
  max_workers: 4            # Optional, number of parallel workers
  retry:                    # Optional retry configuration
    max_attempts: 3         # Retry failed items up to 3 times
    delay: 5               # Wait 5 seconds between retries
  task:                    # Task configuration for processing each item
    task: shell
    inputs:
      command: |
        echo "Processing {{ batch.item }}"
        echo "Progress: {{ batch.index + 1 }}/{{ batch.total }}"
        echo "Task: {{ batch.name }}"
        ./process.sh "{{ batch.item }}"
      working_dir: "{{ env.WORKSPACE }}"
      timeout: 300        # Optional timeout in seconds

# Access batch results
name: check_results
task: python
inputs:
  code: |
    batch_results = steps['batch_step']['results']
    
    # Analyze results
    completed = [r for r in batch_results if 'result' in r]
    failed = [r for r in batch_results if 'error' in r]
    
    result = {
        'total': len(batch_results),
        'completed': len(completed),
        'failed': len(failed),
        'success_rate': len(completed) / len(batch_results) * 100
    }
```

## Custom Tasks

Create custom tasks using the TaskConfig interface:

```python
from yaml_workflow.tasks import register_task, TaskConfig
from yaml_workflow.exceptions import TaskExecutionError

@register_task("my_custom_task")
def my_custom_task_handler(config: TaskConfig) -> Dict[str, Any]:
    """
    Custom task implementation using TaskConfig.
    
    Args:
        config: TaskConfig object containing:
               - name: Task name
               - type: Task type
               - inputs: Task inputs
               - workspace: Workspace path
               - _context: Variable context
    
    Returns:
        Dict containing:
        - result: Task result
        - task_name: Name of the task
        - task_type: Type of task
        - available_variables: Variables accessible to the task
        
    Raises:
        TaskExecutionError: If task execution fails
    """
    try:
        # Process inputs with template resolution
        processed = config.process_inputs()
        
        # Access variables from different namespaces
        input_value = config.get_variable('value', namespace='args')
        env_var = config.get_variable('API_KEY', namespace='env')
        
        # Access batch context if available
        batch_ctx = config.get_variable('item', namespace='batch')
        
        # Perform task logic
        result = process_data(input_value, env_var)
        
        return {
            "result": result,
            "task_name": config.name,
            "task_type": config.type,
            "available_variables": config.get_available_variables()
        }
    except Exception as e:
        raise TaskExecutionError(
            message=f"Custom task failed: {str(e)}",
            step_name=config.name,
            original_error=e
        )
```

Use custom tasks in workflows:
```yaml
name: custom_step
task: my_custom_task
inputs:
  value: "{{ args.input }}"
  api_key: "{{ env.API_KEY }}"
```

## Task Results and State

All tasks maintain consistent result format and state tracking through TaskConfig:

```yaml
# First task execution
name: first_step
task: shell
inputs:
  command: "echo 'Hello'"

# Access results through steps namespace
name: second_step
task: shell
inputs:
  command: |
    # Access previous task results
    echo "Previous output: {{ steps.first_step.stdout }}"
    echo "Previous exit code: {{ steps.first_step.exit_code }}"
    
    # Access current task info
    echo "Current task: {{ steps.current.name }}"
    echo "Task type: {{ steps.current.type }}"
    echo "Available variables: {{ steps.current.available_variables | join(', ') }}"
```

For more detailed information about specific features:
- [Templating Guide](guide/templating.md) - Template syntax and features
- [Batch Processing Guide](guide/batch-tasks.md) - Detailed batch processing
- [Error Handling](guide/error-handling.md) - Error handling patterns 