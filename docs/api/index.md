# API Reference

This section provides detailed API documentation for the YAML Workflow Engine.

## Core Components

- [Core API](core.md) - Core classes and functions for workflow definition and execution
- [Engine](engine.md) - The workflow engine implementation
- [CLI](cli.md) - Command-line interface

## Package Structure

```
yaml_workflow/
├── __init__.py        # Package initialization
├── cli.py            # Command-line interface
├── engine.py         # Workflow engine
├── exceptions.py     # Custom exceptions
├── state.py         # Workflow state management
├── workspace.py      # Workspace configuration
└── tasks/           # Built-in task implementations
    ├── __init__.py
    ├── base.py      # Base task classes
    ├── basic_tasks.py
    ├── file_tasks.py
    ├── http_tasks.py
    └── shell_tasks.py
```

## Using the API

### Basic Usage

```python
from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.workspace import Workspace

# Initialize workspace
workspace = Workspace("path/to/workspace")

# Create engine instance
engine = WorkflowEngine(workspace)

# Load and run workflow
workflow = engine.load_workflow("workflows/example.yaml")
result = engine.run(workflow, params={"name": "World"})
```

### Custom Task Implementation

```python
from yaml_workflow.tasks.base import BaseTask

class CustomTask(BaseTask):
    """Custom task implementation."""
    
    task_type = "custom"  # Task type identifier
    
    def run(self, **params):
        """Execute the task."""
        # Task implementation here
        return {"status": "success", "output": "result"}
```

## API Stability

The YAML Workflow Engine follows semantic versioning:

- Major version changes (1.0.0 → 2.0.0) may include breaking changes
- Minor version changes (1.1.0 → 1.2.0) add features in a backward-compatible way
- Patch version changes (1.1.1 → 1.1.2) include backward-compatible bug fixes

APIs marked as experimental may change between minor versions. 