# Architecture

This page describes the internal architecture of the YAML Workflow Engine.

## Overview

```
                         +-----------+
                         |    CLI    |
                         | (cli.py)  |
                         +-----+-----+
                               |
                    args, workflow path
                               |
                               v
                    +----------+-----------+
                    |   WorkflowEngine     |
                    |     (engine.py)      |
                    |                      |
                    |  - Load YAML         |
                    |  - Process imports   |
                    |  - Validate params   |
                    |  - Resolve flows     |
                    |  - Execute steps     |
                    +---+------+-------+---+
                        |      |       |
           +------------+      |       +------------+
           |                   |                    |
           v                   v                    v
    +------+------+    +-------+-------+    +-------+-------+
    | TemplateEng |    | WorkflowState |    |   Workspace   |
    | (template)  |    |  (state.py)   |    | (workspace.py)|
    |             |    |               |    |               |
    | Jinja2      |    | Persistence   |    | Directories   |
    | resolution  |    | Resume/retry  |    | Logging       |
    +-------------+    +---------------+    +---------------+

                    +----------+-----------+
                    |     Step             |
                    |    (step.py)         |
                    |                      |
                    |  - Condition eval    |
                    |  - Input rendering   |
                    |  - Error handling    |
                    +----------+-----------+
                               |
                               v
                    +----------+-----------+
                    |    Task Registry     |
                    |  (tasks/__init__.py) |
                    |                      |
                    |  @register_task()    |
                    |  get_task_handler()  |
                    |  Plugin discovery    |
                    +---+--+--+--+--+--+--+
                        |  |  |  |  |  |
           +------+-----+  |  |  |  +-----+------+
           |      |        |  |  |        |       |
           v      v        v  v  v        v       v
        shell   file    python  template  http   batch
        tasks   tasks   tasks   tasks     tasks  tasks
```

## Execution Flow

When you run `yaml-workflow run workflow.yaml name=Alice`:

1. **CLI** (`cli.py`) parses arguments, extracts `name=Alice` as a parameter
2. **WorkflowEngine** (`engine.py`) initializes:
    - Loads the YAML file
    - Processes `imports` (merges steps/params from imported files)
    - Validates the workflow structure and parameters
    - Creates a workspace directory for this run
    - Sets up logging
    - Initializes execution context with namespaces (`args`, `env`, `steps`)
3. **Run loop** iterates through steps:
    - For each step, creates a **Step** object
    - Evaluates the `condition` (if any) via **TemplateEngine**
    - Resolves input templates (e.g., `{{ args.name }}` becomes `Alice`)
    - Looks up the task handler via **Task Registry**
    - Executes the handler with a **TaskConfig** object
    - Stores the result in `context["steps"][step_name]`
    - Updates **WorkflowState** (for resume capability)
4. **On error**: retries, skips, or jumps to error handler based on `on_error` config
5. **On completion**: marks workflow as completed, returns results

## Key Components

### WorkflowEngine (`engine.py`)

The central orchestrator. Responsibilities:

- YAML loading and validation
- Import processing (merging steps/params from other files)
- Parameter validation (required, type, min/max length, allowed values)
- Flow resolution (determining which steps to execute in which order)
- Step execution loop with retry/error handling
- Dry-run mode (preview without executing)
- Context management (namespaces for variable access)

### Step (`step.py`)

Represents a single workflow step. Handles:

- **Condition evaluation**: Jinja2 expression that must resolve to `"True"`
- **Input rendering**: Recursive template processing of all input values
- **Error handling**: `on_error` configuration (fail, continue, retry, next)

### TaskConfig (`tasks/config.py`)

The interface between the engine and task handlers:

```python
class TaskConfig:
    name: str                    # Step name
    type: str                    # Task type (e.g., "shell")
    inputs: dict                 # Raw inputs from YAML
    workspace: Path              # Workspace directory
    context: Dict[str, Any]      # Read-only execution context
    processed_inputs: Dict       # Template-resolved inputs

    def process_inputs() -> dict  # Resolve templates in inputs
    def get_variable(name, namespace) -> Any
    def get_available_variables() -> dict
```

### Task Registry (`tasks/__init__.py`)

Manages task handler registration and lookup:

- `@register_task("name")` decorator registers a function
- `get_task_handler("name")` returns the handler
- `_discover_plugins()` loads tasks from entry points at startup

### Template Engine (`template.py`)

Jinja2 wrapper with:

- `StrictUndefined` mode (errors on undefined variables)
- `AttrDict` for dot-notation access (e.g., `steps.my_step.result`)
- Recursive processing of nested dicts/lists
- Helpful error messages showing available variables

### Workflow State (`state.py`)

Manages execution persistence:

- Tracks completed/failed/skipped steps
- Stores step outputs for resume capability
- Manages retry counts per step
- Saves to `.workflow_metadata.json` in workspace

### Workspace (`workspace.py`)

File system management:

- Creates run-specific directories (`workflow_name_run_N/`)
- Manages logs directory
- Provides workspace info (size, file count, creation time)

## Variable Namespaces

The execution context provides these namespaces:

| Namespace | Access | Description |
|-----------|--------|-------------|
| `args` | `{{ args.name }}` | CLI parameters and workflow params |
| `env` | `{{ env.PATH }}` | Environment variables |
| `steps` | `{{ steps.step_name.result }}` | Results from completed steps |
| `workflow` | `{{ workflow.name }}` | Workflow metadata |
| `settings` | `{{ settings.key }}` | Workflow settings |
| `batch` | `{{ batch.item }}` | Current item in batch processing (only available inside batch tasks) |

## Plugin System

External packages can register tasks via Python entry points:

```toml
# In plugin's pyproject.toml
[project.entry-points."yaml_workflow.tasks"]
my_tasks = "my_plugin.tasks"
```

When `my_plugin.tasks` is imported, any `@register_task()` decorated functions are automatically registered. The engine discovers plugins at import time via `importlib.metadata.entry_points()`.
