"""Pause and resume a persisted run across independent worker processes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_WORKER = r"""
import json
import os
import sys

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.tasks import TaskConfig, register_task


def record(config, name):
    with (config.workspace / "calls.txt").open("a") as stream:
        stream.write(name + "\n")


@register_task("prepare")
def prepare(config: TaskConfig):
    record(config, "prepare")
    return {"project": config.context["args"]["project"], "pid": os.getpid()}


@register_task("named_input")
def named_input(answer: dict, config: TaskConfig):
    record(config, "human")
    return {"answer": answer, "pid": os.getpid()}


@register_task("config_input")
def config_input(config: TaskConfig):
    answer = config.process_inputs()["answer"]
    record(config, "human")
    return {"answer": answer, "pid": os.getpid()}


@register_task("finish")
def finish(config: TaskConfig):
    record(config, "finish")
    return {
        "prepared": config.context["steps"]["prepare"]["result"]["project"],
        "answer": config.context["steps"]["human"]["result"]["answer"],
        "project": config.context["args"]["project"],
        "root_project": config.context["project"],
        "pid": os.getpid(),
    }


engine = WorkflowEngine(sys.argv[1], workspace=sys.argv[2], base_dir=sys.argv[3])
if sys.argv[4] == "start":
    result = engine.run(params={"project": "original"})
else:
    result = engine.run(resume_from="human", params={"answer": {"approved": True}})
print(json.dumps({"pid": os.getpid(), "result": result}))
"""


@pytest.mark.parametrize("task_type", ["named_input", "config_input"])
def test_pause_resume_across_processes(tmp_path: Path, task_type: str) -> None:
    worker = tmp_path / "worker.py"
    worker.write_text(_WORKER)
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        yaml.safe_dump(
            {
                "name": "Worker restart",
                "params": {"project": {"required": True}},
                "steps": [
                    {"name": "prepare", "task": "prepare"},
                    {
                        "name": "human",
                        "task": task_type,
                        "resumable": True,
                        "on_error": {"retry": 2, "action": "continue"},
                    },
                    {"name": "finish", "task": "finish"},
                ],
            }
        )
    )
    original_workflow = workflow.read_bytes()
    workspace = tmp_path / "workspace"
    source = str(Path(__file__).resolve().parents[1] / "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [source] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )

    def run_worker(mode: str) -> dict:
        process = subprocess.run(
            [
                sys.executable,
                str(worker),
                str(workflow),
                str(workspace),
                str(tmp_path / "runs"),
                mode,
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert process.returncode == 0, process.stderr
        return json.loads(process.stdout)

    # subprocess.run returns only after the first worker has exited.
    first = run_worker("start")
    assert first["result"]["status"] == "paused"
    assert (workspace / "calls.txt").read_text().splitlines() == ["prepare"]
    metadata_path = workspace / ".workflow_metadata.json"
    paused = json.loads(metadata_path.read_text())
    state = paused["execution_state"]
    assert state["status"] == "paused"
    assert state["completed_steps"] == ["prepare"]
    assert state["completed_at"] is None
    assert state["failed_step"] is None
    assert state["retry_counts"] == {}
    assert state["step_outputs"]["human"]["missing_input"] == "answer"
    assert "finish" not in state["step_outputs"]

    second = run_worker("resume")
    assert second["pid"] != first["pid"]
    assert second["result"]["status"] == "completed"
    outputs = second["result"]["outputs"]
    assert outputs["prepare"] == first["result"]["outputs"]["prepare"]
    assert outputs["prepare"]["result"]["pid"] == first["pid"]
    assert outputs["human"]["result"] == {
        "answer": {"approved": True},
        "pid": second["pid"],
    }
    assert outputs["finish"]["result"] == {
        "prepared": "original",
        "answer": {"approved": True},
        "project": "original",
        "root_project": "original",
        "pid": second["pid"],
    }
    assert (workspace / "calls.txt").read_text().splitlines() == [
        "prepare",
        "human",
        "finish",
    ]
    completed = json.loads(metadata_path.read_text())
    assert completed["created_at"] == paused["created_at"]
    assert completed["execution_state"]["status"] == "completed"
    assert completed["execution_state"]["completed_steps"] == [
        "prepare",
        "human",
        "finish",
    ]
    assert completed["namespaces"]["args"] == {
        "project": "original",
        "answer": {"approved": True},
    }
    assert workflow.read_bytes() == original_workflow
