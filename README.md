# YAML Workflow

[![PyPI version](https://img.shields.io/pypi/v/yaml-workflow.svg)](https://pypi.org/project/yaml-workflow/)
[![Python versions](https://img.shields.io/pypi/pyversions/yaml-workflow.svg)](https://pypi.org/project/yaml-workflow/)
[![CI](https://github.com/orieg/yaml-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/orieg/yaml-workflow/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/orieg/yaml-workflow/graph/badge.svg)](https://codecov.io/gh/orieg/yaml-workflow)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A lightweight, powerful, and flexible workflow engine that executes tasks defined in YAML configuration files. Create modular, reusable workflows by connecting tasks through YAML definitions, with support for parallel processing, batch operations, and state management.

## Why yaml-workflow?

Most workflow tools (Airflow, Prefect, Dagster) are designed for distributed cloud infrastructure with complex server setups. **yaml-workflow** takes a different approach:

| | yaml-workflow | Airflow / Prefect / Dagster |
|---|---|---|
| **Setup** | `pip install yaml-workflow` | Server, database, scheduler, workers |
| **Configuration** | Plain YAML files | Python DAGs + infrastructure config |
| **Dependencies** | 2 (PyYAML, Jinja2) | 50+ packages, Docker, PostgreSQL |
| **Use case** | Local automation, scripts, CI/CD, data pipelines | Enterprise orchestration at scale |
| **Learning curve** | Minutes | Hours to days |
| **State** | File-based, resumable | Database-backed |

**Choose yaml-workflow when you need:**
- Simple task automation without infrastructure overhead
- Reproducible pipelines defined in version-controlled YAML
- Batch processing with parallel execution
- State persistence and workflow resume after failures
- A lightweight alternative to shell scripts with better error handling

## Features

- YAML-driven workflow definition with Jinja2 templating
- Multiple task types: shell, Python, file, template, HTTP, batch
- Workflow composition via `imports` — reuse steps across workflows
- Plugin system via entry points — `pip install yaml-workflow-myplugin`
- Watch mode — `--watch` to re-run on file changes
- Dry-run mode to preview without executing
- Workflow visualization (ASCII branching DAG and Mermaid)
- Parallel execution with configurable worker pools
- State persistence and resume capability
- Retry mechanisms with configurable strategies
- Namespaced variables (`args`, `env`, `steps`, `batch`)
- Flow control with custom step sequences and conditions
- Extensible task system via `@register_task` decorator

## Quick Start

```bash
# Install (isolated CLI — recommended)
pipx install yaml-workflow

# Or install with pip
pip install yaml-workflow

# Initialize example workflows
yaml-workflow init

# Run a workflow with parameters
yaml-workflow run workflows/hello_world.yaml name=Alice
```

**Example workflow** (`hello_world.yaml`):

```yaml
name: Hello World
description: A simple greeting workflow

params:
  name:
    type: string
    default: World

steps:
  - name: create_greeting
    task: template
    inputs:
      template: "Hello, {{ args.name }}!"
      output_file: greeting.txt

  - name: show_greeting
    task: shell
    inputs:
      command: cat greeting.txt
```

### Visualize workflows

```bash
yaml-workflow visualize workflows/data_pipeline.yaml
```

```
  Workflow: Data Pipeline

  ┌─────────────────┐
  │  detect_format  │
  │   python_code   │
  └─────────────────┘
           │
           ▼
  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
  │  process_json  │  │  process_csv   │  │  process_xml   │  │ handle_unknown │
  │     shell      │  │     shell      │  │     shell      │  │     shell      │
  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘
           │
           ▼
  ┌─────────────────┐
  │ generate_report │
  │   python_code   │
  └─────────────────┘
```

Adjacent conditional steps are automatically grouped as branches. Use `--format mermaid` to export for docs or GitHub rendering.

### Dry-run mode

Preview what a workflow would do without executing anything:

```bash
yaml-workflow run workflows/hello_world.yaml name=Alice --dry-run
```

```
[DRY-RUN] Workflow: Hello World
[DRY-RUN] Steps: 2 to execute

  [DRY-RUN] Step 'create_greeting' — task: template — WOULD EXECUTE
    template: Hello, Alice!
    output_file: greeting.txt
  [DRY-RUN] Step 'show_greeting' — task: shell — WOULD EXECUTE
    command: cat greeting.txt

[DRY-RUN] Complete. 2 step(s) would execute, 0 would be skipped.
[DRY-RUN] No files were written. No tasks were executed.
```

### Workflow composition

Reuse steps across workflows with `imports`:

```yaml
# main.yaml
imports:
  - ./shared/logging_steps.yaml
  - ./shared/common_params.yaml

steps:
  - name: my_step
    task: shell
    inputs:
      command: echo "runs after imported steps"
```

Imported steps are prepended. Imported params provide defaults that the main workflow can override. Supports transitive imports with circular detection.

### Watch mode

Automatically re-run on file changes during development:

```bash
yaml-workflow run workflows/hello_world.yaml name=Alice --watch
```

Monitors the workflow file and all imported files. Press `Ctrl+C` to stop.

### More commands

```bash
# List available workflows
yaml-workflow list

# Validate a workflow
yaml-workflow validate workflows/hello_world.yaml

# Resume a failed workflow
yaml-workflow run workflows/hello_world.yaml --resume
```

## Documentation

Full documentation is available at **[orieg.github.io/yaml-workflow](https://orieg.github.io/yaml-workflow/)**.

- [Getting Started](https://orieg.github.io/yaml-workflow/guide/getting-started/) - Installation and first workflow
- [Task Types](https://orieg.github.io/yaml-workflow/guide/tasks/basic-tasks/) - Shell, Python, file, template, and batch tasks
- [Workflow Structure](https://orieg.github.io/yaml-workflow/workflow-structure/) - YAML configuration reference
- [Templating](https://orieg.github.io/yaml-workflow/guide/templating/) - Jinja2 variable substitution
- [State Management](https://orieg.github.io/yaml-workflow/state/) - Persistence and resume
- [Task Development](https://orieg.github.io/yaml-workflow/guide/task-development/) - Creating custom tasks
- [API Reference](https://orieg.github.io/yaml-workflow/reference/) - Full API documentation

## Contributing

Contributions are welcome! See the [Contributing Guide](https://orieg.github.io/yaml-workflow/contributing/development/) for development setup and guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
