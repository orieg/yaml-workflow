# Web Dashboard

yaml-workflow includes a web UI for monitoring workflows and triggering runs.

## Installation

Install with the `serve` extra:

```bash
pip install 'yaml-workflow[serve]'
```

## Usage

Start the dashboard server:

```bash
yaml-workflow serve --port 8080 --dir workflows/
```

Then open `http://127.0.0.1:8080` in your browser.

## Features

- **Dashboard** -- list workflows and recent run history.
- **Workflow detail** -- YAML preview, parameter form, run history.
- **Run detail** -- step timeline with status, outputs, and logs.
- **API** -- JSON endpoints for programmatic access.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/workflows/{name}` | Workflow detail page |
| `GET` | `/runs/{id}` | Run detail page |
| `POST` | `/api/run` | Trigger a workflow run |
| `GET` | `/api/runs` | List all runs |
| `GET` | `/api/workflows` | List all workflows |

### Triggering a run via the API

```bash
curl -X POST http://127.0.0.1:8080/api/run \
  -H "Content-Type: application/json" \
  -d '{"workflow": "hello_world", "params": {"name": "Alice"}}'
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--dir` | Workflow directory | `workflows` |
| `--port` | Port to listen on | `8080` |
| `--host` | Host to bind to | `127.0.0.1` |
