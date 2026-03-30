"""MCP server that exposes yaml-workflow pipelines as tools.

Usage:
    yaml-workflow serve-mcp --dir workflows/

Each workflow YAML file in the directory becomes an MCP tool. Workflow
params become tool input parameters. Running a tool executes the
workflow and returns results as JSON.
"""

import json
import logging
import os
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


async def serve(directory: str, base_dir: str = "runs") -> None:
    """Start the MCP server exposing workflows as tools.

    Args:
        directory: Path to directory containing workflow YAML files.
        base_dir: Base directory for workflow run workspaces.
    """
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import TextContent, Tool
    except ImportError:
        raise ImportError(
            "MCP server requires the 'mcp' package. "
            "Install it with: pip install 'yaml-workflow[mcp]'"
        )

    from .engine import WorkflowEngine

    server = Server("yaml-workflow")
    workflow_dir = directory

    @server.list_tools()
    async def list_tools() -> list:
        """Return available workflow tools."""
        workflows = _scan_workflows(workflow_dir)
        tools = []
        for wf in workflows:
            tool_name = wf["name"].lower().replace(" ", "_").replace("-", "_")
            tools.append(
                Tool(
                    name=tool_name,
                    description=wf["description"] or f"Run the {wf['name']} workflow",
                    inputSchema=_params_to_schema(wf["params"]),
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        """Execute a workflow tool."""
        workflows = _scan_workflows(workflow_dir)

        # Find matching workflow
        target = None
        for wf in workflows:
            tool_name = wf["name"].lower().replace(" ", "_").replace("-", "_")
            if tool_name == name:
                target = wf
                break

        if target is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Workflow '{name}' not found"}),
                )
            ]

        try:
            engine = WorkflowEngine(
                target["path"],
                base_dir=base_dir,
            )
            results = engine.run(**arguments)

            # Extract step outputs
            outputs = {}
            if results and results.get("outputs"):
                for step_name, step_data in results["outputs"].items():
                    if isinstance(step_data, dict) and "result" in step_data:
                        outputs[step_name] = step_data["result"]
                    else:
                        outputs[step_name] = step_data

            response = {
                "status": "success",
                "workflow": target["name"],
                "outputs": outputs,
            }
        except Exception as e:
            response = {
                "status": "failed",
                "workflow": target["name"],
                "error": str(e),
            }

        return [
            TextContent(
                type="text",
                text=json.dumps(response, indent=2, default=str),
            )
        ]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
