"""Tests that the JSON Schema validates all example workflows and catches invalid ones."""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "workflow-schema.json"
EXAMPLES_DIR = Path(__file__).parent.parent / "src" / "yaml_workflow" / "examples"


@pytest.fixture(scope="module")
def schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _example_files():
    return sorted(EXAMPLES_DIR.glob("*.yaml"))


# ---------------------------------------------------------------------------
# All example workflows must pass schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("workflow_file", _example_files(), ids=lambda p: p.name)
def test_example_validates_against_schema(schema, workflow_file):
    """Each example workflow must be valid per the JSON Schema."""
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)
    jsonschema.validate(instance=workflow, schema=schema)


# ---------------------------------------------------------------------------
# Schema rejects invalid workflows
# ---------------------------------------------------------------------------


def test_schema_rejects_unknown_top_level_key(schema):
    """Schema has additionalProperties: false — unknown keys should fail."""
    bad = {"name": "test", "steps": [{"name": "s", "task": "noop"}], "bogus_key": True}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


def test_schema_rejects_step_without_name(schema):
    """Steps require a name field."""
    bad = {"steps": [{"task": "noop"}]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


def test_schema_rejects_step_without_task(schema):
    """Steps require a task field."""
    bad = {"steps": [{"name": "s"}]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


# ---------------------------------------------------------------------------
# Schema accepts v0.8 features
# ---------------------------------------------------------------------------


def test_schema_accepts_depends_on_array(schema):
    """depends_on as an array of strings should be accepted."""
    wf = {
        "name": "dag",
        "steps": [
            {"name": "a", "task": "noop"},
            {"name": "b", "task": "noop", "depends_on": ["a"]},
        ],
    }
    jsonschema.validate(instance=wf, schema=schema)


def test_schema_accepts_depends_on_string(schema):
    """depends_on as a single string should be accepted."""
    wf = {
        "name": "dag",
        "steps": [
            {"name": "a", "task": "noop"},
            {"name": "b", "task": "noop", "depends_on": "a"},
        ],
    }
    jsonschema.validate(instance=wf, schema=schema)


def test_schema_accepts_secrets(schema):
    """The secrets top-level field should be accepted."""
    wf = {
        "name": "with secrets",
        "secrets": ["API_KEY", "DB_PASS"],
        "steps": [{"name": "s", "task": "noop"}],
    }
    jsonschema.validate(instance=wf, schema=schema)


def test_schema_accepts_notify_task(schema):
    """The notify task type should be accepted."""
    wf = {
        "steps": [
            {
                "name": "alert",
                "task": "notify",
                "inputs": {"channel": "log", "message": "done"},
            }
        ],
    }
    jsonschema.validate(instance=wf, schema=schema)


def test_schema_accepts_settings(schema):
    """The settings section should be accepted."""
    wf = {
        "name": "with settings",
        "settings": {"max_workers": 8, "log_level": "DEBUG"},
        "steps": [{"name": "s", "task": "noop"}],
    }
    jsonschema.validate(instance=wf, schema=schema)


def test_schema_accepts_flows(schema):
    """The flows section should be accepted."""
    wf = {
        "name": "with flows",
        "steps": [
            {"name": "a", "task": "noop"},
            {"name": "b", "task": "noop"},
        ],
        "flows": {
            "main": {"steps": ["a", "b"]},
        },
    }
    jsonschema.validate(instance=wf, schema=schema)
