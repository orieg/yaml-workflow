# YAML Workflow Engine

A lightweight, powerful, and flexible workflow engine that executes tasks defined in YAML configuration files.

## Overview

**YAML Workflow** is a streamlined task automation tool designed for developers. It excels at:
- Running local development workflows
- Automating repetitive tasks
- Generating daily/weekly reports
- Processing data in a structured way

Define powerful workflows through simple YAML files with advanced features like error handling, dependencies, and conditional execution. The engine runs locally without requiring external databases or infrastructure.

## Key Features

- Simple YAML-based workflow definitions
- Flexible task execution system
- Built-in error handling and recovery
- Modular workflow composition
- Extensive templating support
- Rich parameter handling
- Flow control and conditional execution

## Quick Start

```bash
# Install the package
pip install yaml-workflow

# Initialize a new project with example workflows
yaml-workflow init --example hello_world

# Run the example workflow
yaml-workflow run workflows/hello_world.yaml name=World
```

## Documentation Structure

- **[Guide](guide/getting-started.md):** Tutorials, core concepts, features, and usage guides.
- **[Examples](examples/basic-workflow.md):** Practical workflow examples.
- **[API Reference](reference/SUMMARY.md):** Detailed API documentation for modules and classes.
- **[Contributing](development.md):** Guidelines for contributing to the project. 