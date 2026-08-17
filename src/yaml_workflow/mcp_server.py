"""MCP server that exposes yaml-workflow pipelines as tools.

Usage:
    yaml-workflow serve-mcp --dir workflows/

The server exposes a fixed set of meta-tools for discovering, validating,
previewing, and running workflows (``list_workflows``, ``validate_workflow``,
``dry_run_workflow``, ``run_workflow``), plus one convenience tool per workflow
YAML file found in the served directory. Running a workflow executes it and
returns its step outputs as JSON.
"""

import contextlib
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


def _scan_workflows(directory: str) -> List[Dict[str, Any]]:
    """Discover workflow YAML files and extract metadata.

    Args:
        directory: Path to scan for workflow YAML files.

    Returns:
        List of dicts with keys: path, name, description, params.
    """
    workflows: List[Dict[str, Any]] = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return workflows

    for path in sorted(dir_path.glob("**/*.yaml")):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict) or "steps" not in data:
                continue
            workflows.append(
                {
                    "path": str(path),
                    "name": data.get("name", path.stem),
                    "description": data.get("description", ""),
                    "params": data.get("params", {}),
                }
            )
        except (yaml.YAMLError, OSError):
            continue

    return workflows


def _params_to_schema(params: dict) -> dict:
    """Convert workflow params section to JSON Schema for MCP tool input.

    Args:
        params: The workflow's params dict (name -> {type, default, description, ...}).

    Returns:
        JSON Schema object suitable for MCP tool inputSchema.
    """
    if not params:
        return {"type": "object", "properties": {}}

    properties = {}
    required = []

    type_map = {
        "string": "string",
        "str": "string",
        "integer": "integer",
        "int": "integer",
        "number": "number",
        "float": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
    }

    for name, config in params.items():
        if isinstance(config, dict):
            prop = {}
            param_type = str(config.get("type", "string")).lower()
            prop["type"] = type_map.get(param_type, "string")
            if "description" in config:
                prop["description"] = config["description"]
            if "default" in config:
                prop["default"] = config["default"]
            properties[name] = prop
            if config.get("required", False) and "default" not in config:
                required.append(name)
        else:
            # Simple form: param_name: default_value
            properties[name] = {"type": "string", "default": str(config)}

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _tool_name(workflow_name: str) -> str:
    """Derive a stable snake_case MCP tool name from a workflow name."""
    return workflow_name.lower().replace(" ", "_").replace("-", "_")


# Reserved meta-tool names that a per-workflow tool must not shadow.
_META_TOOL_NAMES = {
    "list_workflows",
    "validate_workflow",
    "dry_run_workflow",
    "run_workflow",
}


def _resolve_workflow(workflow: Optional[str], directory: str) -> Optional[str]:
    """Resolve a workflow reference to a file path.

    Accepts either a direct path to a YAML file or the ``name`` of a workflow in
    the served directory (matched by its declared name or its snake_case tool
    name). Returns the resolved path, or None if it cannot be found.
    """
    if not workflow:
        return None
    candidate = Path(workflow)
    if candidate.is_file():
        return str(candidate)
    target = _tool_name(workflow)
    for wf in _scan_workflows(directory):
        if wf["name"] == workflow or _tool_name(wf["name"]) == target:
            return wf["path"]
    return None


def _validate_workflow(path: str) -> Dict[str, Any]:
    """Validate a workflow file and return the structured result."""
    from .validator import WorkflowValidator

    return WorkflowValidator(path).validate().to_dict()


