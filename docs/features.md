# Features

YAML Workflow provides a rich set of features for building and executing workflows. This document outlines the key features and their usage.

## Core Features

### YAML-Driven Configuration

Define workflows using simple YAML syntax with standardized task configuration:

```yaml
name: data_processing
description: Process and transform data files
version: "1.0.0"

args:
  input_file:
    type: string
    description: Input file to process
    default: input.csv
  api_key_param: 
    type: string
    description: API key, can be passed via CLI
    required: false

env:
  WORKSPACE: /data/processing
  # Env var set from a param (accessed via args namespace)
  API_KEY: "{{ args.api_key_param }}"

steps:
  read_data:
    name: read_data
    task: read_file
    inputs:
      # Accessing param via args namespace
      file_path: "{{ args.input_file }}"
      encoding: utf-8

  transform:
    name: transform
    task: python_code
    inputs:
      code: |
        # Access data through namespaces
        data = context['steps']['read_data']['result']
        workspace = context['env']['WORKSPACE']
        # Access param value via context dictionary if needed inside Python
        api_key = context['args']['api_key_param'] 
        # Process data
        result = transform_data(data, api_key)
```

### Namespace Support

Access variables through isolated namespaces:

- `params`: (Definition Block) The top-level `params:` block in your workflow YAML is used to *define* the expected parameters, their types, descriptions, defaults, and whether they are required.
- `args`: (Runtime Namespace) Holds the *resolved runtime values* of workflow parameters for use in tasks and templates. This namespace contains values from the `params:` block defaults, potentially overridden by arguments passed via the command line (`name=value` format). Access via `{{ args.PARAM_NAME }}`.
- `env`: Environment variables (`{{ env.VAR_NAME }}`).
- `steps`: Results from previous steps (`{{ steps.STEP_NAME.result }}` or `{{ steps.STEP_NAME.result.KEY }}`).
- `batch`: Batch processing context (`{{ batch.item }}`, `{{ batch.index }}`, etc.).
- `current`: Information about the current task (`{{ current.name }}`).
- `workflow`: Workflow-level information (`{{ workflow.workspace }}`, `{{ workflow.run_id }}`).

Example:
```yaml
# Workflow Definition (my_workflow.yaml)
name: cli_example
params:
  input_file_param: 
    description: Input file defined in params
    default: default.csv
  debug_level:
    description: Debug level defined in params
    default: info

steps:
  process_data:
    name: process_data
    task: shell
    inputs:
      command: |
        # Example Command Line:
        # python -m yaml_workflow run my_workflow.yaml input_file_param=override.csv extra_cli_arg=cli_value
        
        # Access resolved values via 'args' namespace:
        echo "Input File: {{ args.input_file_param }}"  # Will output: override.csv
        echo "Debug Level: {{ args.debug_level }}"     # Will output: info (default, not overridden)
        echo "Extra CLI Arg: {{ args.extra_cli_arg }}" # Will output: cli_value
        echo "API Key (env): {{ env.API_KEY }}"
        echo "Previous Step Result: {{ steps.previous.result }}" # Example only
        echo "Current Step Name: {{ current.name }}"
```

### Error Handling

Standardized error handling through TaskConfig:

```yaml
steps:
  api_call:
    name: api_call
    task: shell
    inputs:
      command: "curl {{ env.API_URL }}"
    retry:
      max_attempts: 3
      delay: 5
      backoff: 2
```

Error types:
- `TaskExecutionError`: Task execution failures
  - Contains step name and original error
  - Provides execution context
  - Lists available variables
- `TemplateError`: Template resolution failures
  - Shows undefined variable details
  - Lists available variables by namespace
  - Provides template context

## Task System

### Built-in Tasks

All tasks use the standardized TaskConfig interface:

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

Create tasks using the TaskConfig interface:

