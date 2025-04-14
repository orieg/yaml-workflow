# Command Line Interface

The YAML Workflow CLI provides several commands to manage and execute workflows.

## Installation

The CLI is automatically installed with the package:

```bash
pip install yaml-workflow
```

## Basic Commands

### Initialize Workflows

Create new workflow directories with examples:

```bash
# Create workflows directory with all examples
yaml-workflow init

# Specify custom directory
yaml-workflow init --dir my-workflows

# Initialize with specific examples
yaml-workflow init --example hello_world
yaml-workflow init --example data_processing
```

### List Workflows

Display available workflows in the current directory:

```bash
# List all workflows
yaml-workflow list

# List workflows in specific directory
yaml-workflow list --dir my-workflows

# Show detailed information
yaml-workflow list --verbose
```

### Validate Workflows

Check workflow configuration for errors:

```bash
# Validate a specific workflow
yaml-workflow validate workflows/hello_world.yaml

# Validate all workflows in directory
yaml-workflow validate --dir workflows/

# Show detailed validation output
yaml-workflow validate --verbose workflows/hello_world.yaml
```

### Run Workflows

Execute workflow files:

```bash
# Run with input parameters
yaml-workflow run workflows/hello_world.yaml name=Alice age=25

# Run with environment variables
yaml-workflow run --env-file .env workflows/process.yaml

# Run specific flow
yaml-workflow run --flow data_collection workflows/multi_flow.yaml

# Resume failed workflow
yaml-workflow run --resume workflows/long_process.yaml

# Run with parallel execution
yaml-workflow run --parallel --max-workers 4 workflows/batch_process.yaml
```

## Advanced Usage

### Environment Variables

The CLI respects the following environment variables:

- `YAML_WORKFLOW_DIR`: Default workflows directory
- `YAML_WORKFLOW_CONFIG`: Path to global configuration
- `YAML_WORKFLOW_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `YAML_WORKFLOW_PARALLEL`: Enable parallel execution by default
- `YAML_WORKFLOW_MAX_WORKERS`: Default number of parallel workers

### Configuration File

Global configuration can be set in `~/.yaml-workflow/config.yaml`:

```yaml
default_dir: ~/workflows
log_level: INFO
parallel: false
max_workers: 4
env_files:
  - ~/.env
  - .env.local
```

### Exit Codes

The CLI uses the following exit codes:

- `0`: Success
- `1`: General error
- `2`: Invalid configuration
- `3`: Workflow execution error
- `4`: Permission error
- `5`: Resource not found

### Logging

Control log output with the following flags:

```bash
# Enable debug logging
yaml-workflow --debug run workflow.yaml

# Quiet mode (errors only)
yaml-workflow --quiet run workflow.yaml

# Output logs to file
yaml-workflow --log-file workflow.log run workflow.yaml

# JSON format logging
yaml-workflow --log-format json run workflow.yaml
```

## Examples

### Basic Workflow Execution

```bash
# Run a simple greeting workflow
yaml-workflow run workflows/hello.yaml name=World

# Expected output:
# Starting workflow: hello
# Step 1/1: Greeting
# Hello, World!
# Workflow completed successfully
```

### Parallel Batch Processing

```bash
# Process multiple files in parallel
yaml-workflow run workflows/batch.yaml \
  --parallel \
  --max-workers 4 \
  input_dir=data \
  output_dir=processed
```

### Error Handling

```bash
# Run with automatic retry on failure
yaml-workflow run workflows/api_calls.yaml \
  --retry-count 3 \
  --retry-delay 5 \
  api_key=$API_KEY

# Resume from last successful step
yaml-workflow run --resume workflows/long_process.yaml
``` 