def _execute_workflow(
    path: str,
    params: Optional[dict],
    base_dir: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """Run (or dry-run) a workflow, returning a compact JSON-friendly result.

    Engine stdout (e.g. the dry-run preview) is captured so it cannot corrupt
    the MCP stdio JSON-RPC stream; for a dry run it is returned as ``preview``.
    """
    from .engine import WorkflowEngine

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        engine = WorkflowEngine(path, base_dir=base_dir, dry_run=dry_run)
        result = engine.run(params=params or {})

    outputs: Dict[str, Any] = {}
    for step_name, data in (result.get("outputs") or {}).items():
        if isinstance(data, dict) and "result" in data:
            outputs[step_name] = data["result"]
        else:
            outputs[step_name] = data

    response: Dict[str, Any] = {
        "status": result.get("status", "unknown"),
        "outputs": outputs,
    }
    if dry_run:
        preview = buffer.getvalue().strip()
        if preview:
            response["preview"] = preview
    return response


async def serve(directory: str, base_dir: str = "runs") -> None:
    """Start the MCP server exposing workflows as tools.

    Args:
        directory: Path to directory containing workflow YAML files.
        base_dir: Base directory for workflow run workspaces.
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool, ToolAnnotations
    except ImportError:
        raise ImportError(
            "MCP server requires the 'mcp' package. "
            "Install it with: pip install 'yaml-workflow[mcp]'"
        )

    server = Server("yaml-workflow")
    workflow_dir = directory

    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
    destructive = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )

    workflow_arg_schema = {
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "description": (
                    "Workflow to target: either a name returned by "
                    "list_workflows, or a path to a workflow YAML file."
                ),
            },
            "params": {
                "type": "object",
                "description": (
                    "Optional values for the workflow's declared inputs, as an "
                    "object of name -> value. Omit to use each parameter's default."
                ),
            },
        },
        "required": ["workflow"],
    }

    def _meta_tools() -> List["Tool"]:
        return [
            Tool(
                name="list_workflows",
                description=(
                    "List the workflows available in this server's workflow "
                    "directory. Returns an object with `count` and `workflows` "
                    "(one entry per workflow, each containing `name` (its declared "
                    "name), `description`, `path` (the YAML file), and "
                    "`parameters` (declared inputs with types and defaults)). Call "
                    "this first to discover which workflows exist and what inputs "
                    "each accepts before calling dry_run_workflow or run_workflow. "
                    "Read-only: it only reads YAML files and never executes "
                    "anything. Takes no arguments."
                ),
                inputSchema={"type": "object", "properties": {}},
                annotations=read_only,
            ),
            Tool(
                name="validate_workflow",
                description=(
                    "Validate a single workflow YAML file without running it. "
                    "Give the file `path`; returns "
                    "`{valid, error_count, warning_count, issues[]}`, where each "
                    "issue has a level (error/warning/info), message, and optional "
                    "line, step, and hint. Use this to check a workflow the agent "
                    "authored or edited before running it, or to explain why a "
                    "workflow is malformed. Read-only: no tasks run and nothing "
                    "is written."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the workflow YAML file to validate.",
                        }
                    },
                    "required": ["path"],
                },
                annotations=read_only,
            ),
            Tool(
                name="dry_run_workflow",
                description=(
                    "Preview what a workflow would do without executing any task. "
                    "Give a `workflow` (a name from list_workflows or a file path) "
                    "and optional `params`; returns `{status, outputs, preview}` "
                    "where `preview` is a human-readable list of the steps that "
                    "would run with their resolved inputs (the same information as "
                    "the CLI's --dry-run). Use this to inspect side effects (shell "
                    "commands, file writes, HTTP calls) before running for real. "
                    "It does not execute any task — no shell or Python runs and "
                    "none of the workflow's own side effects occur; only ephemeral "
                    "logs are written to a temporary workspace."
                ),
                inputSchema=workflow_arg_schema,
                annotations=read_only,
            ),
            Tool(
                name="run_workflow",
                description=(
                    "Execute a workflow and return its results. Give a `workflow` "
                    "(a name from list_workflows or a file path) and optional "
                    "`params`; runs it to completion and returns "
                    "`{status, workflow, outputs}` where `outputs` maps each step "
                    "name to its result. DESTRUCTIVE: a workflow may run arbitrary "
                    "shell commands and Python, write files, and make HTTP "
                    "requests — call dry_run_workflow first if you need to preview "
                    "side effects, and only run workflows you trust."
                ),
                inputSchema=workflow_arg_schema,
                annotations=destructive,
            ),
        ]

    @server.list_tools()
    async def list_tools() -> list:
        """Return the meta-tools plus one convenience tool per workflow."""
        tools = _meta_tools()
        for wf in _scan_workflows(workflow_dir):
            name = _tool_name(wf["name"])
            if name in _META_TOOL_NAMES:
                # Don't let a workflow named e.g. "run workflow" shadow a meta-tool.
                name = f"workflow_{name}"
            base = wf["description"] or f"Run the '{wf['name']}' workflow."
            tools.append(
                Tool(
                    name=name,
                    description=(
                        f"{base} Executes the '{wf['name']}' workflow and returns "
                        "its step outputs as JSON. This runs the workflow's tasks "
                        "(which may include shell commands, Python, and HTTP "
                        "requests). Equivalent to run_workflow with "
                        f'workflow="{wf["name"]}".'
                    ),
                    inputSchema=_params_to_schema(wf["params"]),
                    annotations=destructive,
                )
            )
        return tools

    def _text(payload: Dict[str, Any]) -> list:
        return [
            TextContent(type="text", text=json.dumps(payload, indent=2, default=str))
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        """Dispatch a tool call to a meta-tool or a per-workflow run."""
        arguments = arguments or {}

        if name == "list_workflows":
            workflows = [
                {
                    "name": wf["name"],
                    "description": wf["description"],
                    "path": wf["path"],
                    "parameters": wf["params"],
                }
                for wf in _scan_workflows(workflow_dir)
            ]
            return _text({"workflows": workflows, "count": len(workflows)})

        if name == "validate_workflow":
            path = arguments.get("path")
            if not path or not Path(path).is_file():
                return _text({"error": f"Workflow file not found: {path!r}"})
            try:
                return _text(_validate_workflow(path))
            except Exception as e:  # noqa: BLE001 - surfaced to the agent
                return _text({"error": str(e)})

        if name in ("dry_run_workflow", "run_workflow"):
            workflow = arguments.get("workflow")
            path = _resolve_workflow(workflow, workflow_dir)
            if path is None:
                return _text({"error": f"Workflow not found: {workflow!r}"})
            params = arguments.get("params") or {}
            try:
                result = _execute_workflow(
                    path,
                    params,
                    base_dir=base_dir,
                    dry_run=(name == "dry_run_workflow"),
                )
                result["workflow"] = workflow
                return _text(result)
            except Exception as e:  # noqa: BLE001 - surfaced to the agent
                return _text(
                    {"status": "failed", "workflow": workflow, "error": str(e)}
                )

        # Otherwise: a per-workflow convenience tool. Match by tool name.
        for wf in _scan_workflows(workflow_dir):
            wf_tool = _tool_name(wf["name"])
            if wf_tool in _META_TOOL_NAMES:
                wf_tool = f"workflow_{wf_tool}"
            if wf_tool == name:
                try:
                    result = _execute_workflow(
                        wf["path"], arguments, base_dir=base_dir, dry_run=False
                    )
                    result["workflow"] = wf["name"]
                    return _text(result)
                except Exception as e:  # noqa: BLE001 - surfaced to the agent
                    return _text(
                        {"status": "failed", "workflow": wf["name"], "error": str(e)}
                    )

        return _text({"error": f"Unknown tool: {name!r}"})

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
