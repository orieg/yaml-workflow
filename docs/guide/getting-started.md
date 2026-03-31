# Getting Started

This guide will help you get started with the YAML Workflow Engine.

## Installation

**Option 1: pipx (recommended for CLI use)**

[pipx](https://pipx.pypa.io/) installs the `yaml-workflow` command in an isolated environment, so it never conflicts with your project's dependencies:

```bash
# Core CLI (run, validate, visualize, init)
pipx install yaml-workflow

# With web dashboard
pipx install 'yaml-workflow[serve]'

# With MCP server (AI agent integration)
pipx install 'yaml-workflow[mcp]'

# Everything
pipx install 'yaml-workflow[all]'
```

Install pipx first if needed: `brew install pipx` (macOS) or `pip install pipx`.

**Option 2: pip**

Install into the current Python environment (useful when using yaml-workflow as a library):

```bash
pip install yaml-workflow          # Core
pip install 'yaml-workflow[serve]' # + web dashboard
pip install 'yaml-workflow[mcp]'   # + MCP server
pip install 'yaml-workflow[all]'   # Everything
```

**Option 3: Docker**

Run without installing Python:

```bash
docker run -p 8080:8080 -v $(pwd)/workflows:/app/workflows ghcr.io/orieg/yaml-workflow
```

## Basic Concepts

The YAML Workflow Engine is built around a few core concepts:

1. **Workflows**: YAML files that define a sequence of tasks to be executed
2. **Tasks**: Individual units of work that can be executed
3. **Flows**: Named sequences of tasks that can be executed together
4. **Parameters**: Values that can be passed to workflows and tasks

## Your First Workflow

1. Create a new directory for your workflow:

```bash
mkdir my-workflow
cd my-workflow
```

2. Initialize a new workflow project:

```bash
yaml-workflow init --example hello_world
```

3. Examine the generated workflow file (`workflows/hello_world.yaml`):

```yaml
name: Hello World Workflow
description: A simple example workflow

params:
  name:
    description: Name to include in greeting
    type: string
    required: true

steps:
  - name: greet
    task: shell
    command: echo "Hello, {{ name }}!"
```

4. Run the workflow:

```bash
yaml-workflow run workflows/hello_world.yaml name=World
```

## Next Steps

- Learn about [workflow configuration](configuration.md)
- Explore [built-in tasks](tasks/index.md)
- See more [examples](../examples/basic-workflow.md) 