"""Tests for the WorkflowValidator (validator.py)."""

import json

import pytest
import yaml

from yaml_workflow.validator import ValidationResult, WorkflowValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_workflow(tmp_path, content: str) -> str:
    p = tmp_path / "workflow.yaml"
    p.write_text(content)
    return str(p)


def _valid_workflow() -> str:
    return """
name: Test Workflow
params:
  name:
    type: string
    default: World
steps:
  - name: greet
    task: shell
    inputs:
      command: echo hello
  - name: done
    task: noop
"""


# ---------------------------------------------------------------------------
# Basic happy-path
# ---------------------------------------------------------------------------


def test_valid_workflow_passes(tmp_path):
    path = _write_workflow(tmp_path, _valid_workflow())
    v = WorkflowValidator(path)
    result = v.validate()
    assert result.is_valid
    assert len(result.errors) == 0


def test_valid_workflow_no_warnings(tmp_path):
    path = _write_workflow(tmp_path, _valid_workflow())
    result = WorkflowValidator(path).validate()
    assert len(result.warnings) == 0


# ---------------------------------------------------------------------------
# File errors
# ---------------------------------------------------------------------------


def test_file_not_found():
    result = WorkflowValidator("/nonexistent/workflow.yaml").validate()
    assert not result.is_valid
    assert any("not found" in i.message.lower() for i in result.errors)


def test_invalid_yaml_syntax(tmp_path):
    path = _write_workflow(tmp_path, "steps: [\n  unclosed")
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("YAML syntax" in i.message for i in result.errors)


# ---------------------------------------------------------------------------
# Structure checks
# ---------------------------------------------------------------------------


def test_missing_steps_and_flows(tmp_path):
    path = _write_workflow(tmp_path, "name: NoSteps\n")
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("steps" in i.message for i in result.errors)


def test_unknown_top_level_key(tmp_path):
    content = "steps:\n  - name: s\n    task: noop\nbadkey: value\n"
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("badkey" in i.message for i in result.errors)


def test_step_missing_task(tmp_path):
    content = "steps:\n  - name: no_task\n"
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("task" in i.message for i in result.errors)


def test_step_missing_name(tmp_path):
    content = "steps:\n  - task: noop\n"
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("name" in i.message for i in result.errors)


# ---------------------------------------------------------------------------
# Unique step names
# ---------------------------------------------------------------------------


def test_duplicate_step_names(tmp_path):
    content = (
        "steps:\n" "  - name: dup\n    task: noop\n" "  - name: dup\n    task: noop\n"
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("Duplicate" in i.message for i in result.errors)


# ---------------------------------------------------------------------------
# Task type checks (warnings, not errors)
# ---------------------------------------------------------------------------


def test_builtin_task_no_warning(tmp_path):
    content = "steps:\n  - name: s\n    task: shell\n"
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not any("unknown task type" in i.message for i in result.warnings)


def test_unknown_task_type_is_warning(tmp_path):
    content = "steps:\n  - name: s\n    task: my_plugin.custom\n"
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert result.is_valid  # warnings don't make it invalid
    assert any("unknown task type" in i.message for i in result.warnings)


# ---------------------------------------------------------------------------
# Flow reference checks
# ---------------------------------------------------------------------------


def test_flow_references_valid_steps(tmp_path):
    content = (
        "steps:\n  - name: a\n    task: noop\n  - name: b\n    task: noop\n"
        "flows:\n  main:\n    steps: [a, b]\n"
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert result.is_valid


def test_flow_references_missing_step(tmp_path):
    content = (
        "steps:\n  - name: a\n    task: noop\n"
        "flows:\n  main:\n    steps: [a, ghost]\n"
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not result.is_valid
    assert any("ghost" in i.message for i in result.errors)


# ---------------------------------------------------------------------------
# Param reference check
# ---------------------------------------------------------------------------


def test_undeclared_param_reference_is_warning(tmp_path):
    content = (
        "steps:\n"
        "  - name: s\n    task: shell\n"
        "    inputs:\n      command: echo {{ args.undeclared_param }}\n"
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert result.is_valid  # only a warning
    assert any("undeclared_param" in i.message for i in result.warnings)


def test_declared_param_no_warning(tmp_path):
    content = (
        "params:\n  my_name:\n    type: string\n"
        "steps:\n"
        "  - name: s\n    task: shell\n"
        "    inputs:\n      command: echo {{ args.my_name }}\n"
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not any("my_name" in i.message for i in result.warnings)


# ---------------------------------------------------------------------------
# Double result access pattern
# ---------------------------------------------------------------------------


def test_double_result_access_warning(tmp_path):
    # Use YAML quoted strings to avoid `{{ }}` being parsed as YAML flow mappings
    content = (
        "steps:\n"
        "  - name: producer\n    task: python_code\n"
        "    inputs:\n      code: 'result = 1'\n"
        "  - name: consumer\n    task: shell\n"
        '    inputs:\n      command: "echo {{ steps.producer.result.result.x }}"\n'
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert any("double result" in i.message.lower() for i in result.warnings)
    assert any(
        i.hint and "steps.STEP_NAME.result.KEY" in i.hint for i in result.warnings
    )


def test_correct_result_access_no_warning(tmp_path):
    content = (
        "steps:\n"
        "  - name: producer\n    task: python_code\n"
        "    inputs:\n      code: 'result = 1'\n"
        "  - name: consumer\n    task: shell\n"
        '    inputs:\n      command: "echo {{ steps.producer.result.x }}"\n'
    )
    path = _write_workflow(tmp_path, content)
    result = WorkflowValidator(path).validate()
    assert not any("double result" in i.message.lower() for i in result.warnings)


# ---------------------------------------------------------------------------
# to_dict / JSON serialisation
# ---------------------------------------------------------------------------


def test_to_dict_structure(tmp_path):
    path = _write_workflow(tmp_path, _valid_workflow())
    result = WorkflowValidator(path).validate()
    d = result.to_dict()
    assert d["valid"] is True
    assert d["error_count"] == 0
    assert isinstance(d["issues"], list)


def test_to_dict_roundtrip(tmp_path):
    """ValidationResult.to_dict() should be JSON-serialisable."""
    path = _write_workflow(tmp_path, _valid_workflow())
    result = WorkflowValidator(path).validate()
    serialised = json.dumps(result.to_dict())
    parsed = json.loads(serialised)
    assert parsed["valid"] is True
