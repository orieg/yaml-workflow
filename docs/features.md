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
  
env:
  WORKSPACE: /data/processing
  API_KEY: "{{ args.api_key }}"

steps:
  read_data:
    name: read_data
    task: read_file
    inputs:
      file_path: "{{ args.input_file }}"
      encoding: utf-8

  transform:
    name: transform
    task: python
    inputs:
      code: |
        # Access data through namespaces
        data = steps['read_data']['result']
        workspace = env['WORKSPACE']
        
        # Process data
        result = transform_data(data)
```

### Namespace Support

Access variables through isolated namespaces:

- `args`: Command-line arguments and workflow parameters
- `env`: Environment variables
- `steps`: Results from previous steps
- `batch`: Batch processing context (in batch tasks)
- `current`: Information about the current task

Example:
```yaml
steps:
  process_data:
    name: process_data
    task: shell
    inputs:
      command: |
        # Access from different namespaces
        echo "Input: {{ args.input_file }}"
        echo "API Key: {{ env.API_KEY }}"
        echo "Previous: {{ steps.previous.result }}"
        echo "Current: {{ steps.current.name }}"
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
    task: python
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