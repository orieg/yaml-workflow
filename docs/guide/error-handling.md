# Error Handling Patterns Guide

The YAML Workflow engine provides robust mechanisms for handling errors that occur during task execution within a workflow. This guide explains how to configure error handling at the step level using the `on_error` block.

## The `on_error` Block

Each step in your workflow YAML can optionally include an `on_error` block to define how failures in that specific step should be handled. If a task function raises an exception (or if the centralized `handle_task_error` utility is used within a task and re-raises), the engine checks the `on_error` configuration for the failed step.

```yaml
steps:
  - name: my_potentially_failing_step
    task: some_task
    inputs: { ... }
    on_error:  # <--- Error handling configuration for this step
      action: fail # Options: fail, continue, retry
      message: "Custom error message: {{ error }}" # Optional message template
      retry: # Optional retry configuration
        max_attempts: 3
        delay: 5 # seconds
      next: error_handler_step # Optional target step for error flow
```

## Error Handling Actions (`on_error.action`)

The `action` key determines the primary behavior when an error occurs.

1.  **`fail` (Default)**
    - If `action` is set to `fail`, or if the `on_error` block or `action` key is omitted entirely, the workflow halts immediately upon step failure.
    - The engine marks the workflow state as `failed` and records the failed step and error message.
    - A `WorkflowError` is raised, stopping further execution.
    ```yaml
    steps:
      - name: critical_step
        task: important_operation
        on_error:
          action: fail # Halts the workflow immediately
          message: "Critical step failed: {{ error.error }} - See logs."
    ```

2.  **`continue`**
    - If `action` is set to `continue`, the engine logs the error, marks the specific step as `failed` in the state, but allows the workflow to proceed to the next step.
    - The failed step's output will not be available in the context for subsequent steps.
    - The overall workflow can still complete successfully if subsequent steps don't depend critically on the failed one.
    ```yaml
    steps:
      - name: optional_cleanup
        task: cleanup_temp_files
        on_error:
          action: continue # Logs error but continues workflow
          message: "Optional cleanup failed: {{ error.error }}. Continuing..."
    ```

3.  **`retry`**
    - If `action` is set to `retry`, the engine will attempt to re-execute the failed step based on the configuration provided in the `on_error.retry` block (see below).
    - This action is often used implicitly when the `retry` block is present, but explicitly setting `action: retry` can improve clarity.
    - If all retry attempts fail, the workflow will then typically halt (like `fail`), unless combined with a `next` target.
    ```yaml
    steps:
      - name: flaky_api_call
        task: call_external_api
        retry: # Implicitly uses retry action
          max_attempts: 5
          delay: 10
        on_error:
          # action: retry # Optional explicit action
          message: "API call failed after retries: {{ error.error }}"
          # If retries fail, it implicitly behaves like 'fail' here
          # unless 'next' is specified.
    ```

## Custom Error Messages (`on_error.message`)

You can provide a custom error message template using the `message` key. This message is logged by the engine and stored in the workflow state if the step ultimately fails.

- **Templating:** The message supports Jinja2 templating using the workflow context.
- **`{{ error }}` Context:** When an error occurs, the engine adds an `error` object to the context specifically for resolving this message template. This object typically contains:
    - `error.step`: The name of the step that failed.
    - `error.error`: The string representation of the error message from the exception.
    - `error.raw_error`: The original exception object (use with caution in templates).

```yaml
on_error:
  action: fail
  message: "Error in step '{{ error.step }}': {{ error.error }}. Input args: {{ args }}"
```

## Retry Configuration (`on_error.retry`)

When using the `retry` action (explicitly or implicitly), you can configure the retry behavior within a nested `retry` block:

- **`max_attempts`**: (Required) The total number of times to attempt the step (including the initial attempt). A value of `3` means one initial try and up to two retries.
- **`delay`**: (Optional) The number of seconds to wait before the *next* retry attempt. Defaults to `0`.
- **`backoff`**: (Optional) A multiplier applied to the delay after each failed attempt. For example, a `delay` of `5` and `backoff` of `2` would result in waits of 5s, 10s, 20s, etc., before subsequent retries. Defaults to `1` (no backoff).

```yaml
steps:
  - name: database_connection
    task: check_db
    on_error:
      action: retry
      retry:
        max_attempts: 4
        delay: 3 # Wait 3s before first retry
        backoff: 1.5 # Wait 3*1.5=4.5s before second, 4.5*1.5=6.75s before third
      message: "Database connection failed after {{ error.retry_count }} retries: {{ error.error }}" 
      # Note: error context might include retry_count in future versions
```

## Error Handling Flows (`on_error.next`)

Instead of just failing or continuing, you can redirect the workflow to a different step upon failure using the `next` key.

- This allows you to define specific error handling or notification steps.
- When `next` is specified:
    - The engine marks the current step as failed.
    - It then jumps execution to the step named in the `next` value.
    - The workflow continues from that target step.
- This can be combined with `retry`. If all retries fail, the engine will jump to the `next` step instead of halting.

```yaml
steps:
  - name: process_data
    task: data_processor
    inputs: { file: "data.csv" }
    on_error:
      message: "Data processing failed: {{ error.error }}"
      next: report_processing_error # Jump here on failure

  - name: generate_report
    task: report_generator
    # This step is skipped if process_data fails

  - name: report_processing_error
    task: send_notification
    inputs:
      recipient: admin@example.com
      subject: "Workflow Error: Data Processing Failed"
      body: "Step '{{ error.step }}' failed with error: {{ error.error }}. Check logs."

  - name: final_cleanup
    task: cleanup # This runs even after jumping to report_processing_error
```

**See Also:** For a more comprehensive example combining flows, retry, continue, and error jumps, refer to the `complex_flow_error_handling.yaml` file in the examples directory.

## Task-Level Error Handling (For Developers)

While the YAML `on_error` block defines workflow-level responses, task developers should implement robust error handling *within* the task function itself.

- Use `try...except` blocks to catch expected errors (e.g., `FileNotFoundError`, API errors, validation errors).
- Use the centralized `handle_task_error(context: ErrorContext)` utility within the `except` block.
    - This ensures consistent logging.
    - It wraps unexpected errors in `TaskExecutionError`.
    - It respects the original error type if it's already a `TaskExecutionError`.
- Refer to the [Task Development Guide](task-development.md#error-handling-best-practices) for details on implementing this within task code. 