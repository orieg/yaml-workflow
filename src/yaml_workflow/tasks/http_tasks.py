"""HTTP request task for making web API calls."""

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error


@register_task("http.request")
def http_request_task(config: TaskConfig) -> Dict[str, Any]:
    """
    Make an HTTP request to a URL.

    Args:
        config: Task configuration with namespace support

    Returns:
        Dict[str, Any]: Response with status_code, headers, body, and json

    Raises:
        TaskExecutionError: If the request fails
    """
    task_name = str(config.name or "http_request_task")
    task_type = str(config.type or "http.request")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config._context, config.workspace)

        processed = config.process_inputs()
        config._processed_inputs = processed

        # Validate required inputs
        if "url" not in processed:
            raise ValueError("url parameter is required")

        url = processed["url"]
        method = processed.get("method", "GET").upper()
        headers = processed.get("headers", {})
        body = processed.get("body", None)
        timeout = processed.get("timeout", 30)

        # Prepare request body
        data = None
        if body is not None:
            if isinstance(body, dict):
                data = json.dumps(body).encode("utf-8")
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            elif isinstance(body, str):
                data = body.encode("utf-8")
            elif isinstance(body, bytes):
                data = body

        # Build request
        req = urllib.request.Request(url, data=data, method=method)
        for key, value in headers.items():
            req.add_header(key, value)

        # Execute request
        response = urllib.request.urlopen(req, timeout=timeout)

        response_body = response.read().decode("utf-8")
        response_headers = dict(response.headers)
        status_code = response.status

        # Try to parse JSON
        json_body = None
        try:
            json_body = json.loads(response_body)
        except (json.JSONDecodeError, ValueError):
            pass

        result = {
            "status_code": status_code,
            "headers": response_headers,
            "body": response_body,
            "json": json_body,
        }
        log_task_result(logger, result)
        return result

    except (
        TaskExecutionError,
        TemplateError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        socket.timeout,
        OSError,
        ValueError,
    ) as e:
        # For HTTPError, extract response details before wrapping
        if isinstance(e, urllib.error.HTTPError):
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = ""
            error_msg = f"HTTP {e.code} {e.reason} for {method} {url}: {error_body}"
            e = ValueError(error_msg)

        context = ErrorContext(
            step_name=task_name,
            task_type=task_type,
            error=e,
            task_config=config.step,
            template_context=config._context,
        )
        handle_task_error(context)
        return {}  # Unreachable
