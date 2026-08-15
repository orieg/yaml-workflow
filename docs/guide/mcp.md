# MCP Server Integration

yaml-workflow can expose your workflows as [MCP](https://modelcontextprotocol.io)
(Model Context Protocol) tools, making them discoverable and callable by AI
agents like Claude Code, Claude Desktop, and Cursor. Each workflow in a
directory becomes a typed tool the agent can run.

## Installation

The MCP server requires the `mcp` extra (kept optional so the core engine stays
at two dependencies):

```bash
pipx install 'yaml-workflow[mcp]'   # or 'yaml-workflow[all]'
# or
pip install 'yaml-workflow[mcp]'
```

## Usage

Point the MCP server at a directory of workflow YAML files:

```bash
yaml-workflow serve-mcp --dir workflows/
```

The server speaks MCP over stdio, so it is launched by the MCP client rather
than run standalone (see the client configs below).

## How it works

- Scans the directory for workflow YAML files (any `*.yaml` with a `steps:` key).
- Each workflow becomes an MCP tool, named after the workflow's `name`.
- Workflow `params` become the tool's input parameters, with types and
  descriptions carried through to the agent.
- Calling a tool runs the workflow and returns the step outputs as JSON.

## Client configuration

All MCP clients launch the server the same way — the command `yaml-workflow`
with `serve-mcp --dir <your-workflows>`. Install the `[mcp]` extra first (above).

### Claude Code

```bash
claude mcp add yaml-workflow -- yaml-workflow serve-mcp --dir /path/to/workflows
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

### Cursor / other stdio clients

Any client that speaks MCP over stdio uses the same shape:

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

Once configured, the client discovers every workflow in the directory as a
callable tool; descriptions and parameter metadata appear in the tool list
automatically.

## Install from the MCP Registry

yaml-workflow is published to the [official MCP Registry](https://registry.modelcontextprotocol.io)
as `io.github.orieg/yaml-workflow`. Clients that browse the registry can install
it directly. The registry launches it with [`uvx`](https://docs.astral.sh/uv/),
pulling the `[mcp]` extra:

```bash
uvx --from 'yaml-workflow[mcp]' yaml-workflow serve-mcp --dir workflows/
```

If your client does not compose the `--from` extra automatically, fall back to
the explicit install (`pip install 'yaml-workflow[mcp]'`) plus one of the client
configs above.

## Security

The MCP server lets a connected agent **execute the workflows in the directory
you serve** — which may run shell commands and Python. Only serve workflows you
trust, run the server with least privilege, and treat parameters coming from an
agent as untrusted input. See the [Security Policy](https://github.com/orieg/yaml-workflow/blob/main/SECURITY.md)
for the full execution model.
