# Hello World Example

This example demonstrates the core features of YAML Workflow:
- Template task for generating text with variable substitution
- Shell task for running commands and displaying information
- Built-in variables (run_number, workflow_name, timestamp, workspace)

## Workflow File

```yaml
# A minimal example workflow that demonstrates core features:
# - Template task for generating text with variable substitution
# - Shell task for running commands and displaying information
# - Built-in variables (run_number, workflow_name, timestamp, workspace)
#
# Required parameters:
# - name: The name to include in the greeting (e.g., name=World)

name: Hello World
description: A simple workflow that creates a greeting

params:
  name:
    description: Name to include in the greeting
    default: World

steps:
  - name: create_greeting
    task: template
    template: |
      Hello, {{ name }}!
      
      This is run #{{ run_number }} of the {{ workflow_name }} workflow.
      Created at: {{ timestamp }}
      Workspace: {{ workspace }}
    output: greeting.txt

  - name: show_info
    task: shell
    command: |
      echo "Workflow run information:"
      echo "------------------------"
      echo "Run number: {{ run_number }}"
      echo "Workflow: {{ workflow_name }}"
      echo "Created: {{ timestamp }}"
      echo "Workspace: {{ workspace }}"
      echo "------------------------"
      echo "Current directory: $(pwd)"
      cat greeting.txt
```

## Features Demonstrated

1. **Parameter Definition**
   - Defines a `name` parameter with a default value
   - Uses parameter validation and description

2. **Template Task**
   - Creates a greeting using template substitution
   - Demonstrates variable interpolation
   - Shows output file creation

3. **Shell Task**
   - Runs shell commands
   - Shows environment information
   - Reads and displays files

4. **Built-in Variables**
   - `run_number`: Unique run identifier
   - `workflow_name`: Name of the workflow
   - `timestamp`: Current time
   - `workspace`: Working directory

## Usage

1. Save the workflow:
```bash
mkdir -p workflows
cp examples/hello_world.yaml workflows/
```

2. Run with default parameter:
```bash
yaml-workflow run workflows/hello_world.yaml
```

3. Run with custom name:
```bash
yaml-workflow run workflows/hello_world.yaml name="Alice"
```

## Expected Output

```
Workflow run information:
------------------------
Run number: 1
Workflow: Hello World
Created: 2024-01-23T10:30:00Z
Workspace: /path/to/workspace
------------------------
Current directory: /path/to/workspace
Hello, Alice!

This is run #1 of the Hello World workflow.
Created at: 2024-01-23T10:30:00Z
Workspace: /path/to/workspace
``` 