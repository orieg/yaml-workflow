"""Tests for MCP server utilities (no mcp dependency required)."""

import pytest
import yaml

from yaml_workflow.mcp_server import _params_to_schema, _scan_workflows


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
