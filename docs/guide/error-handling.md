# Error Handling Patterns

YAML Workflow provides robust mechanisms for handling errors gracefully within your workflows. This guide covers common patterns and best practices.

## Core Concepts

- **`TaskExecutionError`**: The base exception raised when a task fails during execution. It often wraps the original exception.
- **`on_error` block**: A step-level configuration to define behavior when that specific step fails.
- **Retry Mechanism**: Automatically retry failed steps based on configuration.
- **Error Context**: Information about the error (step name, original exception, etc.) is available in templates within the `on_error` block and potentially passed to error handling steps.
- **State Management**: The engine tracks the status of each step (completed, failed, skipped) and the overall workflow status.

## Step-Level Error Handling (`on_error`)

*For a runnable example demonstrating the concepts below (retry, continue, next, error messages), see `docs/examples/error_handling/workflow.yaml`.*

You can define how a step should react to its own failure using the `on_error` block within the step definition.

```yaml
steps:
  - name: risky_api_call
    task: api_call
    inputs:
      url: "{{ env.API_URL }}/data"
    on_error:
      action: retry # or fail, continue, next
      retry: 3
      delay: 10 # seconds
      message: "API call failed for {{ args.item }}: {{ error }}" # Optional custom message
      next: handle_api_failure # Optional target step for 'next' action
```

### Actions:

- **`fail` (Default)**: The step is marked as failed, and the entire workflow halts immediately, raising a `WorkflowError`.
- **`retry`**: Attempts to re-run the failed step.
  - `retry` (integer): Maximum number of retry attempts (defaults to global setting or 3).
  - `delay` (integer/float): Seconds to wait before the next retry attempt (defaults to 0).
  - If retries are exhausted, the behavior defaults to `fail` unless `next` or `continue` is also specified.
- **`continue`**: Marks the step as failed but allows the workflow to proceed to the next step in the sequence. The failed step's output will not be available in the `steps` namespace.
- **`next`**: Marks the step as failed and jumps execution to a different step specified by the `next` key. This allows for dedicated error handling flows.

### Custom Error Message (`message`)

- You can provide a custom error message template using `message` for logging and state tracking.
- This template can use Jinja2 syntax and access standard context variables (`args`, `env`, `steps`).
- It can also access the core error details using the `error` variable:
  - `{{ error }}`: Provides the primary error information, often the string representation of the *original* exception that caused the failure (e.g., "FileNotFoundError: [Errno 2] No such file or directory...").
- The resolved `message` is stored in the workflow state for the failed step (e.g., accessible later via `steps.FAILED_STEP_NAME.error_message`) and is used in logs. Use this pattern to access formatted error messages in subsequent error-handling steps.

## Retry Strategies

- **Simple Retry**: Use `action: retry` with `retry` and `delay` for transient issues (e.g., network timeouts, temporary API unavailability). Best for idempotent operations where re-running is safe.
- **Retry with Backoff**: While not built-in directly as an exponential backoff flag, you could potentially implement custom retry logic within a Python task if needed, though standard linear delay is often sufficient.
- **Global Retries**: A global default retry count can potentially be set in workflow `settings` (implementation may vary).

## Error Handling Actions: When to Use What

- **`fail` (Default):** Use when any failure in the step is critical and the entire workflow should stop immediately.
- **`retry`:** Use for transient errors where re-running the step might succeed (e.g., network issues, temporary service unavailability). Ensure the step is safe to re-run (idempotent).
- **`continue`:** Use when a step's failure is non-critical, and the workflow can proceed meaningfully without its results. Subsequent steps should not depend directly on the output of the failed step.
- **`next`:** Use when a failure requires specific cleanup, compensation, or notification actions before potentially stopping or continuing the workflow. Redirects execution to a dedicated error-handling sequence.

## Error Handling Flows (`action: next`)

Use `action: next` to redirect the workflow to a dedicated error handling path.

```yaml
flows:
  default: main_flow
  definitions:
    - main_flow: [step_a, risky_step, step_c]
    - error_flow: [log_error, notify_admin] # Defines the sequence for the error path

steps:
  - name: step_a
    # ...
  - name: risky_step
    task: some_task
    # ...
    on_error:
      action: next
      next: log_error # Jump to the start of the error_flow sequence
      message: "Risky step failed for {{ args.id }}: {{ error }}" # Custom message stored in state
  - name: step_c
    # ... only runs if risky_step succeeds ...

  - name: log_error
    task: write_file
    inputs:
      path: "output/error_log.txt"
      content: |
        Workflow Failure Report
        -----------------------
        Timestamp: {{ workflow.timestamp }}
        Failed Step: {{ steps.risky_step.name }} {# Assumes 'risky_step' is the one that failed #}
        Reason: {{ steps.risky_step.error_message }} {# Access the formatted message defined above #}
        Original Error: {{ steps.risky_step.error }} {# Access raw error if needed #}

        Context:
        Args: {{ args | tojson }}
        # Add other relevant context if available
    # Note: This step runs *after* the risky_step failed and was redirected here.
    # It accesses the state (name, error_message, error) of the failed step.

  - name: notify_admin
    task: slack_notify # Example custom task
    inputs:
      channel: "#alerts"
      message: "Workflow {{ workflow.name }} failed at step {{ steps.risky_step.name }}. Reason: {{ steps.risky_step.error_message }}. See error_log.txt for details."
```

## Error Propagation

- When a step fails and the action is `fail` (or retries are exhausted with no `continue`/`next`), the engine wraps the original exception (or the `TaskExecutionError` created by `handle_task_error`) within a `WorkflowError` and halts execution.
- The `WorkflowError` contains information about the step that failed and often includes the original exception as its cause (`__cause__` or an `original_error` attribute), allowing programmatic inspection if the engine is used as a library.
- If `action: continue` is used, the error is logged and recorded in the state, but execution proceeds.
- If `action: next` is used, the error context is preserved in the failed step's state, and the workflow jumps to the specified step.

## Centralized Error Handling in Custom Tasks

As detailed in the [Task Development Guide](task-development.md#error-handling-best-practices), custom Python tasks should use the `handle_task_error` utility. This ensures:
- Consistent logging format.
- Wrapping of arbitrary exceptions into `TaskExecutionError`.
- Inclusion of relevant context (step name, task type, task config) in the raised exception. 