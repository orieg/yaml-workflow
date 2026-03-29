# YAML Workflow Engine

A lightweight, powerful, and flexible workflow engine that executes tasks defined in YAML configuration files.

## Overview

**YAML Workflow** is a streamlined task automation tool designed for developers. It excels at:

- Running local development workflows
- Automating repetitive tasks
- Building data processing pipelines
- Scripting with better error handling than shell scripts

Define powerful workflows through simple YAML files with advanced features like error handling, retry mechanisms, conditional execution, and state persistence. The engine runs locally without requiring external databases or infrastructure.

## Key Features

- **YAML-driven** workflow definitions with Jinja2 templating
- **Multiple task types**: shell, Python, file, template, HTTP, batch
- **Workflow composition** via `imports` — reuse steps across workflows
- **Plugin system** via entry points — extend with `pip install`
- **Watch mode** — re-run automatically on file changes
- **Dry-run mode** to preview execution without side effects
- **Workflow visualization** as ASCII branching DAGs or Mermaid charts
- **State persistence** with resume from failures
- **Parallel execution** with configurable worker pools
- **Retry mechanisms** with configurable strategies
- **Flow control** with custom step sequences and conditions
- **Extensible** task system via `@register_task` decorator

## Quick Start

```bash
# Install the package
pip install yaml-workflow

# Initialize a new project with example workflows
yaml-workflow init --example hello_world

# Run the example workflow
yaml-workflow run workflows/hello_world.yaml name=World

# Preview without executing
yaml-workflow run workflows/hello_world.yaml name=World --dry-run

# Visualize the workflow
yaml-workflow visualize workflows/hello_world.yaml
```

### Example output

```
  Workflow: Hello World

  ┌─────────────────┐
  │ create_greeting │
  │     template    │
  └─────────────────┘
           │
           ▼
  ┌─────────────────┐
  │    show_info    │
  │      shell      │
  └─────────────────┘

  2 steps (0 conditional, 2 always-run)
```

## Documentation Structure

- **[Guide](guide/getting-started.md):** Tutorials, core concepts, features, and usage guides.
- **[Examples](examples/basic-workflow.md):** Practical workflow examples.
- **[API Reference](reference/SUMMARY.md):** Detailed API documentation for modules and classes.
- **[Contributing](development.md):** Guidelines for contributing to the project.
