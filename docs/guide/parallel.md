# Parallel Execution

yaml-workflow supports parallel step execution via `depends_on`. Steps that declare explicit
dependencies run after those dependencies complete. Independent steps at the same level
run concurrently using a thread pool.

## Basic Usage

Use `depends_on` to declare which steps must finish before a given step starts:

```yaml
steps:
  - name: fetch_users
    task: http.request
    inputs:
      url: https://api.example.com/users

  - name: fetch_orders
    task: http.request
    depends_on: []          # no deps -- runs in parallel with fetch_users
    inputs:
      url: https://api.example.com/orders

  - name: merge
    task: python_code
    depends_on:
      - fetch_users
      - fetch_orders        # waits for both before running
    inputs:
      code: |
        users  = steps["fetch_users"]["result"]
        orders = steps["fetch_orders"]["result"]
        result = {"users": users, "orders": orders}
```

The example above forms a diamond DAG:

```
  fetch_users    fetch_orders
       \              /
        \            /
          merge
```

`fetch_users` and `fetch_orders` execute in parallel. `merge` waits for both to complete.

## How It Works

- Steps **without** `depends_on` implicitly depend on the previous step (sequential order preserved).
- Steps **with** `depends_on` explicitly declare which steps they need.
- Independent steps run in parallel within the same execution level.
- `settings.max_workers` controls the thread pool size (default: 4).

The engine builds a dependency graph from all steps and groups them into execution
levels. Steps in the same level have all their dependencies satisfied and can run
concurrently.

## Controlling Parallelism

Set the maximum number of concurrent workers in the workflow settings:

```yaml
settings:
  max_workers: 8    # default is 4
```

## Example: Parallel Data Fetching

```yaml
name: Parallel Data Pipeline
description: Fetch from three sources in parallel, then merge

settings:
  max_workers: 4

steps:
  - name: fetch_inventory
    task: http.request
    inputs:
      url: https://api.example.com/inventory

  - name: fetch_pricing
    task: http.request
    depends_on: []
    inputs:
      url: https://api.example.com/pricing

  - name: fetch_suppliers
    task: http.request
    depends_on: []
    inputs:
      url: https://api.example.com/suppliers

  - name: merge_data
    task: python_code
    depends_on:
      - fetch_inventory
      - fetch_pricing
      - fetch_suppliers
    inputs:
      code: |
        inventory = steps["fetch_inventory"]["result"]
        pricing   = steps["fetch_pricing"]["result"]
        suppliers = steps["fetch_suppliers"]["result"]
        result = {
            "inventory": inventory,
            "pricing": pricing,
            "suppliers": suppliers,
        }

  - name: generate_report
    task: template
    inputs:
      template: |
        Report generated with {{ steps.merge_data.result | length }} data sources.
      output_file: output/report.txt
```

## Limitations

- `on_error.next` (jump to another step) is not supported in parallel levels.
- All steps in a parallel level must complete before the next level starts.
- The thread pool uses Python threads; for I/O-heavy work, consider batch task parallelism.
