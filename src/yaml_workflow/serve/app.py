"""FastAPI web dashboard for yaml-workflow.

Provides a browser UI for listing workflows, viewing run history,
triggering workflow runs, and inspecting step-level results and logs.

Usage:
    yaml-workflow serve --port 8080 --dir workflows/
"""

import html
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(workflow_dir: str = "workflows", base_dir: str = "runs") -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        workflow_dir: Directory containing workflow YAML files.
        base_dir: Base directory for workflow run workspaces.
    """
    app = FastAPI(title="yaml-workflow", version="0.8.0")

    # In-memory tracking of live runs
    live_runs: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scan_workflows() -> List[Dict[str, Any]]:
        """Find all workflow YAML files in the workflow directory."""
        workflows: List[Dict[str, Any]] = []
        wf_path = Path(workflow_dir)
        if not wf_path.exists():
            return workflows
        for p in sorted(wf_path.glob("**/*.yaml")):
            try:
                with open(p) as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict) or "steps" not in data:
                    continue
                workflows.append(
                    {
                        "path": str(p),
                        "filename": p.name,
                        "name": data.get("name", p.stem),
                        "description": data.get("description", ""),
                        "params": data.get("params", {}),
                        "step_count": len(data.get("steps", [])),
                    }
                )
            except (yaml.YAMLError, OSError):
                continue
        return workflows

    def _scan_runs() -> List[Dict[str, Any]]:
        """Scan the runs directory for past workflow executions."""
        runs: List[Dict[str, Any]] = []
        runs_path = Path(base_dir)
        if not runs_path.exists():
            return runs
        for run_dir in sorted(runs_path.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            metadata_file = run_dir / ".workflow_metadata.json"
            if not metadata_file.exists():
                continue
            try:
                with open(metadata_file) as f:
                    meta = json.load(f)
                exec_state = meta.get("execution_state", {})
                runs.append(
                    {
                        "id": run_dir.name,
                        "path": str(run_dir),
                        "workflow": meta.get("workflow", run_dir.name),
                        "status": exec_state.get("status", "unknown"),
                        "created_at": meta.get("created_at", ""),
                        "completed_steps": exec_state.get("completed_steps", []),
                        "step_outputs": exec_state.get("step_outputs", {}),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return runs

    def _get_run(run_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific run."""
        # Look up run_id in the known runs list instead of constructing paths
        # from user input (avoids CodeQL py/path-injection)
        known_runs = _scan_runs()
        run_entry = next((r for r in known_runs if r["id"] == run_id), None)
        if run_entry is None:
            return None
        run_dir = Path(run_entry["path"])
        metadata_file = run_dir / ".workflow_metadata.json"
        if not metadata_file.exists():
            return None
        try:
            with open(metadata_file) as f:
                meta = json.load(f)
            exec_state = meta.get("execution_state", {})

            # Read log files
            logs = ""
            log_dir = run_dir / "logs"
            if log_dir.exists():
                for log_file in sorted(log_dir.glob("*.log")):
                    try:
                        logs += log_file.read_text()
                    except OSError:
                        pass

            return {
                "id": run_id,
                "path": str(run_dir),
                "workflow": meta.get("workflow", run_id),
                "status": exec_state.get("status", "unknown"),
                "created_at": meta.get("created_at", ""),
                "completed_steps": exec_state.get("completed_steps", []),
                "step_outputs": exec_state.get("step_outputs", {}),
                "failed_step": exec_state.get("failed_step"),
                "logs": logs,
            }
        except (json.JSONDecodeError, OSError):
            return None

    # ------------------------------------------------------------------
    # HTML rendering helpers
    # ------------------------------------------------------------------

    def _base_html(title: str, content: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} — yaml-workflow</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
            <a href="/" class="text-xl font-bold text-blue-600">yaml-workflow</a>
            <a href="/" class="text-gray-600 hover:text-gray-900">Dashboard</a>
            <a href="/api/runs" class="text-gray-600 hover:text-gray-900">API</a>
        </div>
    </nav>
    <main class="max-w-6xl mx-auto px-4 py-8">
        {content}
    </main>
    <footer class="max-w-6xl mx-auto px-4 py-6 text-sm text-gray-400 border-t mt-12">
        yaml-workflow dashboard
    </footer>
