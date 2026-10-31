"""Tests for MCP server utilities (no mcp dependency required)."""

import pytest
import yaml

from yaml_workflow.exceptions import WorkflowError
from yaml_workflow.mcp_server import (
    _execute_workflow,
    _params_to_schema,
    _resolve_workflow,
    _scan_workflows,
    _tool_name,
    _validate_workflow,
)
from yaml_workflow.tasks import register_task


def _write_wf(path, body):
    path.write_text(body)
    return str(path)


class TestScanWorkflows:
    def test_finds_valid_workflows(self, tmp_path):
        wf = tmp_path / "test.yaml"
        wf.write_text("name: Test\nsteps:\n  - name: s1\n    task: noop\n")

        result = _scan_workflows(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "Test"

    def test_skips_non_workflow_yaml(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("database:\n  host: localhost\n")

        result = _scan_workflows(str(tmp_path))
        assert len(result) == 0

    def test_empty_directory(self, tmp_path):
        result = _scan_workflows(str(tmp_path))
        assert result == []

    def test_nonexistent_directory(self):
        result = _scan_workflows("/nonexistent/path")
        assert result == []

    def test_extracts_params(self, tmp_path):
        wf = tmp_path / "test.yaml"
        wf.write_text(
            "name: Test\nparams:\n  name:\n    type: string\n    default: World\nsteps:\n  - name: s\n    task: noop\n"
        )

        result = _scan_workflows(str(tmp_path))
        assert "name" in result[0]["params"]


class TestParamsToSchema:
    def test_empty_params(self):
        schema = _params_to_schema({})
        assert schema["type"] == "object"
        assert schema["properties"] == {}

    def test_string_param(self):
        schema = _params_to_schema(
            {"name": {"type": "string", "description": "User name", "default": "World"}}
        )
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["name"]["default"] == "World"

    def test_integer_param(self):
        schema = _params_to_schema({"count": {"type": "integer"}})
        assert schema["properties"]["count"]["type"] == "integer"

    def test_required_params(self):
        schema = _params_to_schema({"name": {"type": "string", "required": True}})
        assert "name" in schema.get("required", [])

    def test_simple_value_form(self):
        schema = _params_to_schema({"name": "default_value"})
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["name"]["default"] == "default_value"


_RUNNABLE_WF = (
    "name: Greeter\n"
    "description: Says hi\n"
    "params:\n"
    "  who:\n"
    "    type: string\n"
    "    default: World\n"
    "steps:\n"
    "  - name: compute\n"
    "    task: python_code\n"
    "    inputs:\n"
    "      code: |\n"
    '        result = "hi"\n'
)


class TestToolName:
    def test_snake_case(self):
        assert _tool_name("Data Pipeline") == "data_pipeline"
        assert _tool_name("ai-changelog") == "ai_changelog"


class TestResolveWorkflow:
    def test_resolve_by_path(self, tmp_path):
        p = _write_wf(tmp_path / "w.yaml", _RUNNABLE_WF)
        assert _resolve_workflow(p, str(tmp_path)) == p

    def test_resolve_by_name(self, tmp_path):
        p = _write_wf(tmp_path / "w.yaml", _RUNNABLE_WF)
        assert _resolve_workflow("Greeter", str(tmp_path)) == p
        assert _resolve_workflow("greeter", str(tmp_path)) == p

    def test_resolve_not_found(self, tmp_path):
        assert _resolve_workflow("nope", str(tmp_path)) is None
        assert _resolve_workflow("", str(tmp_path)) is None


class TestValidateWorkflow:
    def test_valid(self, tmp_path):
        p = _write_wf(tmp_path / "w.yaml", _RUNNABLE_WF)
        result = _validate_workflow(p)
        assert result["valid"] is True
        assert result["error_count"] == 0

    def test_invalid(self, tmp_path):
        p = _write_wf(tmp_path / "bad.yaml", "name: Bad\nsteps: not-a-list\n")
        result = _validate_workflow(p)
        assert result["valid"] is False
        assert result["error_count"] >= 1


class TestExecuteWorkflow:
    def test_run_returns_outputs(self, tmp_path):
        p = _write_wf(tmp_path / "w.yaml", _RUNNABLE_WF)
        result = _execute_workflow(
            p, {}, base_dir=str(tmp_path / "runs"), dry_run=False
        )
        assert result["status"] in ("completed", "success")
        assert result["outputs"]["compute"] == "hi"
        assert "preview" not in result

    def test_dry_run_previews_without_executing(self, tmp_path):
        p = _write_wf(tmp_path / "w.yaml", _RUNNABLE_WF)
        result = _execute_workflow(p, {}, base_dir=str(tmp_path / "runs"), dry_run=True)
        assert "preview" in result
        assert "DRY-RUN" in result["preview"]

    @pytest.mark.parametrize("resumable", [False, True])
    def test_resume_preserves_outputs_and_parameters(self, tmp_path, resumable):
        calls = []

        @register_task("mcp_resume_input")
        def task(value: str) -> str:
            calls.append(value)
            return value

        workflow = {
            "params": {"greeting": {"default": "default"}},
            "steps": [
                {
                    "name": "before",
                    "task": "mcp_resume_input",
                    "inputs": {"value": "{{ args.greeting }}"},
                },
                {
                    "name": "waiting",
                    "task": "mcp_resume_input",
                    "resumable": resumable,
                    "on_error": {"retry": 0},
                },
                {
                    "name": "after",
                    "task": "mcp_resume_input",
                    "inputs": {
                        "value": "{{ steps.before.result }} / {{ steps.waiting.result }} / {{ args.greeting }}"
                    },
                },
            ],
        }
        path = tmp_path / "workflow.yaml"
        path.write_text(yaml.safe_dump(workflow))
        workspace = str(tmp_path / "workspace")
        kwargs = {
            "base_dir": str(tmp_path / "runs"),
            "dry_run": False,
            "workspace": workspace,
        }
        if resumable:
            result = _execute_workflow(str(path), {"greeting": "saved"}, **kwargs)
            assert result["status"] == "paused"
            assert result["workspace"] == workspace
            assert result["outputs"] == {"before": "saved"}
            assert result["paused_steps"]["waiting"]["missing_input"] == "value"
            again = _execute_workflow(str(path), None, resume_from="waiting", **kwargs)
            assert again["status"] == "paused"
        else:
            with pytest.raises(
                WorkflowError, match="Missing required parameter: value"
            ):
                _execute_workflow(str(path), {"greeting": "saved"}, **kwargs)
        assert calls == ["saved"]

        result = _execute_workflow(
            str(path), {"value": "answer"}, resume_from="waiting", **kwargs
        )
        assert result["status"] == "completed"
        assert result["workspace"] == workspace
        assert "paused_steps" not in result
        assert result["outputs"]["after"] == "saved / answer / saved"
        assert calls == ["saved", "answer", "saved / answer / saved"]

    @pytest.mark.parametrize("workspace", [None, "missing"])
    def test_resume_requires_existing_workspace(self, tmp_path, workspace):
        with pytest.raises(ValueError, match="existing workspace"):
            _execute_workflow(
                "unused.yaml",
                None,
                base_dir=str(tmp_path / "runs"),
                dry_run=False,
                workspace=str(tmp_path / workspace) if workspace else None,
                resume_from="waiting",
            )
        assert not (tmp_path / "runs").exists()

    def test_resume_dry_run_does_not_modify_workspace(self, tmp_path):
        metadata = tmp_path / ".workflow_metadata.json"
        metadata.write_text('{"unchanged": true}')
        with pytest.raises(ValueError, match="dry run"):
            _execute_workflow(
                "unused.yaml",
                None,
                base_dir=str(tmp_path / "runs"),
                dry_run=True,
                workspace=str(tmp_path),
                resume_from="waiting",
            )
        assert metadata.read_text() == '{"unchanged": true}'
