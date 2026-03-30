"""Tests for the notify task."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaml_workflow.tasks.notify_tasks import notify_task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(inputs: dict, workspace=None, name="notify_step", task_type="notify"):
    """Build a minimal TaskConfig-like mock for notify_task."""
    cfg = MagicMock()
    cfg.name = name
    cfg.type = task_type
    cfg.workspace = Path(workspace) if workspace else Path(".")
    cfg.step = {"name": name, "task": task_type}
    cfg.context = {"workflow": {"name": "test_workflow"}}
    cfg.process_inputs.return_value = inputs
    return cfg


# ---------------------------------------------------------------------------
# log channel
# ---------------------------------------------------------------------------


def test_notify_log_info(tmp_path):
    cfg = _make_config({"channel": "log", "message": "hello log"}, workspace=tmp_path)
    result = notify_task(cfg)
    assert result["channel"] == "log"
    assert result["status"] == "sent"
    assert result["message"] == "hello log"


def test_notify_log_to_file(tmp_path):
    log_file = str(tmp_path / "out.log")
    cfg = _make_config(
        {"channel": "log", "message": "log to file", "file": log_file},
        workspace=tmp_path,
    )
    notify_task(cfg)
    content = Path(log_file).read_text()
    assert "log to file" in content


def test_notify_log_levels(tmp_path):
    for level in ("debug", "info", "warning", "error"):
        cfg = _make_config(
            {"channel": "log", "message": f"msg at {level}", "level": level},
            workspace=tmp_path,
        )
        result = notify_task(cfg)
        assert result["status"] == "sent"


# ---------------------------------------------------------------------------
# file channel
# ---------------------------------------------------------------------------


def test_notify_file_jsonl(tmp_path):
    dest = str(tmp_path / "notifications.jsonl")
    cfg = _make_config(
        {"channel": "file", "file": dest, "message": "file test", "format": "jsonl"},
        workspace=tmp_path,
    )
    notify_task(cfg)
    lines = Path(dest).read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["message"] == "file test"
    assert "timestamp" in record


def test_notify_file_text_format(tmp_path):
    dest = str(tmp_path / "notifications.txt")
    cfg = _make_config(
        {"channel": "file", "file": dest, "message": "text msg", "format": "text"},
        workspace=tmp_path,
    )
    notify_task(cfg)
    content = Path(dest).read_text()
    assert "text msg" in content


def test_notify_file_append(tmp_path):
    dest = str(tmp_path / "multi.jsonl")
    for msg in ("first", "second", "third"):
        cfg = _make_config(
            {"channel": "file", "file": dest, "message": msg, "append": True},
            workspace=tmp_path,
        )
        notify_task(cfg)
    lines = Path(dest).read_text().strip().splitlines()
    assert len(lines) == 3


def test_notify_file_overwrite(tmp_path):
    dest = str(tmp_path / "overwrite.jsonl")
    for msg in ("first", "second"):
        cfg = _make_config(
            {"channel": "file", "file": dest, "message": msg, "append": False},
            workspace=tmp_path,
        )
        notify_task(cfg)
    lines = Path(dest).read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["message"] == "second"


# ---------------------------------------------------------------------------
# webhook channel
# ---------------------------------------------------------------------------


def test_notify_webhook_success(tmp_path):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"ok"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch(
        "yaml_workflow.tasks.notify_tasks.urllib.request.urlopen",
        return_value=mock_response,
    ):
        cfg = _make_config(
            {
                "channel": "webhook",
                "url": "https://example.com/hook",
                "message": "done",
            },
            workspace=tmp_path,
        )
        result = notify_task(cfg)
    assert result["status"] == "sent"
    assert result["status_code"] == 200


def test_notify_webhook_missing_url(tmp_path):
    from yaml_workflow.exceptions import TaskExecutionError

    cfg = _make_config({"channel": "webhook", "message": "no url"}, workspace=tmp_path)
    with pytest.raises(TaskExecutionError):
        notify_task(cfg)


# ---------------------------------------------------------------------------
# slack channel
# ---------------------------------------------------------------------------


def test_notify_slack_success(tmp_path):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"ok"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch(
        "yaml_workflow.tasks.notify_tasks.urllib.request.urlopen",
        return_value=mock_response,
    ):
        cfg = _make_config(
            {
                "channel": "slack",
                "webhook_url": "https://hooks.slack.com/xxx",
                "message": "slack test",
            },
            workspace=tmp_path,
        )
        result = notify_task(cfg)
    assert result["status"] == "sent"


def test_notify_slack_missing_webhook_url(tmp_path):
    from yaml_workflow.exceptions import TaskExecutionError

    cfg = _make_config({"channel": "slack", "message": "oops"}, workspace=tmp_path)
    with pytest.raises(TaskExecutionError):
        notify_task(cfg)


# ---------------------------------------------------------------------------
# Unknown channel
# ---------------------------------------------------------------------------


def test_notify_unknown_channel(tmp_path):
    from yaml_workflow.exceptions import TaskExecutionError

    cfg = _make_config(
        {"channel": "carrier_pigeon", "message": "coo"}, workspace=tmp_path
    )
    with pytest.raises(TaskExecutionError):
        notify_task(cfg)


def test_notify_missing_channel(tmp_path):
    from yaml_workflow.exceptions import TaskExecutionError

    cfg = _make_config({"message": "no channel"}, workspace=tmp_path)
    with pytest.raises(TaskExecutionError):
        notify_task(cfg)
