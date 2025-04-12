# YAML Workflow Engine

A simple and flexible workflow engine that executes tasks defined in YAML configuration files.

## Quick Start

1. Create a virtual environment and install the package:
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Unix/macOS
# On Windows use: .venv\Scripts\activate

# Install the package
pip install -e .
```

2. Run a sample workflow:
```bash
# Run the hello world workflow
yaml-workflow run workflows/hello_world.yaml name=Alice

# List available workflows
yaml-workflow list

# Validate a workflow
yaml-workflow validate workflows/my_workflow.yaml
```

## Features

- YAML-driven workflow definition
- Dynamic module and function loading
- Input/output variable management
- Error handling and retry mechanisms
- Conditional execution
- Parallel processing support
- API rate limiting

## Example Workflow

```yaml
workflow:
  steps:
    - name: say_hello
      module: yaml_workflow_engine.tasks.basic_tasks
      function: hello_world
      inputs:
        name: ${name}
      outputs:
        - greeting
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

## Available Task Modules

1. Basic Tasks (`yaml_workflow_engine.tasks.basic_tasks`):
   - `hello_world`: Simple greeting function
   - `add_numbers`: Add two numbers
   - `join_strings`: Join multiple strings
   - `create_greeting`: Create custom greetings

2. File Tasks (`yaml_workflow_engine.tasks.file_tasks`):
   - `read_file`: Read text files
   - `write_file`: Write text files
   - `read_json`: Read JSON files
   - `write_json`: Write JSON files
   - `read_yaml`: Read YAML files
   - `write_yaml`: Write YAML files

3. Shell Tasks (`yaml_workflow_engine.tasks.shell_tasks`):
   - `run_command`: Execute shell commands
   - `check_command`: Execute commands with error checking
   - `get_environment`: Get environment variables
   - `set_environment`: Set environment variables