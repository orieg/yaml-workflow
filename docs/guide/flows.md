# Flow Configuration Guide

YAML Workflow allows you to define specific execution paths, called **flows**, through the steps defined in your workflow. This enables more complex logic, such as running only a subset of steps, defining specific error handling paths, or having different execution sequences based on parameters.

## Defining Flows

Flows are defined within the optional top-level `flows` block in your workflow YAML file.

```yaml
name: My Workflow with Flows
params: { ... }
steps:
  - name: step_a
    task: ...
  - name: step_b
    task: ...
  - name: step_c
    task: ...
  - name: error_handler
    task: ...

flows:
  default: main_flow # Optional: Specifies the flow to run if none is provided via CLI

  definitions:
    - main_flow: # Name of the first flow
        - step_a
        - step_b
        - step_c

    - short_flow: # Name of a second flow
        - step_a
        - step_c

    - error_handling_flow: # A flow potentially used by on_error.next
        - error_handler
        - step_c # Maybe cleanup or final step
```

**Structure:**

- **`flows`**: The main key for flow configuration.
- **`flows.default`**: (Optional) The name of the flow to execute if the user runs `yaml-workflow run <workflow_file>` without specifying a `--flow` argument. If omitted, and flows are defined, the behavior might depend on the engine version (often defaulting to running *all* steps sequentially or requiring an explicit flow). For clarity, defining a `default` is recommended if you use flows.
- **`flows.definitions`**: A list containing flow definitions.
- **Flow Definition**: Each item in the `definitions` list is a dictionary where:
    - The *key* is the unique name of the flow (e.g., `main_flow`).
    - The *value* is an ordered list of step names (strings) that constitute that flow. The steps listed must exist in the main `steps:` block of the workflow.

## Executing a Specific Flow

You can execute a specific flow using the `--flow` option in the CLI:

```bash
# Run the flow named 'short_flow'
yaml-workflow run my_workflow.yaml --flow short_flow

# Run the default flow (if defined, otherwise might error or run all steps)
yaml-workflow run my_workflow.yaml 
```

## Use Cases for Flows

1.  **Subset Execution:** Run only a specific sequence of steps for certain scenarios (e.g., a setup flow, a teardown flow, a testing flow).
2.  **Conditional Logic (High-Level):** While fine-grained conditions are handled by the `condition` key within individual steps, you could potentially have different flows triggered based on input parameters passed to the workflow script that *calls* `yaml-workflow run --flow ...`.
3.  **Error Handling Paths:** As shown in the [Error Handling Guide](error-handling.md#error-handling-flows-onerrornext), the `on_error.next` key can target a specific step. By defining flows consisting of error handling steps, you can create structured error recovery or notification sequences.

**See Also:** The `complex_flow_error_handling.yaml` file in the examples directory provides a practical demonstration of using different flows for standard execution, subset execution, and error handling paths.

## Best Practices

- **Clear Naming:** Give your flows descriptive names.
- **Define a Default:** If you use flows, define a `default` flow for standard execution and clarity.
- **Validate Steps:** Ensure all step names listed within a flow definition correspond to actual steps defined in the main `steps:` block. The engine performs validation, but checking beforehand is good practice.
- **Combine with `condition`:** Use step-level `condition` keys for fine-grained conditional execution *within* a flow. Flows control the overall sequence, while `condition` controls whether an individual step in that sequence runs.
- **Keep Flows Focused:** Avoid overly complex flows. If a flow becomes very long or has many branches, consider if refactoring the workflow or splitting it into multiple workflow files might be clearer. 