</body>
</html>"""

    def _status_badge(status: str) -> str:
        colors = {
            "completed": "bg-green-100 text-green-800",
            "success": "bg-green-100 text-green-800",
            "failed": "bg-red-100 text-red-800",
            "running": "bg-blue-100 text-blue-800",
            "in_progress": "bg-blue-100 text-blue-800",
            "pending": "bg-gray-100 text-gray-800",
        }
        cls = colors.get(status, "bg-gray-100 text-gray-800")
        return f'<span class="px-2 py-1 rounded-full text-xs font-medium {cls}">{html.escape(str(status))}</span>'

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Dashboard: list workflows and recent runs."""
        workflows = _scan_workflows()
        runs = _scan_runs()[:20]

        wf_rows = ""
        for wf in workflows:
            params_str = (
                html.escape(", ".join(wf["params"].keys())) if wf["params"] else "none"
            )
            wf_rows += f"""
            <tr class="border-b hover:bg-gray-50">
                <td class="px-4 py-3 font-medium">
                    <a href="/workflows/{html.escape(wf['filename'])}" class="text-blue-600 hover:underline">{html.escape(wf['name'])}</a>
                </td>
                <td class="px-4 py-3 text-gray-600">{html.escape(wf['description'][:80]) if wf['description'] else '-'}</td>
                <td class="px-4 py-3 text-gray-500">{wf['step_count']} steps</td>
                <td class="px-4 py-3 text-gray-500 text-sm">{params_str}</td>
            </tr>"""

        run_rows = ""
        for run in runs:
            run_rows += f"""
            <tr class="border-b hover:bg-gray-50">
                <td class="px-4 py-3">
                    <a href="/runs/{html.escape(run['id'])}" class="text-blue-600 hover:underline text-sm">{html.escape(run['id'][:40])}</a>
                </td>
                <td class="px-4 py-3">{html.escape(run['workflow'])}</td>
                <td class="px-4 py-3">{_status_badge(run['status'])}</td>
                <td class="px-4 py-3 text-gray-500 text-sm">{html.escape(run['created_at'][:19]) if run['created_at'] else '-'}</td>
                <td class="px-4 py-3 text-gray-500 text-sm">{len(run['completed_steps'])} steps</td>
            </tr>"""

        content = f"""
        <h1 class="text-2xl font-bold mb-6">Dashboard</h1>

        <h2 class="text-lg font-semibold mb-3">Workflows</h2>
        <div class="bg-white rounded-lg shadow overflow-hidden mb-8">
            <table class="w-full">
                <thead class="bg-gray-50 text-left text-sm text-gray-500">
                    <tr>
                        <th class="px-4 py-2">Name</th>
                        <th class="px-4 py-2">Description</th>
                        <th class="px-4 py-2">Steps</th>
                        <th class="px-4 py-2">Params</th>
                    </tr>
                </thead>
                <tbody>{wf_rows or '<tr><td colspan="4" class="px-4 py-6 text-gray-400 text-center">No workflows found</td></tr>'}</tbody>
            </table>
        </div>

        <h2 class="text-lg font-semibold mb-3">Recent Runs</h2>
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="w-full">
                <thead class="bg-gray-50 text-left text-sm text-gray-500">
                    <tr>
                        <th class="px-4 py-2">Run ID</th>
                        <th class="px-4 py-2">Workflow</th>
                        <th class="px-4 py-2">Status</th>
                        <th class="px-4 py-2">Created</th>
                        <th class="px-4 py-2">Steps</th>
                    </tr>
                </thead>
                <tbody>{run_rows or '<tr><td colspan="5" class="px-4 py-6 text-gray-400 text-center">No runs found</td></tr>'}</tbody>
            </table>
        </div>
        """
        return HTMLResponse(_base_html("Dashboard", content))

    @app.get("/workflows/{filename}", response_class=HTMLResponse)
    async def workflow_detail(filename: str):
        """Workflow detail: YAML preview, params form, run history."""
        # Look up filename in known workflows instead of constructing paths
        # from user input (avoids CodeQL py/path-injection)
        workflows = _scan_workflows()
        wf = next((w for w in workflows if w["filename"] == filename), None)
        if not wf:
            return HTMLResponse(
                _base_html("Not Found", "<p>Workflow not found.</p>"),
                status_code=404,
            )

        try:
            yaml_content = Path(wf["path"]).read_text()
        except OSError:
            yaml_content = "(could not read file)"

        # Build params form
        form_fields = ""
        for pname, pconfig in wf["params"].items():
            if isinstance(pconfig, dict):
                default = pconfig.get("default", "")
                desc = pconfig.get("description", "")
                ptype = pconfig.get("type", "string")
            else:
                default = pconfig
                desc = ""
                ptype = "string"
            form_fields += f"""
            <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-1">{html.escape(str(pname))} <span class="text-gray-400">({html.escape(str(ptype))})</span></label>
                <input type="text" name="{html.escape(str(pname))}" value="{html.escape(str(default))}"
                       class="w-full px-3 py-2 border rounded-md text-sm"
                       placeholder="{html.escape(str(desc))}">
            </div>"""

        # Find related runs
        runs = [r for r in _scan_runs() if r["workflow"] == wf["name"]][:10]
        run_rows = ""
        for run in runs:
            run_rows += f"""
            <tr class="border-b">
                <td class="px-3 py-2"><a href="/runs/{html.escape(run['id'])}" class="text-blue-600 hover:underline text-sm">{html.escape(run['id'][:30])}</a></td>
                <td class="px-3 py-2">{_status_badge(run['status'])}</td>
                <td class="px-3 py-2 text-sm text-gray-500">{html.escape(run['created_at'][:19]) if run['created_at'] else '-'}</td>
            </tr>"""

        content = f"""
        <div class="flex items-center gap-3 mb-6">
            <a href="/" class="text-gray-400 hover:text-gray-600">&larr; Dashboard</a>
            <h1 class="text-2xl font-bold">{html.escape(wf['name'])}</h1>
        </div>
        <p class="text-gray-600 mb-6">{html.escape(wf['description']) if wf['description'] else 'No description'}</p>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
                <h2 class="text-lg font-semibold mb-3">Run Workflow</h2>
                <form method="POST" action="/api/run" class="bg-white rounded-lg shadow p-4">
                    <input type="hidden" name="workflow" value="{html.escape(wf['path'])}">
                    {form_fields or '<p class="text-gray-400 text-sm">No parameters</p>'}
                    <button type="submit"
                            class="mt-3 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
                        Run
                    </button>
                </form>
            </div>
            <div>
                <h2 class="text-lg font-semibold mb-3">Workflow YAML</h2>
                <pre class="bg-gray-900 text-green-400 p-4 rounded-lg text-xs overflow-x-auto max-h-96">{html.escape(yaml_content)}</pre>
            </div>
        </div>

        <h2 class="text-lg font-semibold mt-8 mb-3">Run History</h2>
        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="w-full">
                <thead class="bg-gray-50 text-left text-sm text-gray-500">
                    <tr><th class="px-3 py-2">Run</th><th class="px-3 py-2">Status</th><th class="px-3 py-2">Created</th></tr>
                </thead>
                <tbody>{run_rows or '<tr><td colspan="3" class="px-3 py-4 text-gray-400 text-center">No runs yet</td></tr>'}</tbody>
            </table>
        </div>
        """
        return HTMLResponse(_base_html(wf["name"], content))

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    async def run_detail(run_id: str):
        """Run detail: step timeline, outputs, logs."""
        run = _get_run(run_id)
        if not run:
            # Check live runs
            if run_id in live_runs:
                run = live_runs[run_id]
            else:
                return HTMLResponse(
                    _base_html("Not Found", "<p>Run not found.</p>"),
                    status_code=404,
                )

        # Step timeline
        steps_html = ""
        for step_name in run.get("completed_steps", []):
            output = run.get("step_outputs", {}).get(step_name, {})
            result_str = json.dumps(output.get("result", {}), indent=2, default=str)[
                :500
            ]
            steps_html += f"""
            <div class="border-l-4 border-green-400 pl-4 py-2 mb-3">
                <div class="font-medium text-sm">{html.escape(str(step_name))} {_status_badge('completed')}</div>
                <pre class="text-xs text-gray-600 mt-1 overflow-x-auto">{html.escape(result_str)}</pre>
            </div>"""

        failed = run.get("failed_step")
        if failed:
            fname = (
                failed.get("step_name", "unknown")
                if isinstance(failed, dict)
                else str(failed)
            )
            ferr = failed.get("error_message", "") if isinstance(failed, dict) else ""
            steps_html += f"""
            <div class="border-l-4 border-red-400 pl-4 py-2 mb-3">
                <div class="font-medium text-sm">{html.escape(str(fname))} {_status_badge('failed')}</div>
                <pre class="text-xs text-red-600 mt-1">{html.escape(str(ferr))}</pre>
            </div>"""

        logs_html = html.escape(run.get("logs", ""))

        content = f"""
        <div class="flex items-center gap-3 mb-6">
            <a href="/" class="text-gray-400 hover:text-gray-600">&larr; Dashboard</a>
            <h1 class="text-2xl font-bold">Run: {html.escape(run['workflow'])}</h1>
            {_status_badge(run.get('status', 'unknown'))}
        </div>
        <p class="text-sm text-gray-500 mb-6">ID: {html.escape(str(run_id))} &bull; Created: {html.escape(run.get('created_at', '-')[:19])}</p>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
                <h2 class="text-lg font-semibold mb-3">Step Timeline</h2>
                <div class="bg-white rounded-lg shadow p-4">
                    {steps_html or '<p class="text-gray-400">No steps recorded</p>'}
                </div>
            </div>
            <div>
                <h2 class="text-lg font-semibold mb-3">Logs</h2>
                <pre class="bg-gray-900 text-gray-300 p-4 rounded-lg text-xs overflow-x-auto max-h-96">{logs_html or 'No logs available'}</pre>
            </div>
        </div>
        """
        return HTMLResponse(
            _base_html(f"Run \u2014 {html.escape(run['workflow'])}", content)
        )

    # ------------------------------------------------------------------
    # API routes
    # ------------------------------------------------------------------

    @app.post("/api/run")
    async def trigger_run(request: Request):
        """Trigger a workflow run in a background thread."""
        form = await request.form()
        workflow_ref = str(form.get("workflow", ""))
        params = {k: v for k, v in form.items() if k != "workflow" and v}

        if not workflow_ref:
            return JSONResponse({"error": "workflow path required"}, status_code=400)

        # Look up the workflow in known workflows instead of using raw user
        # input as a path (avoids CodeQL py/path-injection)
        known_workflows = _scan_workflows()
        wf_match = next(
            (w for w in known_workflows if w["path"] == workflow_ref),
            None,
        )
        if wf_match is None:
            return JSONResponse({"error": "workflow not found"}, status_code=404)
        workflow_path = wf_match["path"]

        run_id = (
            f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        live_runs[run_id] = {
            "id": run_id,
            "workflow": Path(str(workflow_path)).stem,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "completed_steps": [],
            "step_outputs": {},
            "logs": "",
        }

        def _run_in_bg():
            try:
                from yaml_workflow.engine import WorkflowEngine

                engine = WorkflowEngine(workflow_path, base_dir=base_dir)
                results = engine.run(**params)
                live_runs[run_id]["status"] = "completed"
                if results and results.get("outputs"):
                    live_runs[run_id]["step_outputs"] = results["outputs"]
                    live_runs[run_id]["completed_steps"] = list(
                        results["outputs"].keys()
                    )
            except Exception as e:
                live_runs[run_id]["status"] = "failed"
                live_runs[run_id]["logs"] = str(e)

        thread = threading.Thread(target=_run_in_bg, daemon=True)
        thread.start()

        # If request came from HTML form, redirect to dashboard
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/", status_code=303)
        return JSONResponse({"run_id": run_id, "status": "started"})

    @app.get("/api/runs")
    async def api_list_runs():
        """JSON API: list all runs."""
        runs = _scan_runs()
        # Include live runs
        for run_id, run in live_runs.items():
            if not any(r["id"] == run_id for r in runs):
                runs.insert(0, run)
        return JSONResponse({"runs": runs})

    @app.get("/api/runs/{run_id}")
    async def api_get_run(run_id: str):
        """JSON API: get run details."""
        run = _get_run(run_id)
        if not run and run_id in live_runs:
            run = live_runs[run_id]
        if not run:
            return JSONResponse({"error": "Run not found"}, status_code=404)
        return JSONResponse(run)

    @app.get("/api/workflows")
    async def api_list_workflows():
        """JSON API: list all workflows."""
        return JSONResponse({"workflows": _scan_workflows()})

    return app
