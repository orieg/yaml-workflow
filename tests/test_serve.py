"""Tests for the web dashboard (skip if fastapi not installed)."""

import json
from types import SimpleNamespace

import pytest
import yaml

from yaml_workflow.tasks import register_task

try:
    from fastapi.testclient import TestClient

    from yaml_workflow.serve.app import create_app

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")


@pytest.fixture
def inline_threads(monkeypatch):
    class InlineThread:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(
        "yaml_workflow.serve.app.threading", SimpleNamespace(Thread=InlineThread)
    )


@pytest.fixture
def client(tmp_path):
    """Create a test client with temporary workflow and runs directories."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a sample workflow
    sample = wf_dir / "hello.yaml"
    sample.write_text(
        "name: Hello\ndescription: A test workflow\n"
        "params:\n  name:\n    type: string\n    default: World\n"
        "steps:\n  - name: greet\n    task: noop\n"
    )

    app = create_app(workflow_dir=str(wf_dir), base_dir=str(runs_dir))
    return TestClient(app)


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "Hello" in response.text


def test_workflow_detail(client):
    response = client.get("/workflows/hello.yaml")
    assert response.status_code == 200
    assert "Hello" in response.text
    assert "name" in response.text  # param name


def test_workflow_not_found(client):
    response = client.get("/workflows/nonexistent.yaml")
    assert response.status_code == 404


def test_api_list_workflows(client):
    response = client.get("/api/workflows")
    assert response.status_code == 200
    data = response.json()
    assert len(data["workflows"]) == 1
    assert data["workflows"][0]["name"] == "Hello"


def test_api_list_runs_empty(client):
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["runs"] == []


def test_run_not_found(client):
    response = client.get("/runs/nonexistent_run")
    assert response.status_code == 404


@pytest.mark.parametrize("supplied", [False, True])
def test_trigger_run_preserves_engine_status(tmp_path, inline_threads, supplied):
    @register_task("dashboard_pause_input")
    def task(value: str) -> str:
        return value

    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    base_dir = tmp_path / "runs"
    path = workflow_dir / "waiting.yaml"
    waiting = {"name": "waiting", "task": "dashboard_pause_input", "resumable": True}
    if supplied:
        waiting["inputs"] = {"value": "answer"}
    path.write_text(
        yaml.safe_dump(
            {
                "name": "Dashboard pause",
                "params": {"greeting": {"required": True}},
                "steps": [
                    {
                        "name": "before",
                        "task": "dashboard_pause_input",
                        "inputs": {"value": "{{ args.greeting }}"},
                    },
                    waiting,
                ],
            }
        )
    )
    client = TestClient(create_app(str(workflow_dir), str(base_dir)))
    response = client.post(
        "/api/run", data={"workflow": str(path), "greeting": "saved"}
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    run = client.get(f"/api/runs/{run_id}").json()
    expected = "completed" if supplied else "paused"
    assert run["status"] == expected
    assert run["step_outputs"]["before"]["result"] == "saved"
    assert run["step_outputs"]["waiting"]["status"] == expected
    if not supplied:
        assert run["completed_steps"] == ["before"]
        assert run["step_outputs"]["waiting"]["missing_input"] == "value"
        detail = client.get(f"/runs/{run_id}")
        assert detail.status_code == 200
        assert "Waiting for input: value" in detail.text
        assert "bg-yellow-100 text-yellow-800" in detail.text
    assert all(r["status"] == expected for r in client.get("/api/runs").json()["runs"])

    restarted = TestClient(create_app(str(workflow_dir), str(base_dir)))
    persisted = restarted.get("/api/runs").json()["runs"]
    assert len(persisted) == 1
    assert persisted[0]["status"] == expected
    assert persisted[0]["step_outputs"]["waiting"]["status"] == expected


@pytest.fixture
def paused_dashboard(tmp_path, inline_threads):
    calls = []

    @register_task("dashboard_resume_input")
    def task(value: str) -> str:
        calls.append(value)
        return value

    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    base_dir = tmp_path / "runs"
    path = workflow_dir / "waiting.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "name": "Dashboard resume",
                "params": {"greeting": {"required": True}},
                "steps": [
                    {
                        "name": "before",
                        "task": "dashboard_resume_input",
                        "inputs": {"value": "{{ args.greeting }}"},
                    },
                    {
                        "name": "waiting",
                        "task": "dashboard_resume_input",
                        "resumable": True,
                    },
                    {
                        "name": "after",
                        "task": "dashboard_resume_input",
                        "inputs": {
                            "value": "{{ steps.before.result }} / {{ steps.waiting.result }}"
                        },
                    },
                ],
            }
        )
    )
    client = TestClient(create_app(str(workflow_dir), str(base_dir)))
    response = client.post(
        "/api/run", data={"workflow": str(path), "greeting": "saved"}
    )
    assert response.status_code == 200
    return client, response.json()["run_id"], workflow_dir, base_dir, calls


@pytest.mark.parametrize("restart", [False, True])
@pytest.mark.parametrize("form", [False, True])
def test_dashboard_resumes_same_run(paused_dashboard, restart, form):
    client, run_id, workflow_dir, base_dir, calls = paused_dashboard
    if restart:
        client = TestClient(create_app(str(workflow_dir), str(base_dir)))
    original = client.get(f"/api/runs/{run_id}").json()
    assert original["status"] == "paused"
    assert calls == ["saved"]
    detail = client.get(f"/runs/{run_id}")
    assert f"/api/runs/{run_id}/resume" in detail.text
    if form:
        response = client.post(
            f"/api/runs/{run_id}/resume",
            data={"params": '{"value": "answer"}'},
            headers={"accept": "text/html"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/runs/{run_id}"
    else:
        response = client.post(
            f"/api/runs/{run_id}/resume", json={"params": {"value": "answer"}}
        )
        assert response.status_code == 200
        assert response.json()["run_id"] == run_id
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["path"] == original["path"]
    assert run["created_at"] == original["created_at"]
    assert run["step_outputs"]["after"]["result"] == "saved / answer"
    assert calls == ["saved", "answer", "saved / answer"]
    assert len(client.get("/api/runs").json()["runs"]) == 1
    assert len(list(base_dir.iterdir())) == 1


def test_dashboard_resume_without_answer_remains_paused(paused_dashboard):
    client, run_id, _, _, calls = paused_dashboard
    response = client.post(f"/api/runs/{run_id}/resume", json={"params": {}})
    assert response.status_code == 200
    run = client.get(f"/api/runs/{run_id}").json()
    assert run["status"] == "paused"
    assert run["step_outputs"]["waiting"]["missing_input"] == "value"
    assert calls == ["saved"]


@pytest.mark.parametrize("body", [[], {"params": []}, {"params": "wrong"}])
def test_dashboard_resume_rejects_invalid_params(paused_dashboard, body):
    client, run_id, _, _, calls = paused_dashboard
    response = client.post(f"/api/runs/{run_id}/resume", json=body)
    assert response.status_code == 400
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "paused"
    assert calls == ["saved"]


def test_dashboard_resume_rejects_completed_run(paused_dashboard):
    client, run_id, _, _, calls = paused_dashboard
    client.post(f"/api/runs/{run_id}/resume", json={"params": {"value": "answer"}})
    response = client.post(
        f"/api/runs/{run_id}/resume", json={"params": {"value": "again"}}
    )
    assert response.status_code == 409
    assert calls == ["saved", "answer", "saved / answer"]


def test_dashboard_resume_rejects_running_run(paused_dashboard, monkeypatch):
    client, run_id, _, _, calls = paused_dashboard

    class DeferredThread:
        def __init__(self, target, daemon):
            pass

        def start(self):
            pass

    monkeypatch.setattr(
        "yaml_workflow.serve.app.threading", SimpleNamespace(Thread=DeferredThread)
    )
    first = client.post(
        f"/api/runs/{run_id}/resume", json={"params": {"value": "answer"}}
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/runs/{run_id}/resume", json={"params": {"value": "again"}}
    )
    assert second.status_code == 409
    assert calls == ["saved"]


def test_dashboard_resume_unknown_run(client):
    response = client.post("/api/runs/unknown/resume", json={"params": {}})
    assert response.status_code == 404
