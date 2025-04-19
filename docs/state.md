# State Management

YAML Workflow provides robust state management capabilities to track workflow execution, handle failures, and enable resumable workflows.

## State Storage

### State File Structure

The workflow state is stored in `.workflow_state.json` (or similar, often within `.workflow_metadata.json`) in the workspace directory. The exact structure evolves, but conceptually includes:

```json
{
    "workflow_id": "unique-workflow-id",
    "name": "workflow-name",
    "start_time": "2025-04-14T10:00:00Z",
    "last_updated": "2025-04-14T10:05:00Z",
    "status": "running", // Overall workflow status
    // Information about the execution progress and failures:
    "execution_state": {
        "status": "running", // Current execution status (running, failed, completed)
        "current_step": "step2",
        "failed_step": null, // Populated on failure
        "step_outputs": {   // Stores results of successfully completed steps
            "step1": {       // Key is the step name
                "result": "Output from Step 1" // The actual return value of the task is here
            }
            // step2 output would appear here upon completion
        },
        "retry_state": { // Information about retries
            "step_1_retry": {
                "attempt": 1,
                "max_attempts": 3
            }
        }
        // Other execution details like error messages might be stored here too
    },
    "variables": { // Snapshot of context variables (args, env etc. might be here)
        "user_input": "value",
        "computed_value": 42
    }
}
```

### State Lifecycle

1. **Initialization**
   - Created when workflow starts
   - Records start time and initial parameters
   - Initializes empty step tracking

2. **Step Execution**
   - Updates current step
   - Records step outputs
   - Tracks execution time

3. **Completion/Failure**
   - Records final status
   - Preserves outputs for resume
   - Logs error information if failed

## Resume Capability

### Resuming Failed Workflows

```bash
# Resume from last successful step
yaml-workflow run --resume workflow.yaml

# Resume from specific step
yaml-workflow run --resume --from-step step2 workflow.yaml

# Resume with modified parameters
yaml-workflow run --resume --override-params workflow.yaml
```

### Resume Behavior

1. **State Loading**
   - Reads previous state file
   - Validates step consistency
   - Merges new parameters

2. **Execution Strategy**
   - Skips completed steps
   - Restarts from failure point
   - Preserves previous outputs

3. **State Updates**
   - Maintains execution history
   - Updates modified steps
   - Tracks resume attempts

## Progress Tracking

### Step Progress

```yaml
steps:
  - name: long_running_step
    task: batch
    params:
      progress_update: true  # Enable progress tracking
      progress_interval: 5   # Update every 5 seconds
```

### Progress Information

- Step completion percentage
- Estimated time remaining
- Resource usage
- Error counts
- Retry attempts

## Error Handling

### Retry Mechanism

```yaml
steps:
  - name: api_call
    task: http_request
    retry:
      max_attempts: 3
      delay: 5
      backoff: 2
      on_error:
        - ConnectionError
        - TimeoutError
```

### Error Recovery

1. **Automatic Recovery**
   - Configurable retry policies
   - Exponential backoff
   - Error-specific handling

2. **Manual Intervention**
   - State inspection tools
   - Manual retry capability
   - Step skip options

## State Management API

### Reading State

```python
from yaml_workflow.state import WorkflowState

# Load current state
state = WorkflowState.load("workflow_id")

# Access state information
current_step = state.current_step
outputs = state.step_outputs
variables = state.variables
```

### Modifying State

```python
# Update state
state.update_step("step1", status="completed", output="result")
state.set_variable("key", "value")
state.mark_completed()

# Save changes
state.save()
```

## State Cleanup

### Automatic Cleanup

- Successful workflows: Optional state retention
- Failed workflows: State preserved for resume
- Configurable retention policy

### Manual Cleanup

```bash
# Clean old state files
yaml-workflow clean --older-than 30d

# Remove specific workflow state
yaml-workflow clean --workflow-id workflow-123

# Clean all successful states
yaml-workflow clean --status completed
```

## Best Practices

1. **State File Management**
   - Use version control ignore rules
   - Implement backup strategies
   - Clean up old state files

2. **Resume Strategy**
   - Design idempotent steps
   - Handle partial completions
   - Validate state consistency

3. **Error Handling**
   - Define retry policies
   - Log sufficient context
   - Plan for recovery

4. **Progress Monitoring**
   - Enable appropriate tracking
   - Set reasonable intervals
   - Monitor resource usage 