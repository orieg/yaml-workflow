# AGENTS.md

Guidance for AI coding agents (Claude Code, Cursor, Copilot, and others) working
in the **yaml-workflow** repository. Humans: see [CONTRIBUTING.md](CONTRIBUTING.md).

## What this project is

yaml-workflow is a lightweight Python workflow engine that runs tasks defined in
YAML — shell, Python, file, template, HTTP, and batch — with Jinja2 templating,
parallel execution, and resumable file-based state. The core runtime depends on
only **PyYAML and Jinja2**; keep it that way — optional features (MCP server, web
dashboard) live behind extras.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev,test,doc]"
```

## Build, test, and lint

```bash
pytest tests/ --benchmark-disable                      # run the test suite
pytest tests/test_shell_tasks.py::test_shell_basic     # run a single test
black --check src tests                                 # format check
isort --check-only --profile black src tests            # import-order check
mypy src                                                # type check
mkdocs build                                            # build the docs site
```

Apply formatting with `black src tests && isort --profile black src tests`. Run
everything through the virtualenv (`source .venv/bin/activate`). CI runs black +
isort + mypy as a gate on Ubuntu / Python 3.12 **before** the tests, and runs
the test suite across Linux/macOS/Windows and Python 3.10–3.13 — so a change
must pass all four checks locally.

## Code layout

- `src/yaml_workflow/engine.py` — the workflow engine (parse, template, run, state).
- `src/yaml_workflow/cli.py` — CLI: `run`, `list`, `validate`, `visualize`, `init`, `serve`, `serve-mcp`.
- `src/yaml_workflow/tasks/` — built-in task types; register new ones with `@register_task`.
- `src/yaml_workflow/validator.py` — workflow validation (`yaml-workflow validate`).
- `src/yaml_workflow/mcp_server.py` — MCP server exposing workflows as agent tools.
- `src/yaml_workflow/examples/` — bundled example workflows (copied by `yaml-workflow init`).
- `schema/workflow-schema.json` — JSON Schema for the workflow YAML format.
- `tests/` — pytest suite, one file per module.
- `docs/` — MkDocs (Material) documentation source.

## Conventions

- **Commits:** `type(scope): description` (`feat`, `fix`, `docs`, `refactor`, `chore`, `test`). Keep them atomic.
- **Tests are required** for behavior changes; add them under `tests/` matching the module.
- **Type hints everywhere** — `mypy src` must pass (the package ships `py.typed`).
- **Update `CHANGELOG.md`** under `## [Unreleased]` for any user-facing change.
- **No new core runtime dependencies** — add an optional extra in `pyproject.toml` instead.
- **New task types** subclass the task base and register via `@register_task`; document them under `docs/guide/tasks/`.

## Authoring a workflow (quick reference)

A workflow is a YAML file with `name`, optional `params`, and ordered `steps`:

```yaml
name: Example
params:
  who:
    type: string
    default: World
steps:
  - name: greet
    task: shell
    inputs:
      command: echo "Hello, {{ args.who }}"
```

Validate with `yaml-workflow validate <file>`, preview with `--dry-run`, and
point your editor at `schema/workflow-schema.json` for autocomplete (see the
[Editor Integration guide](https://orieg.github.io/yaml-workflow/guide/editor-integration/)).
Full reference: <https://orieg.github.io/yaml-workflow/>.

## Before opening a PR

- [ ] `pytest tests/ --benchmark-disable` passes
- [ ] `black --check src tests` and `isort --check-only --profile black src tests` pass
- [ ] `mypy src` passes
- [ ] Docs updated if behavior or the public API changed
- [ ] `CHANGELOG.md` `[Unreleased]` updated for user-facing changes
