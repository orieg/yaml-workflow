# Web Dashboard

yaml-workflow includes a web UI for monitoring workflows and triggering runs.

## Installation

The web dashboard requires the `serve` extra:

```bash
pipx install 'yaml-workflow[serve]'   # or yaml-workflow[all]
# or
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

Runs waiting for a required input on a resumable step are shown as `paused`,
with the missing input in the step timeline and API step data. Paused steps
are not included in the completed-step count.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Dashboard |
| `GET` | `/workflows/{name}` | Workflow detail page |
| `GET` | `/runs/{id}` | Run detail page |
| `POST` | `/api/run` | Trigger a workflow run |
| `POST` | `/api/runs/{id}/resume` | Resume a paused or failed run with additional parameters |
| `GET` | `/api/runs` | List all runs |
| `GET` | `/api/workflows` | List all workflows |

### Triggering a run via the API

```bash
curl -X POST http://127.0.0.1:8080/api/run \
  -H "Content-Type: application/json" \
  -d '{"workflow": "hello_world", "params": {"name": "Alice"}}'
```

### Resuming a run

Open a paused run's detail page, enter additional parameters as a JSON object,
and select **Resume**. The engine restores saved parameters and outputs and
continues in the existing workspace. Supplied parameter values override saved
ones. The run keeps its ID across dashboard restarts.

The same operation is available through the API:

```bash
curl -X POST http://127.0.0.1:8080/api/runs/RUN_ID/resume \
  -H "Content-Type: application/json" \
  -d '{"params": {"answer": "yes"}}'
```

The API returns `run_id` and `status: started`; execution continues in a background
thread. Inspect `GET /api/runs/RUN_ID` for the resulting state. Missing answers
leave the run paused. Completed and already-running runs cannot be resumed.

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--dir` | Workflow directory | `workflows` |
| `--port` | Port to listen on | `8080` |
| `--host` | Host to bind to | `127.0.0.1` |
