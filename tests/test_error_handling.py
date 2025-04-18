"""
Tests for centralized task error handling utilities.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yaml_workflow.exceptions import TaskExecutionError
from yaml_workflow.tasks.error_handling import ErrorContext, handle_task_error


@pytest.fixture
def mock_logger() -> MagicMock:
    """Fixture to provide a mock logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_task_config() -> dict:
    """Fixture to provide a sample task config dictionary."""
    return {"param1": "value1", "workspace": Path("/tmp/fake_workspace")}


@pytest.fixture
def mock_error_context(mock_task_config) -> ErrorContext:
    """Fixture to provide a basic ErrorContext."""
    return ErrorContext(
        step_name="test_step",
        task_type="test_task",
        error=ValueError("Something went wrong"),
        task_config=mock_task_config,
    )


# --- Test ErrorContext --- #


def test_error_context_creation(mock_task_config):
    """Test basic creation and attribute access of ErrorContext."""
    original_error = ValueError("Original error message")
    context = ErrorContext(
        step_name="step1",
        task_type="file",
        error=original_error,
        retry_count=2,
        task_config=mock_task_config,
        template_context={"var": "val"},
    )
    assert context.step_name == "step1"
    assert context.task_type == "file"
    assert context.error is original_error
    assert context.retry_count == 2
    assert context.task_config == mock_task_config
    assert context.template_context == {"var": "val"}


# --- Test handle_task_error --- #


@patch("yaml_workflow.tasks.error_handling.get_task_logger")
@patch("yaml_workflow.tasks.error_handling.log_task_error")
def test_handle_task_error_wraps_standard_exception(
    mock_log_task_error: MagicMock,
    mock_get_task_logger: MagicMock,
    mock_logger: MagicMock,
    mock_error_context: ErrorContext,
):
    """Test that a standard Exception is wrapped in TaskExecutionError."""
    mock_get_task_logger.return_value = mock_logger
    original_error = mock_error_context.error

    with pytest.raises(TaskExecutionError) as exc_info:
        handle_task_error(mock_error_context)

    # Verify logging calls
    assert mock_error_context.task_config is not None
    mock_get_task_logger.assert_called_once_with(
        mock_error_context.task_config["workspace"], mock_error_context.step_name
    )
    mock_log_task_error.assert_called_once_with(mock_logger, original_error)

    # Verify wrapped exception details
    assert isinstance(exc_info.value, TaskExecutionError)
    assert exc_info.value.step_name == mock_error_context.step_name
    assert exc_info.value.original_error is original_error
    assert exc_info.value.task_config == mock_error_context.task_config
    # Check that the message includes the original error string
    assert str(original_error) in str(exc_info.value)


@patch("yaml_workflow.tasks.error_handling.get_task_logger")
@patch("yaml_workflow.tasks.error_handling.log_task_error")
def test_handle_task_error_reraises_task_execution_error(
    mock_log_task_error: MagicMock,
    mock_get_task_logger: MagicMock,
    mock_logger: MagicMock,
    mock_task_config: dict,
):
    """Test that an existing TaskExecutionError is re-raised directly."""
    mock_get_task_logger.return_value = mock_logger
    original_error = TaskExecutionError(
        step_name="orig_step", original_error=RuntimeError("Inner error")
    )
    context = ErrorContext(
        step_name="test_step_reraise",
        task_type="test_task",
        error=original_error,
        task_config=mock_task_config,
    )

    with pytest.raises(TaskExecutionError) as exc_info:
        handle_task_error(context)

    # Verify logging calls
    mock_get_task_logger.assert_called_once_with(
        mock_task_config["workspace"], context.step_name
    )
    mock_log_task_error.assert_called_once_with(mock_logger, original_error)

    # Verify the *exact* original exception is re-raised
    assert exc_info.value is original_error


@patch("yaml_workflow.tasks.error_handling.get_task_logger")
@patch("yaml_workflow.tasks.error_handling.log_task_error")
def test_handle_task_error_missing_task_config(
    mock_log_task_error: MagicMock,
    mock_get_task_logger: MagicMock,
    mock_logger: MagicMock,
):
    """Test handling when task_config is None."""
    mock_get_task_logger.return_value = mock_logger
    original_error = TypeError("Config missing")
    context = ErrorContext(
        step_name="no_config_step",
        task_type="test_task",
        error=original_error,
        task_config=None,  # Explicitly None
    )

    with pytest.raises(TaskExecutionError) as exc_info:
        handle_task_error(context)

    # Verify logger uses default workspace '.'
    mock_get_task_logger.assert_called_once_with(".", context.step_name)
    mock_log_task_error.assert_called_once_with(mock_logger, original_error)

    # Verify wrapped exception
    assert exc_info.value.step_name == context.step_name
    assert exc_info.value.original_error is original_error
    assert exc_info.value.task_config is None


@patch("yaml_workflow.tasks.error_handling.get_task_logger")
@patch("yaml_workflow.tasks.error_handling.log_task_error")
@patch("yaml_workflow.tasks.error_handling.logging.warning")  # Patch logging.warning
def test_handle_task_error_missing_workspace_in_config(
    mock_logging_warning: MagicMock,
    mock_log_task_error: MagicMock,
    mock_get_task_logger: MagicMock,
    mock_logger: MagicMock,
):
    """Test handling when task_config exists but lacks 'workspace' key."""
    mock_get_task_logger.return_value = mock_logger
    original_error = KeyError("Missing key")
    # Config without 'workspace'
    task_config_no_workspace = {"param1": "value1"}
    context = ErrorContext(
        step_name="no_workspace_step",
        task_type="test_task",
        error=original_error,
        task_config=task_config_no_workspace,
    )

    with pytest.raises(TaskExecutionError) as exc_info:
        handle_task_error(context)

    # Verify logger uses default workspace '.'
    mock_get_task_logger.assert_called_once_with(".", context.step_name)
    # Verify the warning was logged
    mock_logging_warning.assert_called_once()
    assert "Invalid or missing 'workspace'" in mock_logging_warning.call_args[0][0]
    assert context.step_name in mock_logging_warning.call_args[0][0]

    mock_log_task_error.assert_called_once_with(mock_logger, original_error)

    # Verify wrapped exception
    assert exc_info.value.step_name == context.step_name
    assert exc_info.value.original_error is original_error
    assert exc_info.value.task_config == task_config_no_workspace
