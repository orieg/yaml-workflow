"""Tests for parallel step execution with depends_on."""

import time
from pathlib import Path
from threading import get_ident
from unittest.mock import MagicMock, patch

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import ConfigurationError, WorkflowError
from yaml_workflow.tasks import register_task
from yaml_workflow.validator import WorkflowValidator


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def _run_workflow(workflow_dict, workspace):
    """Helper to run a workflow dict and return results."""
    engine = WorkflowEngine(workflow_dict, base_dir=str(workspace))
    return engine.run()


@pytest.mark.parametrize("restart", [False, True])
def test_resume_parallel_pauses_keeps_full_graph(tmp_path, restart):
    calls = []

    @register_task("parallel_resume_record")
    def record(value: str) -> str:
        calls.append(value)
        return value

    workflow = {
        "steps": [
            {
                "name": "prepare",
                "task": "parallel_resume_record",
                "inputs": {"value": "prepared"},
            },
            {
                "name": "first",
                "task": "parallel_resume_record",
                "resumable": True,
                "depends_on": ["prepare"],
            },
            {
                "name": "second",
                "task": "parallel_resume_record",
                "resumable": True,
                "depends_on": ["prepare"],
            },
            {
                "name": "sibling",
                "task": "parallel_resume_record",
                "depends_on": ["prepare"],
                "inputs": {"value": "sibling"},
            },
            {
                "name": "join",
                "task": "parallel_resume_record",
                "depends_on": ["first", "second", "sibling"],
                "inputs": {
                    "value": "{{ steps.prepare.result }}:{{ steps.first.result }}:{{ steps.second.result }}"
                },
            },
        ],
    }
    engine = WorkflowEngine(workflow, base_dir=str(tmp_path))
    assert engine.run()["status"] == "paused"
    assert calls == ["prepared", "sibling"]
    workspace = engine.workspace

    # Resuming the later step must not drop the earlier unanswered step.
    workflow["steps"][2]["inputs"] = {"value": "two"}
    if restart:
        engine = WorkflowEngine(
            workflow, workspace=str(workspace), base_dir=str(tmp_path)
        )
    result = engine.run(resume_from="second")
    assert result["status"] == "paused"
    assert result["steps_state"]["first"]["status"] == "paused"
    assert result["outputs"]["second"]["result"] == "two"
    assert "join" not in result["steps_state"]

    workflow["steps"][1]["inputs"] = {"value": "one"}
    if restart:
        engine = WorkflowEngine(
            workflow, workspace=str(workspace), base_dir=str(tmp_path)
        )
    result = engine.run(resume_from="first")
    assert result["status"] == "completed"
    assert calls == ["prepared", "sibling", "two", "one", "prepared:one:two"]
    assert result["outputs"]["join"]["result"] == "prepared:one:two"


def test_empty_dependencies_preserve_nonresumable_sequential_behavior(tmp_path):
    @register_task("parallel_legacy_thread")
    def task() -> int:
        return get_ident()

    engine = WorkflowEngine(
        {
            "steps": [
                {"name": "first", "task": "parallel_legacy_thread", "depends_on": []},
                {"name": "second", "task": "parallel_legacy_thread", "depends_on": []},
            ]
        },
        base_dir=str(tmp_path),
    )
    result = engine.run()
    assert result["status"] == "completed"
    assert result["outputs"]["first"]["result"] == get_ident()
    assert result["outputs"]["second"]["result"] == get_ident()


def test_explicit_empty_dependencies_allow_sibling_to_finish(tmp_path):
    @register_task("parallel_empty_dependencies")
    def task(value: str) -> str:
        return value

    engine = WorkflowEngine(
        {
            "steps": [
                {
                    "name": "waiting",
                    "task": "parallel_empty_dependencies",
                    "resumable": True,
                    "depends_on": [],
                },
                {"name": "sibling", "task": "noop", "depends_on": []},
            ]
        },
        base_dir=str(tmp_path),
    )
    result = engine.run()
    assert result["status"] == "paused"
    assert result["steps_state"]["waiting"]["status"] == "paused"
    assert "sibling" in result["outputs"]


