"""Tests for the web dashboard (skip if fastapi not installed)."""

import json

import pytest

try:
    from fastapi.testclient import TestClient

    from yaml_workflow.serve.app import create_app

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")


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
