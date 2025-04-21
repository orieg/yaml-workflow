# Python Tasks

YAML Workflow provides several tasks for integrating Python logic into your workflows. These tasks allow you to execute Python code snippets, call functions from modules, run external scripts, or execute Python modules directly.

All Python tasks provide access to the standard workflow context namespaces (`args`, `env`, `steps`, `batch`) within their execution environment.

## `python_code`

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

## `python_function`

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

## `python_script`

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

## `python_module`

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