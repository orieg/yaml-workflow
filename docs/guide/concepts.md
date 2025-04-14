# Core Concepts

This document explains the core concepts of the YAML Workflow Engine.

## Workflows

A workflow is a YAML file that defines a sequence of tasks to be executed. Each workflow can have:

- A name and description
- Parameter definitions
- Environment variables
- A sequence of steps (tasks)
- Flow definitions for organizing steps

Example workflow structure:
```yaml
name: Data Processing Workflow
description: Process and analyze data files

params:
  input_file:
    description: Input file to process
    type: string
    required: true
  batch_size:
    description: Number of items to process at once
    type: integer
    default: 100

env:
  DEBUG: "true"
  TEMP_DIR: "./temp"

steps:
  - name: validate_input
    task: file_check
    params:
      path: "{{ input_file }}"
      
  - name: process_data
    task: data_processor
    params:
      input: "{{ input_file }}"
      batch_size: "{{ batch_size }}"
```

## Tasks

Tasks are the building blocks of workflows. Each task:

- Has a specific type (e.g., shell, python, http)
- Can accept parameters
- Can produce outputs
- Can have conditions for execution
- Can include error handling

## Parameters

Parameters allow workflows to be dynamic and reusable:

- Can be defined at workflow or task level
- Support type validation
- Can have default values
- Can be required or optional
- Support Jinja2 templating

## Flows

Flows allow you to organize steps into logical groups:

```yaml
flows:
  default: process  # Default flow to execute
  definitions:
    - process: [validate_input, process_data, save_results]
    - cleanup: [archive_data, cleanup_temp]
```

Benefits of flows:

- Organize steps into logical sequences
- Run different step combinations for different purposes
- Skip unnecessary steps
- Maintain multiple workflows in one file

## Error Handling

The engine provides several error handling mechanisms:

- Retry mechanisms for failed tasks
- Alternative paths on failure
- Skip or abort options
- Custom error handlers
- Detailed error reporting

## Templating

The engine uses Jinja2 for templating, allowing:

- Parameter substitution
- Environment variable access
- Task output reuse
- Conditional expressions
- Custom filters and functions 