```python
from yaml_workflow.tasks import register_task, TaskConfig
from yaml_workflow.exceptions import TaskExecutionError

@register_task("custom_task")
def custom_task_handler(config: TaskConfig) -> Dict[str, Any]:
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
    """
    try:
        # Process inputs with template resolution
        processed = config.process_inputs()
        
        # Access variables from different namespaces
        input_value = config.get_variable('value', namespace='args')
        env_var = config.get_variable('API_KEY', namespace='env')
        
        # Process data
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

## Batch Processing

Process items in parallel with proper error handling and state tracking:

```yaml
steps:
  process_files:
    name: process_files
    task: batch
    inputs:
      items: "{{ args.files }}"
      chunk_size: 10          # Process 10 items at a time
      max_workers: 4          # Use 4 parallel workers
      retry:
        max_attempts: 3       # Retry failed items up to 3 times
        delay: 5              # Wait 5 seconds between retries
      task:
        task: shell
        inputs:
          command: |
            echo "Processing {{ batch.item }}"
            echo "Progress: {{ batch.index + 1 }}/{{ batch.total }}"
            echo "Task: {{ batch.name }}"
            ./process.sh "{{ batch.item }}"
          working_dir: "{{ env.WORKSPACE }}"
          timeout: 300        # Timeout after 5 minutes

  check_results:
    name: check_results
    task: python_code
    inputs:
      code: |
        results = steps['process_files']['results']
        
        # Analyze results
        completed = [r for r in results if 'result' in r]
        failed = [r for r in results if 'error' in r]
        
        result = {
            'total': len(results),
            'completed': len(completed),
            'failed': len(failed),
            'success_rate': len(completed) / len(results) * 100,
            'failed_items': [r['item'] for r in failed]
        }
```

### Batch Features

1. **Chunk Processing**
   - Configurable chunk sizes
   - Memory optimization
   - Progress tracking

2. **Parallel Execution**
   - Dynamic worker pools
   - Resource management
   - Timeout handling

3. **Error Handling**
   - Per-item retry
   - Batch-level retry
   - Detailed error reporting

4. **State Tracking**
   - Progress monitoring
   - Result aggregation
   - Failure analysis

## Template System

### Variable Resolution

Access variables through namespaces:

```yaml
steps:
  create_file:
    name: create_file
    task: write_file
    inputs:
      content: |
        User: {{ args.user }}
        Environment: {{ env.ENV_NAME }}
        Previous Result: {{ steps.previous.result }}
        Current Task: {{ steps.current.name }}
      file_path: "{{ env.OUTPUT_DIR }}/report.txt"
```

### Built-in Functions

Template functions with namespace awareness:
- Date/time manipulation: `now()`, `format_date()`
- String operations: `trim()`, `upper()`, `lower()`
- Math functions: `sum()`, `min()`, `max()`
- Path handling: `join_paths()`, `basename()`

### Custom Functions

Register template functions with namespace support:

```python
from yaml_workflow.template import register_function

@register_function
def format_with_context(value: str, context: Dict[str, Any]) -> str:
    """Format string with context awareness."""
    return value.format(**context)
```

## State Management

### Task Results

All tasks maintain consistent result format:
- `result`: Task output
- `task_name`: Name of the task
- `task_type`: Type of task
- `available_variables`: Variables accessible to the task

Access results through the steps namespace:
```yaml
steps:
  first_step:
    name: first_step
    task: shell
    inputs:
      command: "echo 'Hello'"

  second_step:
    name: second_step
    task: shell
    inputs:
      command: |
        # Access previous results
        echo "Output: {{ steps.first_step.stdout }}"
        echo "Exit Code: {{ steps.first_step.exit_code }}"
        
        # Access current task
        echo "Task: {{ steps.current.name }}"
        echo "Type: {{ steps.current.type }}"
```

### Error Recovery

Standardized error handling and recovery:
- Automatic retries with configurable backoff
- Detailed error context for debugging
- State preservation during failures
- Resume capability from last successful point

## Best Practices

1. **Task Design**
   - Use TaskConfig interface
   - Implement proper error handling
   - Maintain namespace isolation
   - Return standardized results

2. **Error Handling**
   - Use TaskExecutionError for task failures
   - Include context in error messages
   - Implement retry mechanisms
   - Clean up resources on failure

3. **Batch Processing**
   - Choose appropriate chunk sizes
   - Monitor resource usage
   - Handle errors gracefully
   - Track progress effectively

4. **Template Usage**
   - Use proper namespace access
   - Validate variable existence
   - Handle undefined variables
   - Document available variables

For more detailed information:
- [Task Types](tasks.md)
- [Templating Guide](guide/templating.md)
- [Batch Processing Guide](guide/batch-tasks.md)
- [Error Handling Guide](guide/error-handling.md)

## Variable Templating

Use Jinja2 templates for dynamic values:

```yaml
steps:
  - name: download_data
    task: shell
    inputs:
      command: "curl -o {{ args.output_dir }}/data.zip {{ env.DATA_URL }}"
  
  - name: process_downloaded_data
    task: python_code # Use python_code for inline Python
    inputs:
      code: |
        input_file = f\"{{ args.output_dir }}/data.zip\"
        result = process(input_file)
``` 