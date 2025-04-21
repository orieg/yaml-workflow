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

Tasks for file operations with support for various formats.

**Path Resolution:** All relative paths specified in task inputs (`file_path`, `file`, `source`, `destination`) are resolved relative to the root of the workflow's workspace directory. To interact with files inside the standard `output/` directory, explicitly include the `output/` prefix in the path string (e.g., `output/my_file.txt`).

```yaml
# Write a file
- name: write_file_step
  task: write_file
  inputs:
    # Explicitly specify output/ for files in the output directory
    file: "output/{{ args.output_dir }}/output.txt"
    content: "{{ steps.previous.result.content }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Write JSON file
- name: write_json_step
  task: write_json
  inputs:
    file: "output/data.json" # Added output/ prefix
    data: 
      key: "{{ args.value }}"
      timestamp: "{{ env.TIMESTAMP }}"
    indent: 2  # Optional, defaults to 2

# Write YAML file
- name: write_yaml_step
  task: write_yaml
  inputs:
    file: "output/config.yaml" # Added output/ prefix
    data: 
      settings: "{{ steps.load_settings.result }}"

# Read a file
- name: read_file_step
  task: read_file
  inputs:
    # Assuming input file might be outside output/
    file: "{{ args.input_file }}"
    # If reading from output/, use: file: "output/{{ args.input_file }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Read JSON file
- name: read_json_step
  task: read_json
  inputs:
    # Assuming config might be at root or elsewhere
    file: "{{ env.CONFIG_PATH }}"
    # If reading from output/, use: file: "output/{{ env.CONFIG_PATH }}"

# Read YAML file
- name: read_yaml_step
  task: read_yaml
  inputs:
    # Assuming config might be at root or elsewhere
    file: "{{ args.config_file }}"
    # If reading from output/, use: file: "output/{{ args.config_file }}"

# Append to a file (e.g., a log file in the logs/ directory)
- name: append_file_step
  task: append_file
  inputs:
    file: "logs/workflow.log" # Example: Log file outside output/
    # If appending to output/, use: file: "output/{{ env.LOG_FILE }}"
    content: "{{ steps.process.result }}"
    encoding: "utf-8"  # Optional, defaults to utf-8

# Copy a file (e.g., from output/ to a backup dir)
- name: copy_file_step
  task: copy_file
  inputs:
    source: "output/{{ steps.download.result.output_file }}" # Added output/ prefix to source
    # Assuming backup dir is at workspace root
    destination: "{{ env.BACKUP_DIR }}/{{ args.filename }}"

# Move a file (e.g., from a temp location in output/ to final location in output/)
- name: move_file_step
  task: move_file
  inputs:
    source: "output/{{ steps.process.result.temp_file }}" # Added output/ prefix to source
    destination: "output/{{ args.output_dir }}/final.txt" # Added output/ prefix to destination

# Delete a file (e.g., a temp file in output/)
- name: delete_file_step
  task: delete_file
  inputs:
    file: "output/{{ steps.process.result.temp_file }}" # Added output/ prefix
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

YAML Workflow provides several tasks for integrating Python logic into your workflows. These tasks allow you to execute Python code snippets, call functions from modules, run external scripts, or execute Python modules directly.

All Python tasks provide access to the standard workflow context namespaces (`args`, `env`, `steps`, `batch`) within their execution environment.

### `python_code`

Executes a multi-line string containing Python code.

**Inputs:**

*   `code` (str, required): A string containing the Python code to execute.
*   `result_variable` (str, optional): The name of a variable within the executed code whose value should be returned as the task's result. If omitted, the task will look for a variable named `result` and return its value. If neither `result_variable` is specified nor a `result` variable is found, the task returns `None`.

**Execution Context:**

The code is executed with access to the following variables in its local scope:
*   `config`: The `TaskConfig` object for the step.
*   `context`: The full workflow context dictionary.
*   `args`, `env`, `steps`, `batch`: Direct access to the main context namespaces.
*   Any inputs defined directly under the `inputs:` key for the task (after template rendering).

**Result:**

The task returns a dictionary `{"result": value}`, where `value` is the value of the variable specified by `result_variable` or the variable named `result` by default.

**Example:**

```yaml
- name: calculate_sum
  task: python_code
  inputs:
    # Inputs provided here are available directly in the code
    x: "{{ args.num1 }}"
    y: "{{ args.num2 }}"
    code: |
      # x and y are directly available from inputs
      sum_val = x + y 
      
      # Set the 'result' variable for implicit return
      result = sum_val 

- name: process_data
  task: python_code
  inputs:
    raw_data: "{{ steps.load_data.result }}"
    # Explicitly specify the variable to return
    result_variable: processed_data 
    code: |
      # raw_data is available from inputs
      data = raw_data * 10
      # ... more processing ...
      
      # Assign to the variable named in result_variable
      processed_data = data 
