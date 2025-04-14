# YAML Workflow

A lightweight, powerful, and flexible workflow engine that executes tasks defined in YAML configuration files. This engine allows you to create modular, reusable workflows by connecting tasks through YAML definitions, with support for parallel processing, batch operations, and state management.

## Features

- 📝 YAML-driven workflow definition
- 🔌 Dynamic module and function loading
- 🔄 Input/output variable management
- ⚠️ Comprehensive error handling
- 🔁 Retry mechanisms
- ⚡ Parallel processing support
- 📊 Progress tracking and logging
- 💾 State persistence and resume capability
- 🔄 Batch processing with chunking
- 🌐 Template variable substitution
- 🔀 Flow control with custom step sequences

## Quick Start

1. Install the package:
```bash
pip install yaml-workflow
```

2. Initialize example workflows:
```bash
# Create workflows directory with examples
yaml-workflow init

# Or specify a custom directory
yaml-workflow init --dir my-workflows

# Initialize with specific examples only
yaml-workflow init --example hello_world
```

3. Run the example workflow:
```bash
# Run with input parameters
yaml-workflow run workflows/hello_world.yaml name=Alice

# List available workflows
yaml-workflow list

# Validate a workflow
yaml-workflow validate workflows/hello_world.yaml

# Resume a failed workflow
yaml-workflow run workflows/hello_world.yaml --resume
```

## Documentation

- [Task Types](https://github.com/orieg/yaml-workflow/blob/main/docs/tasks.md) - Available task types and how to use them
- [Workflow Structure](https://github.com/orieg/yaml-workflow/blob/main/docs/workflow-structure.md) - Detailed workflow configuration
- [Development Guide](https://github.com/orieg/yaml-workflow/blob/main/docs/development.md) - Setup, building, and contributing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
