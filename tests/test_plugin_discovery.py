"""Tests for plugin discovery via Python entry points."""

import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from yaml_workflow.tasks import (
    TaskConfig,
    _discover_plugins,
    get_task_handler,
    register_task,
)


def test_discover_plugins_no_plugins():
    """Test _discover_plugins runs without error when no plugins are installed."""
    # With no external plugins registered, this should complete silently
    _discover_plugins()


def test_discover_plugins_loads_entry_point():
    """Test that a plugin entry point is loaded and its task becomes available."""

    def fake_load():
        @register_task("plugin_task")
        def plugin_task(config: TaskConfig) -> Dict[str, Any]:
            return {"result": "from plugin"}

    mock_ep = MagicMock()
    mock_ep.name = "plugin_task"
    mock_ep.load = fake_load

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        _discover_plugins()

    handler = get_task_handler("plugin_task")
    assert handler is not None


def test_discover_plugins_handles_import_error(caplog):
    """Test that a failing plugin logs a warning but does not crash."""
    mock_ep = MagicMock()
    mock_ep.name = "bad_plugin"
    mock_ep.load.side_effect = ImportError("missing dependency")

    with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        with caplog.at_level(logging.WARNING):
            _discover_plugins()

    assert any(
        "Failed to load task plugin 'bad_plugin'" in msg for msg in caplog.messages
    )


def test_discover_plugins_fallback_for_old_python():
    """Test the fallback path for Python < 3.10 entry_points API."""

    def fake_load():
        @register_task("fallback_plugin_task")
        def fallback_task(config: TaskConfig) -> Dict[str, Any]:
            return {"result": "fallback"}

    mock_ep = MagicMock()
    mock_ep.name = "fallback_plugin_task"
    mock_ep.load = fake_load

    def entry_points_raises(**kwargs):
        if "group" in kwargs:
            raise TypeError("entry_points() got an unexpected keyword argument 'group'")
        return {"yaml_workflow.tasks": [mock_ep]}

    with patch("importlib.metadata.entry_points", side_effect=entry_points_raises):
        _discover_plugins()

    handler = get_task_handler("fallback_plugin_task")
    assert handler is not None


def test_plugin_registered_task_accessible(temp_workspace):
    """Test that a plugin-registered task is accessible via get_task_handler and works."""

    @register_task("ext_plugin_task")
    def ext_plugin_task(config: TaskConfig) -> Dict[str, Any]:
        processed = config.process_inputs()
        return {"output": f"plugin says {processed.get('msg', 'hi')}"}

    handler = get_task_handler("ext_plugin_task")
    assert handler is not None

    step = {
        "name": "test_ext",
        "task": "ext_plugin_task",
        "inputs": {"msg": "hello"},
    }
    config = TaskConfig(step, {}, temp_workspace)
    result = handler(config)
    assert result["output"] == "plugin says hello"
