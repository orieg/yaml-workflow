# Cookbook

Real-world workflow examples for common automation tasks.

## Data ETL Pipeline

Extract data from an API, transform it, and load it into files:

```yaml
name: Data ETL Pipeline
description: Fetch, transform, and store API data

params:
  api_url:
    type: string
    default: "https://jsonplaceholder.typicode.com/users"
  output_dir:
    type: string
    default: "output"

steps:
  # Extract: fetch data from API
  - name: fetch_data
    task: http.request
    inputs:
      url: "{{ args.api_url }}"
      timeout: 30

  # Transform: process the JSON response
  - name: transform_data
    task: python_code
    inputs:
      code: |
        import json
        users = json.loads(steps["fetch_data"]["result"]["body"])
        # Extract just names and emails
        result = [
            {"name": u["name"], "email": u["email"], "city": u["address"]["city"]}
            for u in users
        ]

  # Load: write to JSON file
  - name: save_json
    task: write_json
    inputs:
      file: "output/users.json"
      data: "{{ steps.transform_data.result.result }}"
      indent: 2

  # Load: write summary report
  - name: write_report
    task: template
    inputs:
      template: |
        ETL Pipeline Report
        ===================
        Source: {{ args.api_url }}
        Records processed: {{ steps.transform_data.result.result | length }}
        Output: output/users.json
        Status: Complete
      output_file: output/etl_report.txt

  - name: show_report
    task: shell
    inputs:
      command: cat output/etl_report.txt
```

## CI/CD Pipeline

Run linting, tests, and build steps in sequence:

```yaml
name: CI Pipeline
description: Lint, test, and build a Python project

params:
  project_dir:
    type: string
    default: "."
  python_version:
    type: string
    default: "python3"

steps:
  - name: check_environment
    task: shell
    inputs:
      command: |
        echo "Python: $({{ args.python_version }} --version)"
        echo "Pip: $(pip --version)"
        echo "Project: {{ args.project_dir }}"

  - name: install_deps
    task: shell
    inputs:
      command: pip install -e "{{ args.project_dir }}[test,dev]"
    on_error:
      action: fail
      message: "Dependency installation failed"

  - name: lint_check
    task: shell
    inputs:
      command: |
        echo "Running black..."
        black --check {{ args.project_dir }}/src
        echo "Running isort..."
        isort --check-only {{ args.project_dir }}/src
    on_error:
      action: continue
      message: "Linting issues found (continuing)"

  - name: type_check
    task: shell
    inputs:
      command: mypy {{ args.project_dir }}/src
    on_error:
      action: continue
      message: "Type errors found (continuing)"

  - name: run_tests
    task: shell
    inputs:
      command: pytest {{ args.project_dir }}/tests --cov --cov-report=term-missing -q
    on_error:
      action: fail
      message: "Tests failed"

  - name: build_package
    task: shell
    inputs:
      command: "{{ args.python_version }} -m build {{ args.project_dir }}"
    on_error:
      action: fail
      message: "Build failed"

  - name: report
    task: print_message
    inputs:
      message: |
        CI Pipeline Complete
        - Lint: {{ steps.lint_check.result.return_code | default('skipped') }}
        - Types: {{ steps.type_check.result.return_code | default('skipped') }}
        - Tests: passed
        - Build: passed
```

## Deployment Workflow

Deploy an application with validation and rollback capability:

