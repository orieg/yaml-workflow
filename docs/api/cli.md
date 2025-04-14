# Command Line Interface

The YAML Workflow Engine provides a command-line interface (CLI) for managing and running workflows.

## Command Overview

```bash
yaml-workflow [OPTIONS] COMMAND [ARGS]...
```

## Commands

### Initialize Project

```bash
yaml-workflow init [--example EXAMPLE]
```

Initialize a new YAML Workflow project in the current directory.

**Options:**
- `--example EXAMPLE`: Initialize with an example workflow (e.g., hello_world, data_pipeline)

### Run Workflow

```bash
yaml-workflow run [OPTIONS] WORKFLOW [PARAMS]...
```

Execute a workflow file with optional parameters.

**Options:**
- `--flow FLOW`: Specify which flow to run (default: the one specified in workflow)
- `--workspace PATH`: Specify workspace directory (default: current directory)
- `--env-file PATH`: Load environment variables from file
- `--debug`: Enable debug logging

**Parameters:**
- `WORKFLOW`: Path to the workflow file
- `PARAMS`: Key-value pairs for workflow parameters (e.g., name=value)

### List Tasks

```bash
yaml-workflow tasks list
```

List all available task types and their descriptions.

### Validate Workflow

```bash
yaml-workflow validate WORKFLOW
```

Validate a workflow file without executing it.

**Parameters:**
- `WORKFLOW`: Path to the workflow file to validate

## API Reference

### CLI Functions

::: yaml_workflow.cli
    options:
      show_root_heading: true
      show_source: true
      members:
        - main
        - run_workflow
        - init_project
        - list_tasks
        - validate_workflow

## Environment Variables

The CLI behavior can be configured using these environment variables:

- `YAML_WORKFLOW_HOME`: Base directory for YAML Workflow (default: ~/.yaml-workflow)
- `YAML_WORKFLOW_CONFIG`: Path to global configuration file
- `YAML_WORKFLOW_DEBUG`: Enable debug logging when set to 1 or true
- `YAML_WORKFLOW_NO_COLOR`: Disable colored output when set

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid command usage
- `3`: Workflow validation error
- `4`: Workflow execution error
- `5`: Configuration error

## Examples

1. Initialize a new project with example:
```bash
yaml-workflow init --example hello_world
```

2. Run a workflow with parameters:
```bash
yaml-workflow run workflows/process_data.yaml \
  input_file=data.csv \
  output_dir=results
```

3. Run a specific flow:
```bash
yaml-workflow run --flow cleanup workflows/maintenance.yaml
```

4. Run with environment file:
```bash
yaml-workflow run --env-file .env workflows/api_calls.yaml
```

5. Validate a workflow:
```bash
yaml-workflow validate workflows/complex_workflow.yaml
```

## Configuration

The CLI can be configured using a YAML configuration file at `~/.yaml-workflow/config.yaml`:

```yaml
# Global CLI configuration
default_workspace: ~/workflows
log_level: INFO
colors: true

# Default task settings
tasks:
  shell:
    timeout: 300
  http_request:
    verify_ssl: true
``` 