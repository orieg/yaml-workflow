# Contributing to yaml-workflow

Thanks for your interest in contributing! This document covers everything you
need to get up and running, from setting up a dev environment to opening a
pull request.

A `CODE_OF_CONDUCT.md` should be added to this repository. Until then, please
interact respectfully with all contributors and maintainers.

---

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/orieg/yaml-workflow.git
cd yaml-workflow

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install the package in editable mode with all dev/test/docs extras
pip install -e ".[dev,test,doc]"
```

After this you should be able to run `yaml-workflow --help` and import
`yaml_workflow` in a Python REPL.

---

## Running Tests

```bash
# Run the full test suite (benchmarks disabled for speed)
pytest tests/ --benchmark-disable

# Run a single test file
pytest tests/test_shell_tasks.py

# Run a specific test by name
pytest tests/test_shell_tasks.py::test_shell_basic

# Run with coverage report
pytest tests/ --benchmark-disable --cov --cov-branch --cov=yaml_workflow --cov-report=term-missing

# Run benchmarks separately
pytest tests/test_performance.py --benchmark-json=benchmark-results.json -v
```

Tests are organised by module. Each task implementation in
`src/yaml_workflow/tasks/` has a corresponding test file in `tests/`.

---

## Code Style

The project uses **black** for formatting and **isort** for import ordering
(both configured in `pyproject.toml`).

```bash
# Check formatting without making changes
black --check src tests
isort --check-only --profile black src tests

# Apply formatting
black src tests
isort --profile black src tests

# Type checking
mypy src
```

CI runs all three checks on every pull request. Formatting failures will block
the merge, so it is easiest to run them locally before pushing.

---

## Writing Tests

- Test files live in `tests/` and are named `test_<module>.py`.
- Test functions are named `test_<what_is_being_tested>`.
- Use the `tmp_path` or `workspace` fixtures for any tests that write files.
- Shared fixtures belong in `tests/conftest.py`.
- Tests that rely on bash/unix-specific commands must be decorated with
  `@unix_only` (defined at the top of `tests/test_shell_tasks.py`) so they
  are automatically skipped on Windows CI runners.

```python
# Example: adding a test for a new task
def test_my_task_returns_expected_output(tmp_path):
    from yaml_workflow.tasks import TaskConfig
    from yaml_workflow.tasks.my_tasks import my_task

    step = {"name": "demo", "task": "my_task", "inputs": {"value": "hello"}}
    context = {"args": {}, "env": {}, "steps": {}}
    config = TaskConfig(step, context, tmp_path)

    result = my_task(config)
    assert result["output"] == "hello"
```

---

## Adding a New Task

Step-by-step instructions for writing a plugin task are in
[`docs/guide/plugins.md`](docs/guide/plugins.md). The same pattern applies to
tasks added directly inside `src/yaml_workflow/tasks/`:

1. Create `src/yaml_workflow/tasks/my_tasks.py`.
2. Import `TaskConfig` and `register_task` from `yaml_workflow.tasks`.
3. Decorate your handler with `@register_task("my_task")`.
4. Return a plain `dict` from the handler.
5. Import the module in `src/yaml_workflow/tasks/__init__.py` so the task is
   registered at startup.
6. Write tests in `tests/test_my_tasks.py`.

For external plugins that live in a separate package, follow the entry-point
approach documented in `docs/guide/plugins.md`.

---

## Submitting a PR

### Branch naming

```
feat/<short-description>
fix/<short-description>
docs/<short-description>
refactor/<short-description>
```

### Commit message format

Follow the existing style visible in `git log`:

```
<type>: <short imperative summary>

Optional longer body explaining the why, not the what.
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`.

### PR checklist

Before requesting a review, make sure:

- [ ] All existing tests pass (`pytest tests/ --benchmark-disable`)
- [ ] New behaviour is covered by tests
- [ ] Code is formatted (`black`, `isort`) and type-checked (`mypy src`)
- [ ] Relevant documentation is updated (docstrings, `docs/` pages)
- [ ] The PR description explains **what** changed and **why**

### GitHub ruleset requirements

The `main` branch is protected. A PR must:

- Pass all CI jobs (lint, test on Linux/macOS/Windows, benchmark)
- Receive at least one approving review from a maintainer

---

## Reporting Bugs

Open an issue at <https://github.com/orieg/yaml-workflow/issues> and include:

- yaml-workflow version (`yaml-workflow --version`)
- Python version and OS
- Minimal workflow YAML that reproduces the problem
- Full error output or traceback

---

## Release Process

Releases are managed by the project maintainers. When a release is ready, a
maintainer:

1. Updates the version in `pyproject.toml`
2. Creates a GitHub Release with a tag matching the version (e.g. `v0.7.0`)
3. The release triggers the publish workflow which builds and uploads to PyPI

Contributors do not need to do anything special — just get your PR merged and
the maintainers will handle the rest.
