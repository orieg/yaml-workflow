"""Notification task supporting webhook, log, slack, and file channels."""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..exceptions import TaskExecutionError, TemplateError
from . import TaskConfig, register_task
from .base import get_task_logger, log_task_execution, log_task_result
from .error_handling import ErrorContext, handle_task_error

# ---------------------------------------------------------------------------
# Channel helpers
# ---------------------------------------------------------------------------


def _notify_webhook(
    url: str,
    message: str,
    method: str = "POST",
    extra_headers: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> Dict[str, Any]:
    """Send a notification via an arbitrary HTTP webhook.

    Args:
        url: Webhook endpoint URL.
        message: Notification message (used as the body when *payload* is None).
        method: HTTP method. Default ``POST``.
        extra_headers: Additional headers to include in the request.
        payload: If provided, serialised as-is to JSON.  When omitted the
            message is wrapped in ``{"text": message}``.

    Returns:
        Dict with ``status_code`` and ``response_body``.

    Raises:
        urllib.error.HTTPError: On non-2xx responses.
        urllib.error.URLError: On connectivity issues.
    """
    body = payload if payload is not None else {"text": message}
    data = json.dumps(body).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, data=data, method=method.upper())
    for key, value in headers.items():
        req.add_header(key, value)

    response = urllib.request.urlopen(req, timeout=30)
    response_body = response.read().decode("utf-8")
    return {"status_code": response.status, "response_body": response_body}


def _notify_log(
    message: str,
    level: str = "info",
    file: Optional[str] = None,
) -> None:
    """Write a notification to the Python logging system and optionally to a file.

    Args:
        message: Notification message.
        level: Log level — ``debug``, ``info``, ``warning``, or ``error``.
            Default ``info``.
        file: Optional path to an additional log file.  When provided, the
            message is appended as a plain-text line.
    """
    logger = logging.getLogger("yaml_workflow.notify")
    level_map = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
    }
    log_fn = level_map.get(str(level).lower(), logger.info)
    log_fn(message)

    if file:
        log_path = os.path.abspath(file)
        with open(log_path, "a", encoding="utf-8") as fh:
            ts = datetime.now(timezone.utc).isoformat()
            fh.write(f"[{ts}] [{level.upper()}] {message}\n")


