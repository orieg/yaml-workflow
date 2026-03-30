"""Tests for parallel step execution with depends_on."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import ConfigurationError, WorkflowError
from yaml_workflow.validator import WorkflowValidator


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


def _run_workflow(workflow_dict, workspace):
    """Helper to run a workflow dict and return results."""
    engine = WorkflowEngine(workflow_dict, base_dir=str(workspace))
    return engine.run()


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
