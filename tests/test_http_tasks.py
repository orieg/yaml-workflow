"""Tests for HTTP request task implementation."""

import json
import socket
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from yaml_workflow.exceptions import TaskExecutionError
from yaml_workflow.tasks import TaskConfig
from yaml_workflow.tasks.http_tasks import http_request_task


@pytest.fixture
def workspace(tmp_path) -> Path:
    """Create a temporary workspace for testing."""
    return tmp_path


@pytest.fixture
def basic_context() -> Dict[str, Any]:
    """Create a basic context with namespaces."""
    return {
        "args": {"api_key": "test-key-123"},
        "env": {"base_url": "https://api.example.com"},
        "steps": {},
    }


def _make_mock_response(
    body: str = "",
    status: int = 200,
    headers: Dict[str, str] = None,
) -> MagicMock:
    """Create a mock HTTP response object."""
    mock_response = MagicMock()
    mock_response.read.return_value = body.encode("utf-8")
    mock_response.status = status

    # Build an http.client.HTTPMessage-like headers object
    from email.message import Message

    msg = Message()
    if headers:
        for key, value in headers.items():
            msg[key] = value
    mock_response.headers = msg
    # Make dict(response.headers) work correctly
    mock_response.headers.items = msg.items
    mock_response.headers.keys = msg.keys
    mock_response.headers.__iter__ = msg.__iter__
    mock_response.headers.__getitem__ = msg.__getitem__

    # Support context manager usage
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestHttpRequestBasicGet:
    """Tests for basic GET request functionality."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_basic_get_request(self, mock_urlopen, workspace, basic_context):
        """Test a simple GET request returns expected result."""
        mock_urlopen.return_value = _make_mock_response(
            body='{"message": "hello"}',
            status=200,
            headers={"Content-Type": "application/json"},
        )

        step = {
            "name": "test_get",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/data"},
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["status_code"] == 200
        assert result["body"] == '{"message": "hello"}'
        assert result["json"] == {"message": "hello"}

        # Verify the request was made correctly
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://api.example.com/data"
        assert req.method == "GET"

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_get_with_default_method(self, mock_urlopen, workspace, basic_context):
        """Test that method defaults to GET when not specified."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_default_method",
            "task": "http.request",
            "inputs": {"url": "https://example.com"},
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.method == "GET"
        assert result["status_code"] == 200