def _notify_slack(
    webhook_url: str,
    message: str,
    username: str = "yaml-workflow",
    icon_emoji: str = ":robot_face:",
    color: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a notification to Slack via an Incoming Webhook URL.

    Builds a minimal Slack attachment payload when *color* is provided;
    otherwise sends a plain ``text`` message.

    Args:
        webhook_url: Slack Incoming Webhook URL.
        message: Notification message.
        username: Display name shown in Slack. Default ``yaml-workflow``.
        icon_emoji: Emoji icon shown next to the bot name. Default
            ``:robot_face:``.
        color: Optional attachment sidebar colour — ``good``, ``warning``,
            ``danger``, or a hex string (e.g. ``#36a64f``).

    Returns:
        Dict with ``status_code`` and ``response_body``.
    """
    if color:
        payload: dict = {
            "username": username,
            "icon_emoji": icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "text": message,
                    "fallback": message,
                }
            ],
        }
    else:
        payload = {
            "text": message,
            "username": username,
            "icon_emoji": icon_emoji,
        }

    return _notify_webhook(webhook_url, message, payload=payload)


def _notify_file(
    file: str,
    message: str,
    workflow_name: str = "",
    append: bool = True,
    fmt: str = "jsonl",
) -> None:
    """Write a notification to a file.

    Args:
        file: Destination file path.
        message: Notification message.
        workflow_name: Optional workflow name included in structured records.
        append: Whether to append to an existing file. Default ``True``.
        fmt: Output format — ``jsonl`` or ``text``. Default ``jsonl``.
    """
    mode = "a" if append else "w"
    file_path = os.path.abspath(file)
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    with open(file_path, mode, encoding="utf-8") as fh:
        ts = datetime.now(timezone.utc).isoformat()
        if fmt == "jsonl":
            record = {
                "timestamp": ts,
                "message": message,
                "workflow": workflow_name,
            }
            fh.write(json.dumps(record) + "\n")
        else:
            fh.write(f"[{ts}] {message}\n")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@register_task("notify")
def notify_task(config: TaskConfig) -> Dict[str, Any]:
    """
    Send a notification via one of several supported channels.

    Args:
        config: Task configuration with namespace support.

    Inputs:
        channel (str): Notification channel. Required. One of ``webhook``,
            ``log``, ``slack``, ``file``.

        **webhook channel**::

            channel: webhook
            url: "https://hooks.example.com/..."
            message: "Workflow completed"
            method: POST          # optional, default POST
            headers:              # optional extra headers
              X-Custom: value
            payload:              # optional; used as-is; otherwise {"text": message}
              text: "..."

        **log channel**::

            channel: log
            message: "Step completed"
            level: info           # debug|info|warning|error, default: info
            file: "notify.log"    # optional; appended as plain text

        **slack channel**::

            channel: slack
            webhook_url: "{{ env.SLACK_WEBHOOK_URL }}"
            message: "{{ workflow.name }} finished"
            username: "yaml-workflow"     # optional
            icon_emoji: ":robot_face:"    # optional
            color: good                   # optional: good|warning|danger|#hex

        **file channel**::

            channel: file
            file: "notifications.jsonl"
            message: "Completed"
            append: true          # default true
            format: jsonl         # jsonl|text, default: jsonl

    Returns:
        Dict[str, Any]: ``{"channel": channel, "status": "sent", "message": message}``

    Raises:
        TaskExecutionError: If the notification cannot be delivered.
    """
    task_name = str(config.name or "notify_task")
    task_type = str(config.type or "notify")
    logger = get_task_logger(config.workspace, task_name)

    try:
        log_task_execution(logger, config.step, config.context, config.workspace)

        processed = config.process_inputs()
        config.processed_inputs = processed

        channel = processed.get("channel", "")
        if not channel:
            raise ValueError("'channel' input is required for the notify task.")

        message = str(processed.get("message", ""))

        # Derive a workflow name for structured outputs
        workflow_name = ""
        if config.context:
            wf = config.context.get("workflow", {})
            if isinstance(wf, dict):
                workflow_name = str(wf.get("name", ""))

        # ----------------------------------------------------------------
        # Dispatch by channel
        # ----------------------------------------------------------------
        extra: Dict[str, Any] = {}

        if channel == "webhook":
            url = processed.get("url")
            if not url:
                raise ValueError("webhook channel requires 'url'.")
            method = processed.get("method", "POST")
            extra_headers = processed.get("headers", {}) or {}
            payload = processed.get("payload", None)
            send_result = _notify_webhook(
                url,
                message,
                method=method,
                extra_headers=extra_headers,
                payload=payload,
            )
            extra["status_code"] = send_result["status_code"]

        elif channel == "log":
            level = processed.get("level", "info")
            log_file = processed.get("file", None)
            _notify_log(message, level=level, file=log_file)

        elif channel == "slack":
            webhook_url = processed.get("webhook_url")
            if not webhook_url:
                raise ValueError("slack channel requires 'webhook_url'.")
            username = processed.get("username", "yaml-workflow")
            icon_emoji = processed.get("icon_emoji", ":robot_face:")
            color = processed.get("color", None)
            send_result = _notify_slack(
                webhook_url,
                message,
                username=username,
                icon_emoji=icon_emoji,
                color=color,
            )
            extra["status_code"] = send_result["status_code"]

        elif channel == "file":
            dest_file = processed.get("file")
            if not dest_file:
                raise ValueError("file channel requires 'file'.")
            append = bool(processed.get("append", True))
            fmt = processed.get("format", "jsonl")
            _notify_file(
                dest_file,
                message,
                workflow_name=workflow_name,
                append=append,
                fmt=fmt,
            )

        else:
            raise ValueError(
                f"Unsupported notification channel: '{channel}'. "
                "Supported channels: webhook, log, slack, file."
            )

        result: Dict[str, Any] = {
            "channel": channel,
            "status": "sent",
            "message": message,
            **extra,
        }
        log_task_result(logger, result)
        return result

    except (
        TaskExecutionError,
        TemplateError,
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
        ValueError,
    ) as e:
        if isinstance(e, urllib.error.HTTPError):
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                error_body = ""
            error_msg = (
                f"HTTP {e.code} {e.reason} sending notification to "
                f"{processed.get('url') or processed.get('webhook_url', '?')}: "
                f"{error_body}"
            )
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