```yaml
name: Deploy Application
description: Deploy with pre-checks and rollback support

params:
  environment:
    type: string
    default: staging
    allowed_values: [staging, production]
  version:
    type: string
    required: true

steps:
  # Pre-deployment checks
  - name: validate_version
    task: shell
    inputs:
      command: |
        echo "Deploying version {{ args.version }} to {{ args.environment }}"
        # Check version format
        if ! echo "{{ args.version }}" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
          echo "Invalid version format. Expected vX.Y.Z" >&2
          exit 1
        fi
    on_error:
      action: fail
      message: "Version validation failed"

  - name: backup_current
    task: shell
    inputs:
      command: |
        echo "Backing up current deployment..."
        mkdir -p output/backups
        echo "{{ args.environment }}-backup-$(date +%Y%m%d)" > output/backups/manifest.txt

  # Deploy
  - name: deploy
    task: shell
    inputs:
      command: |
        echo "Deploying {{ args.version }} to {{ args.environment }}..."
        echo "{{ args.version }}" > output/current_version.txt
        echo "Deployment complete"
    on_error:
      action: retry
      retry: 2
      delay: 5
      next: rollback
      message: "Deployment failed, will retry"

  # Post-deployment validation
  - name: health_check
    task: shell
    inputs:
      command: |
        echo "Running health checks..."
        DEPLOYED=$(cat output/current_version.txt)
        if [ "$DEPLOYED" = "{{ args.version }}" ]; then
          echo "Health check passed: version $DEPLOYED running"
        else
          echo "Health check failed: expected {{ args.version }}, got $DEPLOYED" >&2
          exit 1
        fi
    on_error:
      action: fail
      next: rollback

  - name: notify_success
    task: print_message
    inputs:
      message: |
        Deployment successful!
        Version: {{ args.version }}
        Environment: {{ args.environment }}

  # Rollback handler
  - name: rollback
    task: shell
    inputs:
      command: |
        echo "Rolling back deployment..."
        echo "Restored from backup"
    condition: "False"

flows:
  default: deploy_flow
  definitions:
    - deploy_flow:
        - validate_version
        - backup_current
        - deploy
        - health_check
        - notify_success
```

## File Processing with Batch

Process multiple files in parallel:

```yaml
name: Batch File Processor
description: Process a batch of data files in parallel

params:
  input_dir:
    type: string
    default: "data"

steps:
  - name: list_files
    task: python_code
    inputs:
      code: |
        import os
        files = [f for f in os.listdir(args.get("input_dir", "data"))
                 if f.endswith(".txt")]
        result = files

  - name: process_files
    task: batch
    inputs:
      items: "{{ steps.list_files.result.result }}"
      max_workers: 4
      task:
        task: shell
        inputs:
          command: |
            echo "Processing {{ batch.item }}..."
            wc -l "{{ args.input_dir }}/{{ batch.item }}"

  - name: summary
    task: print_message
    inputs:
      message: "Processed {{ steps.list_files.result.result | length }} files"
```

## Workflow with Shared Imports

Split reusable steps into shared files:

```yaml
# shared/logging.yaml
steps:
  - name: log_start
    task: shell
    inputs:
      command: echo "[$(date)] Workflow started"

  - name: log_end
    task: shell
    inputs:
      command: echo "[$(date)] Workflow completed"
```

```yaml
# main_workflow.yaml
name: Workflow with Imports
imports:
  - shared/logging.yaml

steps:
  - name: do_work
    task: shell
    inputs:
      command: echo "Doing the actual work..."
```

The imported `log_start` step runs before `do_work`, and `log_end` runs after.

## Conditional Branching

Route execution based on data:

```yaml
name: Conditional Pipeline
params:
  format:
    type: string
    default: json

steps:
  - name: detect
    task: python_code
    inputs:
      code: |
        result = {"format": args.get("format", "unknown")}

  - name: process_json
    task: shell
    inputs:
      command: echo "Processing JSON data"
    condition: '{% if steps.detect.result.result.format == "json" %}True{% else %}False{% endif %}'

  - name: process_csv
    task: shell
    inputs:
      command: echo "Processing CSV data"
    condition: '{% if steps.detect.result.result.format == "csv" %}True{% else %}False{% endif %}'

  - name: done
    task: print_message
    inputs:
      message: "Pipeline complete for format: {{ args.format }}"
```

Visualize with `yaml-workflow visualize` to see the branching structure:

```
  ┌────────────────┐
  │     detect     │
  │  python_code   │
  └────────────────┘
           │
           ▼
  ┌──────────────┐  ┌──────────────┐
  │ process_json │  │ process_csv  │
  │    shell     │  │    shell     │
  └──────────────┘  └──────────────┘
           │
           ▼
  ┌────────────────┐
  │      done      │
  │ print_message  │
  └────────────────┘
```
