# Getting Started

This guide will help you get started with the YAML Workflow Engine.

## Installation

Install the YAML Workflow Engine using pip:

```bash
pip install yaml-workflow
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
- See more [examples](../examples/index.md) 