```

### `python_function`

Calls a specified Python function within a given module.

**Inputs:**

*   `module` (str, required): The dot-separated path to the Python module (e.g., `my_package.my_module`). The module must be importable in the environment where the workflow runs.
*   `function` (str, required): The name of the function to call within the module.
*   `args` (list, optional): A list of positional arguments to pass to the function. Templates can be used within the list items.
*   `kwargs` (dict, optional): A dictionary of keyword arguments to pass to the function. Templates can be used within the dictionary values.

**Result:**

The task returns a dictionary `{"result": value}`, where `value` is the return value of the called Python function.
Supports both synchronous and asynchronous (`async def`) functions.

**Example:**

Assuming a module `utils.processors` with a function `def process_user(user_id: int, active_only: bool = True) -> dict:`:

```yaml
- name: process_single_user
  task: python_function
  inputs:
    module: utils.processors
    function: process_user
    args: # Positional arguments
      - "{{ args.user_id }}"
    kwargs: # Keyword arguments
      active_only: false
```

### `python_script`

Executes an external Python script file.

**Inputs:**

*   `script_path` (str, required): The path to the Python script. 
    *   If absolute, it's used directly.
    *   If relative, it's resolved first relative to the workflow workspace directory, then searched for in the system's `PATH`.
*   `args` (list, optional): A list of string arguments to pass to the script command line. Templates can be used.
*   `cwd` (str, optional): The working directory from which to run the script. Defaults to the workflow workspace. Templates can be used.
*   `timeout` (float, optional): Maximum execution time in seconds. Raises `TimeoutError` if exceeded.
*   `check` (bool, optional): If `true` (default), raises a `TaskExecutionError` if the script exits with a non-zero return code.

**Result:**

The task returns a dictionary `{"result": value}` where `value` is a dictionary containing:
*   `returncode` (int): The exit code of the script.
*   `stdout` (str): The standard output captured from the script.
*   `stderr` (str): The standard error captured from the script.

**Example:**

```yaml
- name: run_analysis_script
  task: python_script
  inputs:
    script_path: scripts/analyze_data.py # Relative to workspace
    args:
      - "--input"
      - "{{ steps.prepare_data.result.output_file }}"
      - "--threshold"
      - "{{ args.threshold | default(0.95) }}"
    cwd: "{{ workspace }}/analysis_module" # Optional working directory
    timeout: 600 # 10 minutes
    check: true # Fail workflow if script fails
```

### `python_module`

Executes a Python module using `python -m <module>`.

**Inputs:**

*   `module` (str, required): The name of the module to execute (e.g., `my_tool.cli`).
*   `args` (list, optional): A list of string arguments to pass to the module command line. Templates can be used.
*   `cwd` (str, optional): The working directory from which to run the module. Defaults to the workflow workspace. Templates can be used.
*   `timeout` (float, optional): Maximum execution time in seconds. Raises `TimeoutError` if exceeded.
*   `check` (bool, optional): If `true` (default), raises a `TaskExecutionError` if the module exits with a non-zero return code.

**Execution Environment:** The workflow's workspace directory is automatically added to the `PYTHONPATH` environment variable for the execution, allowing the module to import other local Python files or packages within the workspace.

**Result:**

The task returns a dictionary `{"result": value}` where `value` is a dictionary containing:
*   `returncode` (int): The exit code of the module process.
*   `stdout` (str): The standard output captured from the process.
*   `stderr` (str): The standard error captured from the process.

**Example:**

```yaml
- name: run_cli_tool
  task: python_module
  inputs:
    module: my_project.cli_tool
    args:
      - "process"
      - "--input-file"
      - "{{ steps.download.result.file_path }}"
      - "--verbose"
    check: true
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

# Access batch results
name: check_results
task: python_code
inputs:
  code: |
    # Assuming the batch step was named 'batch_step'
    batch_step_result = steps['batch_step']
    # Access the lists directly from the batch task's result
    processed_items = batch_step_result.result.get('processed', [])
    failed_items = batch_step_result.result.get('failed', [])
    all_results = batch_step_result.result.get('results', []) # List of results from sub-tasks
    stats = batch_step_result.result.get('stats', {})
    
    # Example: Log summary
    print(f"Total items: {stats.get('total', 0)}")
    print(f"Successfully processed: {len(processed_items)}")
    print(f"Failed: {len(failed_items)}")
    print(f"Success rate: {stats.get('success_rate', 0):.2f}%")
    
    # Set a final result for this step
    result = {
        'total': stats.get('total', 0),
        'completed': len(processed_items),
        'failed': len(failed_items),
        'success_rate': stats.get('success_rate', 0)
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