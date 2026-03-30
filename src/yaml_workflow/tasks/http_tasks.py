"""HTTP request task for making web API calls."""

import base64
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error


def _apply_auth(headers: dict, auth: Optional[dict], token: Optional[str]) -> dict:
    """Apply authentication to the request headers.

    Supports the following auth types via the ``auth`` dict:

    - ``bearer``: Adds ``Authorization: Bearer <token>``.  The token is read
      from ``auth["token"]`` or, when ``auth["token_env"]`` is set, from
      ``os.environ[token_env]``.
    - ``api_key``: Adds a custom header (default ``X-API-Key``) set to
      ``auth["key"]``.  Override the header name with ``auth["header"]``.
    - ``basic``: Encodes ``auth["username"]`` and ``auth["password"]`` as an
      HTTP Basic authentication header using base64.

    A top-level ``token`` shorthand (``inputs.token``) is also supported and
    is treated as a Bearer token.

    Args:
        headers: Existing request headers dict (not mutated; a copy is returned).
        auth: Optional auth configuration dict with ``type`` and related keys.
        token: Optional top-level shorthand Bearer token string.

    Returns:
        Updated headers dict (new dict, not the original).

    Raises:
        ValueError: If a required field is missing or ``token_env`` is not set
            in the environment.
    """
    headers = dict(headers)  # work on a copy

    # Top-level token shorthand → Bearer
    if token:
        headers.setdefault("Authorization", f"Bearer {token}")

    if not auth:
        return headers

    auth_type = str(auth.get("type", "")).lower()

    if auth_type == "bearer":
        # Resolve token from explicit value or environment variable
        if "token_env" in auth:
            env_var = auth["token_env"]
            value = os.environ.get(env_var)
            if not value:
                raise ValueError(
                    f"Bearer auth requires environment variable '{env_var}' "
                    "but it is not set or is empty."
                )
            bearer_token = value
        elif "token" in auth:
            bearer_token = auth["token"]
        else:
            raise ValueError(
                "Bearer auth requires either 'token' or 'token_env' in the auth config."
            )
        headers["Authorization"] = f"Bearer {bearer_token}"

    elif auth_type == "api_key":
        if "key" not in auth:
            raise ValueError("api_key auth requires 'key' in the auth config.")
        header_name = auth.get("header", "X-API-Key")
        headers[header_name] = auth["key"]

    elif auth_type == "basic":
        if "username" not in auth or "password" not in auth:
            raise ValueError(
                "basic auth requires both 'username' and 'password' in the auth config."
            )
        credentials = f"{auth['username']}:{auth['password']}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {encoded}"

    else:
        raise ValueError(
            f"Unsupported auth type: '{auth_type}'. "
            "Supported types: bearer, api_key, basic."
        )

    return headers


@register_task("http.request")
def http_request_task(config: TaskConfig) -> Dict[str, Any]:
    """
    Make an HTTP request to a URL.

    Args:
        config: Task configuration with namespace support

    Inputs:
        url (str): Target URL. Required.
        method (str): HTTP method. Default ``GET``.
        headers (dict): Extra request headers. Default ``{}``.
        body (str | dict | bytes): Request body. When a dict is provided it is
            serialised to JSON and ``Content-Type: application/json`` is set
            automatically (unless already present in *headers*).
        timeout (int | float): Request timeout in seconds. Default ``30``.
        token (str): Shorthand Bearer token. Sets
            ``Authorization: Bearer <token>``.  Ignored when *auth* is also
            provided.
        auth (dict): Authentication configuration.  Supports the following
            types:

            bearer::

                auth:
                  type: bearer
                  token: "{{ env.API_TOKEN }}"
                  # OR read from environment:
                  token_env: API_TOKEN

            api_key::

                auth:
                  type: api_key
                  key: "{{ env.API_KEY }}"
                  header: X-API-Key   # optional, default: X-API-Key

            basic::

                auth:
                  type: basic
                  username: "{{ env.API_USER }}"
                  password: "{{ env.API_PASS }}"

        verify_ssl (bool): Verify the server's TLS certificate. Default
            ``True``.  Set to ``False`` to disable certificate verification
            (equivalent to ``curl --insecure``).
        retry (dict): Retry configuration::

                retry:
                  max_attempts: 3          # total attempts, default: 1
                  delay: 1.0               # seconds between retries, default: 1.0
                  status_codes: [429, 503] # retry on these codes,
                                           # default: [429, 500, 502, 503, 504]

    Returns:
        Dict[str, Any]: Response with keys ``status_code``, ``headers``,
        ``body``, and ``json``.

    Raises:
        TaskExecutionError: If the request fails or authentication config is
            invalid.
    """
    task_name = str(config.name or "http_request_task")
    task_type = str(config.type or "http.request")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config.context, config.workspace)

        processed = config.process_inputs()
        config.processed_inputs = processed

        # Validate required inputs
        if "url" not in processed:
            raise ValueError("url parameter is required")

        url = processed["url"]
        method = processed.get("method", "GET").upper()
        headers = processed.get("headers", {})
        body = processed.get("body", None)
        timeout = processed.get("timeout", 30)
        token = processed.get("token", None)
        auth = processed.get("auth", None)
        verify_ssl = processed.get("verify_ssl", True)

        # Retry configuration
        retry_cfg = processed.get("retry", {}) or {}
        max_attempts = int(retry_cfg.get("max_attempts", 1))
        retry_delay = float(retry_cfg.get("delay", 1.0))
        retry_status_codes = list(
            retry_cfg.get("status_codes", [429, 500, 502, 503, 504])
        )

        # Apply authentication
        headers = _apply_auth(headers, auth, token)

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

        # SSL context
        ssl_context: Optional[ssl.SSLContext] = None
        if not verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Retry loop
        last_exception: Optional[Exception] = None
        result: Optional[Dict[str, Any]] = None

        for attempt in range(1, max_attempts + 1):
            try:
                # Build request
                req = urllib.request.Request(url, data=data, method=method)
                for key, value in headers.items():
                    req.add_header(key, value)

                # Execute request
                response = urllib.request.urlopen(
                    req, timeout=timeout, context=ssl_context
                )

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
                # Success — exit retry loop
                break

            except urllib.error.HTTPError as http_err:
                if http_err.code in retry_status_codes and attempt < max_attempts:
                    logger.warning(
                        f"HTTP {http_err.code} on attempt {attempt}/{max_attempts}; "
                        f"retrying in {retry_delay}s…"
                    )
                    last_exception = http_err
                    time.sleep(retry_delay)
                    continue
                # Not retryable or last attempt — re-raise to outer handler
                raise

            except (urllib.error.URLError, socket.timeout, OSError) as net_err:
                if attempt < max_attempts:
                    logger.warning(
                        f"Network error on attempt {attempt}/{max_attempts}: {net_err}; "
                        f"retrying in {retry_delay}s…"
                    )
                    last_exception = net_err
                    time.sleep(retry_delay)
                    continue
                raise

        if result is None:
            # All attempts exhausted via retry loop without raising — shouldn't
            # normally happen, but guard defensively.
            raise last_exception or RuntimeError("All retry attempts exhausted.")

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
            template_context=config.context,
        )
        handle_task_error(context)
        return {}  # Unreachable
