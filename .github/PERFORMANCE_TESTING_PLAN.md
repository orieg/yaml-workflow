# Performance Testing Plan (using pytest-benchmark)

## Goal

Implement performance benchmark tests for the `yaml-workflow` engine to measure execution overhead, scaling characteristics, and the relative performance of different task types and features. This will help identify bottlenecks and track performance regressions over time.

## Prerequisites

1.  **Add Dependency:** Add `pytest-benchmark` to the `[project.optional-dependencies.test]` section in `pyproject.toml`.
2.  **Install:** Ensure dependencies are installed (`pip install -e ".[test]"`).

## Test Plan

Tests will be implemented in `tests/test_performance.py`.

1.  **Engine Overhead:**
    *   Benchmark running a minimal workflow (e.g., 1 `noop` step) to measure baseline engine startup/teardown time.

2.  **Scaling - Number of Steps:**
    *   Benchmark workflows with increasing numbers of simple steps (e.g., 10, 50, 100, 200 `noop` or `echo` tasks).
    *   Analyze how execution time scales with the number of steps.

3.  **Task Type Comparison:**
    *   Benchmark workflows executing a fixed number (e.g., 50) of specific task types:
        *   `shell` (simple command like `echo hello`)
        *   `write_file` (small content)
        *   `read_file` (small content)
        *   `python` (simple operation like adding two numbers)
        *   `print_message`
    *   Compare the relative overhead of each task handler.

4.  **Template Rendering:**
    *   Benchmark a workflow with steps using moderately complex Jinja templates accessing `args` and previous `steps` results.
    *   Compare against a similar workflow with static inputs.

5.  **Context Size Impact (Timing):**
    *   Benchmark a workflow where steps generate and pass increasingly large data structures (e.g., dictionaries/lists of increasing size) via `steps.{step_name}.result`.
    *   Focus on execution time impact.

## Implementation Strategy

*   Use `pytest-benchmark` fixtures (`benchmark`) to run target functions multiple times.
*   Create helper functions to generate workflow dictionaries or temporary YAML files dynamically for different test scenarios (e.g., varying number of steps, task types).
*   Use the `WorkflowEngine` class directly within benchmarked functions for more precise control, rather than using the CLI via `run_cli`.
*   Establish baseline performance numbers by running the benchmarks initially. Store these results (e.g., using `pytest-benchmark`'s storage options) for future comparisons.

## Future Considerations

*   **Memory Profiling:** Investigate adding memory usage benchmarks later using tools like `memory-profiler` if needed.
*   **CI Integration:** Explore options for running benchmarks as part of the CI pipeline and potentially failing builds on significant performance regressions. 