class TestDependencyGraph:
    """Test _build_dep_graph and _compute_levels."""

    def test_no_depends_on_sequential(self, workspace):
        """Without depends_on, steps run sequentially (no DAG mode)."""
        wf = {
            "name": "sequential",
            "steps": [
                {"name": "a", "task": "noop"},
                {"name": "b", "task": "noop"},
                {"name": "c", "task": "noop"},
            ],
        }
        result = _run_workflow(wf, workspace)
        # All steps should complete
        assert result is not None

    def test_basic_dag_two_levels(self, workspace):
        """Two independent steps then one dependent step."""
        wf = {
            "name": "basic_dag",
            "steps": [
                {"name": "a", "task": "noop"},
                {"name": "b", "task": "noop"},
                {"name": "c", "task": "noop", "depends_on": ["a", "b"]},
            ],
        }
        result = _run_workflow(wf, workspace)
        assert result is not None

    def test_single_dependency(self, workspace):
        """String form of depends_on (single dep)."""
        wf = {
            "name": "single_dep",
            "steps": [
                {"name": "a", "task": "noop"},
                {"name": "b", "task": "noop", "depends_on": "a"},
            ],
        }
        result = _run_workflow(wf, workspace)
        assert result is not None

    def test_diamond_dag(self, workspace):
        """Diamond pattern: a -> b,c -> d."""
        wf = {
            "name": "diamond",
            "steps": [
                {"name": "a", "task": "noop"},
                {"name": "b", "task": "noop", "depends_on": ["a"]},
                {"name": "c", "task": "noop", "depends_on": ["a"]},
                {"name": "d", "task": "noop", "depends_on": ["b", "c"]},
            ],
        }
        result = _run_workflow(wf, workspace)
        assert result is not None

    def test_missing_dependency_raises(self, workspace):
        """Reference to non-existent step raises ConfigurationError."""
        wf = {
            "name": "missing_dep",
            "steps": [
                {"name": "a", "task": "noop"},
                {"name": "b", "task": "noop", "depends_on": ["nonexistent"]},
            ],
        }
        with pytest.raises((ConfigurationError, WorkflowError)):
            _run_workflow(wf, workspace)

    def test_circular_dependency_raises(self, workspace):
        """Circular dependency raises ConfigurationError."""
        wf = {
            "name": "circular",
            "steps": [
                {"name": "a", "task": "noop", "depends_on": ["b"]},
                {"name": "b", "task": "noop", "depends_on": ["a"]},
            ],
        }
        with pytest.raises((ConfigurationError, WorkflowError)):
            _run_workflow(wf, workspace)


class TestParallelExecution:
    """Test that independent steps actually run in parallel."""

    def test_parallel_steps_complete(self, workspace):
        """Multiple independent steps all produce results."""
        wf = {
            "name": "parallel_results",
            "steps": [
                {"name": "p1", "task": "noop"},
                {"name": "p2", "task": "noop"},
                {"name": "p3", "task": "noop"},
                {"name": "final", "task": "noop", "depends_on": ["p1", "p2", "p3"]},
            ],
        }
        engine = WorkflowEngine(wf, base_dir=str(workspace))
        engine.run()
        # All steps should have results in context
        for name in ["p1", "p2", "p3", "final"]:
            assert name in engine.context["steps"]

    def test_dependent_step_can_access_parent_results(self, workspace):
        """Steps can read results from their dependencies."""
        wf = {
            "name": "access_results",
            "steps": [
                {
                    "name": "producer",
                    "task": "python_code",
                    "inputs": {"code": "result = {'value': 42}"},
                },
                {
                    "name": "consumer",
                    "task": "python_code",
                    "depends_on": ["producer"],
                    "inputs": {
                        "code": 'result = {"got": steps["producer"]["result"]["value"]}'
                    },
                },
            ],
        }
        engine = WorkflowEngine(wf, base_dir=str(workspace))
        engine.run()
        consumer_result = engine.context["steps"]["consumer"]["result"]
        assert consumer_result["got"] == 42


class TestValidatorDependsOn:
    """Test validator checks for depends_on."""

    def _validate(self, tmp_path, content):
        p = tmp_path / "wf.yaml"
        p.write_text(content)
        return WorkflowValidator(str(p)).validate()

    def test_valid_depends_on(self, tmp_path):
        content = "steps:\n  - name: a\n    task: noop\n  - name: b\n    task: noop\n    depends_on: [a]\n"
        result = self._validate(tmp_path, content)
        assert result.is_valid

    def test_missing_dep_reference(self, tmp_path):
        content = "steps:\n  - name: a\n    task: noop\n  - name: b\n    task: noop\n    depends_on: [missing]\n"
        result = self._validate(tmp_path, content)
        assert not result.is_valid
        assert any("missing" in i.message for i in result.errors)

    def test_circular_dep_detected(self, tmp_path):
        content = "steps:\n  - name: a\n    task: noop\n    depends_on: [b]\n  - name: b\n    task: noop\n    depends_on: [a]\n"
        result = self._validate(tmp_path, content)
        assert not result.is_valid
        assert any(
            "circular" in i.message.lower() or "cycle" in i.message.lower()
            for i in result.errors
        )
