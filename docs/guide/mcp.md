# MCP Server Integration

yaml-workflow can expose workflows as MCP (Model Context Protocol) tools, making them
discoverable by AI agents like Claude Desktop and Claude Code.

## Installation

Install with the `mcp` extra:

```bash
pip install 'yaml-workflow[mcp]'
```

## Usage

Point the MCP server at a directory of workflow YAML files:

```bash
yaml-workflow serve-mcp --dir workflows/
```

## How It Works

- Scans the directory for workflow YAML files.
- Each workflow becomes an MCP tool, named after the workflow file.
- Workflow `params` become tool input parameters with types and descriptions.
- Running a tool executes the workflow and returns results as JSON.

## Claude Desktop Configuration

Add yaml-workflow to your Claude Desktop MCP config
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "yaml-workflow": {
      "command": "yaml-workflow",
      "args": ["serve-mcp", "--dir", "/path/to/workflows"]
    }
  }
}
```

Once configured, Claude Desktop will discover every workflow in the directory as a
callable tool. Workflow descriptions and parameter metadata appear in the tool list
automatically.
