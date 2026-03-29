"""Tests for workflow composition / imports."""

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import CircularImportError, WorkflowImportError


def _write_yaml(path, data):
    path.write_text(yaml.dump(data, default_flow_style=False))


class TestBasicImport:
    def test_import_merges_steps(self, tmp_path):
        """Imported steps appear before main steps."""
        shared = tmp_path / "shared.yaml"
        _write_yaml(
            shared,
            {
                "name": "Shared",
                "steps": [
                    {
                        "name": "shared_step",
                        "task": "echo",
                        "inputs": {"message": "ok"},
                    },
                ],
            },
        )

        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Main",
                "imports": ["shared.yaml"],
                "steps": [
                    {"name": "main_step", "task": "echo", "inputs": {"message": "ok"}},
                ],
            },
        )

        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        step_names = [s["name"] for s in engine.workflow["steps"]]
        assert step_names == ["shared_step", "main_step"]

    def test_import_merges_params(self, tmp_path):
        """Imported params provide defaults, main overrides."""
        shared = tmp_path / "shared.yaml"
        _write_yaml(
            shared,
            {
                "name": "Shared",
                "params": {
                    "shared_param": {"default": "from_shared"},
                    "override_me": {"default": "shared_value"},
                },
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )

        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Main",
                "imports": ["shared.yaml"],
                "params": {
                    "override_me": {"default": "main_value"},
                },
                "steps": [{"name": "s2", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )

        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        assert engine.workflow["params"]["shared_param"]["default"] == "from_shared"
        assert engine.workflow["params"]["override_me"]["default"] == "main_value"

    def test_imported_files_tracked(self, tmp_path):
        """Engine tracks imported file paths for watch mode."""
        shared = tmp_path / "shared.yaml"
        _write_yaml(
            shared,
            {
                "name": "Shared",
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )

        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Main",
                "imports": ["shared.yaml"],
                "steps": [{"name": "s2", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )

        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        assert len(engine.imported_files) == 1
        assert engine.imported_files[0] == shared.resolve()


class TestImportExecution:
    def test_workflow_with_import_runs(self, tmp_path):
        """A workflow with imports executes successfully."""
        shared = tmp_path / "shared.yaml"
        _write_yaml(
            shared,
            {
                "steps": [
                    {
                        "name": "imported_step",
                        "task": "echo",
                        "inputs": {"message": "ok"},
                    }
                ]
            },
        )

        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "With Import",
                "imports": ["shared.yaml"],
                "steps": [
                    {"name": "local_step", "task": "echo", "inputs": {"message": "ok"}}
                ],
            },
        )

        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        result = engine.run()
        assert result["status"] == "completed"


class TestTransitiveImports:
    def test_transitive_import(self, tmp_path):
        """A imports B, B imports C — all steps present."""
        c = tmp_path / "c.yaml"
        _write_yaml(
            c,
            {
                "steps": [
                    {"name": "step_c", "task": "echo", "inputs": {"message": "ok"}}
                ]
            },
        )

        b = tmp_path / "b.yaml"
        _write_yaml(
            b,
            {
                "imports": ["c.yaml"],
                "steps": [
                    {"name": "step_b", "task": "echo", "inputs": {"message": "ok"}}
                ],
            },
        )

        a = tmp_path / "a.yaml"
        _write_yaml(
            a,
            {
                "name": "Transitive",
                "imports": ["b.yaml"],
                "steps": [
                    {"name": "step_a", "task": "echo", "inputs": {"message": "ok"}}
                ],
            },
        )

        engine = WorkflowEngine(str(a), base_dir=str(tmp_path / "runs"))
        step_names = [s["name"] for s in engine.workflow["steps"]]
        assert "step_c" in step_names
        assert "step_b" in step_names
        assert "step_a" in step_names
        # Imported files should include both b.yaml and c.yaml
        assert len(engine.imported_files) == 2


class TestImportErrors:
    def test_missing_import_file(self, tmp_path):
        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Missing",
                "imports": ["nonexistent.yaml"],
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )
        with pytest.raises(WorkflowImportError, match="File not found"):
            WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))

    def test_circular_import(self, tmp_path):
        a = tmp_path / "a.yaml"
        b = tmp_path / "b.yaml"
        _write_yaml(
            a,
            {
                "name": "A",
                "imports": ["b.yaml"],
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )
        _write_yaml(
            b,
            {
                "imports": ["a.yaml"],
                "steps": [{"name": "s2", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )
        with pytest.raises(CircularImportError, match="Circular import"):
            WorkflowEngine(str(a), base_dir=str(tmp_path / "runs"))

    def test_import_in_dict_workflow(self, tmp_path):
        """Imports not supported for dict-based workflows."""
        workflow = {
            "name": "Dict",
            "imports": ["shared.yaml"],
            "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
        }
        with pytest.raises(WorkflowImportError, match="file-based"):
            WorkflowEngine(workflow, base_dir=str(tmp_path / "runs"))

    def test_invalid_yaml_import(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(": : : invalid yaml [[[")
        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Bad",
                "imports": ["bad.yaml"],
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )
        with pytest.raises(WorkflowImportError, match="Invalid YAML"):
            WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))

    def test_no_imports_produces_empty_list(self, tmp_path):
        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "No Imports",
                "steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )
        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        assert engine.imported_files == []


class TestImportDictFormat:
    def test_import_with_path_dict(self, tmp_path):
        """Support dict format: {path: ./shared.yaml}."""
        shared = tmp_path / "shared.yaml"
        _write_yaml(
            shared,
            {"steps": [{"name": "s1", "task": "echo", "inputs": {"message": "ok"}}]},
        )

        main = tmp_path / "main.yaml"
        _write_yaml(
            main,
            {
                "name": "Dict Format",
                "imports": [{"path": "shared.yaml"}],
                "steps": [{"name": "s2", "task": "echo", "inputs": {"message": "ok"}}],
            },
        )

        engine = WorkflowEngine(str(main), base_dir=str(tmp_path / "runs"))
        step_names = [s["name"] for s in engine.workflow["steps"]]
        assert "s1" in step_names
        assert "s2" in step_names