class TestHttpRequestPost:
    """Tests for POST request with JSON body."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_post_with_json_body(self, mock_urlopen, workspace, basic_context):
        """Test POST request with a dict body is JSON-encoded."""
        mock_urlopen.return_value = _make_mock_response(
            body='{"id": 1, "created": true}',
            status=201,
            headers={"Content-Type": "application/json"},
        )

        step = {
            "name": "test_post",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/items",
                "method": "POST",
                "body": {"name": "test-item", "value": 42},
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["status_code"] == 201
        assert result["json"]["created"] is True

        # Verify request body and headers
        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        assert req.get_header("Content-type") == "application/json"
        sent_data = json.loads(req.data.decode("utf-8"))
        assert sent_data == {"name": "test-item", "value": 42}

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_post_with_string_body(self, mock_urlopen, workspace, basic_context):
        """Test POST request with a string body."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_post_string",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/raw",
                "method": "POST",
                "body": "raw string body",
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.data == b"raw string body"

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_post_dict_body_does_not_override_explicit_content_type(
        self, mock_urlopen, workspace, basic_context
    ):
        """Test that explicit Content-Type is preserved when body is a dict."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_explicit_ct",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/items",
                "method": "POST",
                "body": {"key": "value"},
                "headers": {"Content-Type": "application/vnd.api+json"},
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/vnd.api+json"


class TestHttpRequestHeaders:
    """Tests for custom headers."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_custom_headers(self, mock_urlopen, workspace, basic_context):
        """Test that custom headers are sent with the request."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_headers",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/secure",
                "headers": {
                    "Authorization": "Bearer token123",
                    "X-Custom-Header": "custom-value",
                },
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer token123"
        assert req.get_header("X-custom-header") == "custom-value"


class TestHttpRequestTimeout:
    """Tests for timeout parameter."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_timeout_parameter(self, mock_urlopen, workspace, basic_context):
        """Test that timeout is passed to urlopen."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_timeout",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/slow",
                "timeout": 60,
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        http_request_task(config)

        call_kwargs = mock_urlopen.call_args
        assert call_kwargs[1]["timeout"] == 60

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_default_timeout(self, mock_urlopen, workspace, basic_context):
        """Test that default timeout of 30 is used."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_default_timeout",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/data"},
        }

        config = TaskConfig(step, basic_context, workspace)
        http_request_task(config)

        call_kwargs = mock_urlopen.call_args
        assert call_kwargs[1]["timeout"] == 30

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_socket_timeout_error(self, mock_urlopen, workspace, basic_context):
        """Test that socket timeout is caught and wrapped."""
        mock_urlopen.side_effect = socket.timeout("Connection timed out")

        step = {
            "name": "test_socket_timeout",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/slow",
                "timeout": 1,
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert isinstance(exc_info.value.original_error, socket.timeout)


class TestHttpRequestValidation:
    """Tests for input validation."""

    def test_missing_url(self, workspace, basic_context):
        """Test that missing URL raises ValueError wrapped in TaskExecutionError."""
        step = {
            "name": "test_no_url",
            "task": "http.request",
            "inputs": {"method": "GET"},
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert isinstance(exc_info.value.original_error, ValueError)
        assert "url parameter is required" in str(exc_info.value.original_error)


class TestHttpRequestErrors:
    """Tests for HTTP and connection error handling."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_http_error_response(self, mock_urlopen, workspace, basic_context):
        """Test that HTTP errors (4xx/5xx) are caught and wrapped."""
        error = urllib.error.HTTPError(
            url="https://api.example.com/missing",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=BytesIO(b'{"error": "not found"}'),
        )
        mock_urlopen.side_effect = error

        step = {
            "name": "test_http_error",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/missing"},
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert "404" in str(exc_info.value)
        assert "Not Found" in str(exc_info.value)

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_http_500_error(self, mock_urlopen, workspace, basic_context):
        """Test that server errors (500) are caught."""
        error = urllib.error.HTTPError(
            url="https://api.example.com/error",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=BytesIO(b"server error"),
        )
        mock_urlopen.side_effect = error

        step = {
            "name": "test_500_error",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/error"},
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert "500" in str(exc_info.value)

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_connection_error(self, mock_urlopen, workspace, basic_context):
        """Test that URLError (connection failure) is caught."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        step = {
            "name": "test_connection_error",
            "task": "http.request",
            "inputs": {"url": "https://nonexistent.example.com"},
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert isinstance(exc_info.value.original_error, urllib.error.URLError)
        assert "Connection refused" in str(exc_info.value)

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_os_error(self, mock_urlopen, workspace, basic_context):
        """Test that OSError is caught and wrapped."""
        mock_urlopen.side_effect = OSError("Network is unreachable")

        step = {
            "name": "test_os_error",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/data"},
        }

        config = TaskConfig(step, basic_context, workspace)
        with pytest.raises(TaskExecutionError) as exc_info:
            http_request_task(config)

        assert isinstance(exc_info.value.original_error, OSError)


class TestHttpRequestJsonParsing:
    """Tests for JSON response parsing."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_json_response_parsed(self, mock_urlopen, workspace, basic_context):
        """Test that valid JSON response body is parsed."""
        mock_urlopen.return_value = _make_mock_response(
            body='{"users": [{"id": 1}, {"id": 2}]}',
            status=200,
            headers={"Content-Type": "application/json"},
        )

        step = {
            "name": "test_json_parse",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/users"},
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["json"] == {"users": [{"id": 1}, {"id": 2}]}
        assert isinstance(result["json"], dict)

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_non_json_response(self, mock_urlopen, workspace, basic_context):
        """Test that non-JSON response has json=None."""
        mock_urlopen.return_value = _make_mock_response(
            body="<html><body>Hello</body></html>",
            status=200,
            headers={"Content-Type": "text/html"},
        )

        step = {
            "name": "test_non_json",
            "task": "http.request",
            "inputs": {"url": "https://example.com"},
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["json"] is None
        assert result["body"] == "<html><body>Hello</body></html>"
        assert result["status_code"] == 200

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_json_array_response(self, mock_urlopen, workspace, basic_context):
        """Test that JSON array response is parsed correctly."""
        mock_urlopen.return_value = _make_mock_response(
            body="[1, 2, 3]",
            status=200,
        )

        step = {
            "name": "test_json_array",
            "task": "http.request",
            "inputs": {"url": "https://api.example.com/list"},
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["json"] == [1, 2, 3]

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_empty_body_response(self, mock_urlopen, workspace, basic_context):
        """Test response with empty body."""
        mock_urlopen.return_value = _make_mock_response(
            body="",
            status=204,
        )

        step = {
            "name": "test_empty_body",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/delete",
                "method": "DELETE",
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        assert result["status_code"] == 204
        assert result["body"] == ""
        assert result["json"] is None


class TestHttpRequestMethodVariants:
    """Tests for various HTTP methods."""

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_put_request(self, mock_urlopen, workspace, basic_context):
        """Test PUT request with JSON body."""
        mock_urlopen.return_value = _make_mock_response(
            body='{"updated": true}',
            status=200,
        )

        step = {
            "name": "test_put",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/items/1",
                "method": "PUT",
                "body": {"name": "updated-item"},
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        result = http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.method == "PUT"
        assert req.get_header("Content-type") == "application/json"
        assert result["json"]["updated"] is True

    @patch("yaml_workflow.tasks.http_tasks.urllib.request.urlopen")
    def test_method_case_insensitive(self, mock_urlopen, workspace, basic_context):
        """Test that method is uppercased regardless of input case."""
        mock_urlopen.return_value = _make_mock_response(body="OK", status=200)

        step = {
            "name": "test_method_case",
            "task": "http.request",
            "inputs": {
                "url": "https://api.example.com/data",
                "method": "get",
            },
        }

        config = TaskConfig(step, basic_context, workspace)
        http_request_task(config)

        req = mock_urlopen.call_args[0][0]
        assert req.method == "GET"
