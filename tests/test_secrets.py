"""Tests for the secrets top-level section."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import ConfigurationError
from yaml_workflow.validator import WorkflowValidator

# ---------------------------------------------------------------------------
# Helper: minimal workflow dict with secrets
# ---------------------------------------------------------------------------


def _workflow_with_secrets(secrets):
    """Return a minimal workflow dict that includes a secrets key."""
    wf = {
        "name": "secrets-test",
        "steps": [
            {"name": "noop_step", "task": "noop", "inputs": {"message": "hello"}},
        ],
    }
    if secrets is not None:
        wf["secrets"] = secrets
    return wf


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------


def test_secrets_all_present(tmp_path):
    """When every secret env var is set the workflow initialises without error."""
    wf = _workflow_with_secrets(["MY_SECRET_A", "MY_SECRET_B"])
    with patch.dict(os.environ, {"MY_SECRET_A": "val_a", "MY_SECRET_B": "val_b"}):
        engine = WorkflowEngine(wf, base_dir=str(tmp_path))
        result = engine.run()
        assert result["status"] == "completed"


def test_secrets_missing_raises(tmp_path):
    """Missing env var raises ConfigurationError."""
    wf = _workflow_with_secrets(["MISSING_SECRET_XYZ"])
    env = os.environ.copy()
    env.pop("MISSING_SECRET_XYZ", None)
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ConfigurationError, match="Missing required secrets"):
            WorkflowEngine(wf, base_dir=str(tmp_path))


def test_secrets_empty_list(tmp_path):
    """An empty secrets list should not raise any error."""
    wf = _workflow_with_secrets([])
    engine = WorkflowEngine(wf, base_dir=str(tmp_path))
    result = engine.run()
    assert result["status"] == "completed"


def test_secrets_not_present(tmp_path):
    """No secrets key at all should not raise any error."""
    wf = _workflow_with_secrets(None)  # key omitted entirely
    engine = WorkflowEngine(wf, base_dir=str(tmp_path))
    result = engine.run()
    assert result["status"] == "completed"


def test_secrets_invalid_format(tmp_path):
    """secrets: 'string' (non-list) raises ConfigurationError."""
    wf = _workflow_with_secrets("NOT_A_LIST")
    with pytest.raises(ConfigurationError, match="must be a list"):
        WorkflowEngine(wf, base_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------


def test_validator_secrets_format(tmp_path):
    """Validator catches non-list secrets."""
    wf_path = tmp_path / "bad_secrets.yaml"
    wf_path.write_text(
        yaml.dump(
            {
                "name": "bad-secrets",
                "secrets": "NOT_A_LIST",
                "steps": [
                    {"name": "s1", "task": "noop", "inputs": {"message": "hi"}},
                ],
            }
        )
    )
    validator = WorkflowValidator(wf_path)
    result = validator.validate()
    assert not result.is_valid
    secret_errors = [i for i in result.errors if "secrets" in i.message.lower()]
    assert len(secret_errors) >= 1
