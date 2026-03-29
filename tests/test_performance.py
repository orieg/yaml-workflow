"""Performance benchmarks for the workflow engine."""

import pytest

from yaml_workflow.engine import WorkflowEngine


def make_workflow(num_steps, task_type="noop"):
    """Generate a workflow dictionary with the given number of steps.

    Args:
        num_steps: Number of steps to include in the workflow.
        task_type: Task type for each step ('noop' or 'echo').

    Returns:
        A workflow definition dictionary.
    """
    steps = []
    for i in range(num_steps):
        step = {"name": f"step_{i}", "task": task_type}
        if task_type == "echo":
            step["inputs"] = {"message": f"Step {i}"}
        elif task_type == "noop":
            pass  # noop needs no inputs
        steps.append(step)
    return {"name": "benchmark_workflow", "steps": steps}


# ---------------------------------------------------------------------------
# Engine overhead
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_engine_overhead(benchmark, tmp_path):
    """Benchmark minimal workflow (1 noop step)."""
    workflow = make_workflow(1)

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


# ---------------------------------------------------------------------------
# Scaling benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_scaling_10(benchmark, tmp_path):
    """Benchmark workflow with 10 noop steps."""
    workflow = make_workflow(10)

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


@pytest.mark.benchmark
def test_scaling_50(benchmark, tmp_path):
    """Benchmark workflow with 50 noop steps."""
    workflow = make_workflow(50)

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


@pytest.mark.benchmark
def test_scaling_100(benchmark, tmp_path):
    """Benchmark workflow with 100 noop steps."""
    workflow = make_workflow(100)

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


@pytest.mark.benchmark
def test_scaling_200(benchmark, tmp_path):
    """Benchmark workflow with 200 noop steps."""
    workflow = make_workflow(200)

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_template_rendering(benchmark, tmp_path):
    """Benchmark template rendering with Jinja2 expressions vs static inputs."""
    workflow = {
        "name": "template_benchmark",
        "params": {"x": {"default": "hello"}},
        "steps": [
            {
                "name": "static_step",
                "task": "echo",
                "inputs": {"message": "static value"},
            },
            {
                "name": "template_step",
                "task": "echo",
                "inputs": {"message": "{{ args.x }} world"},
            },
        ],
    }

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)


# ---------------------------------------------------------------------------
# Context size impact
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_context_size_impact(benchmark, tmp_path):
    """Benchmark with a large context dict passed through the workflow."""
    # Build a workflow where step_0 produces a large result, and subsequent
    # steps reference it via template expressions so the engine must carry the
    # full context through each step resolution.
    large_data = {f"key_{i}": f"value_{i}" for i in range(500)}
    steps = [
        {
            "name": "producer",
            "task": "noop",
            "inputs": large_data,
        },
        {
            "name": "consumer",
            "task": "echo",
            "inputs": {"message": "{{ steps.producer.result.processed_inputs.key_0 }}"},
        },
    ]
    workflow = {"name": "context_size_benchmark", "steps": steps}

    def run():
        engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
        engine.run()

    benchmark(run)
