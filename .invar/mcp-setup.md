# Invar MCP Server Setup

This project includes an MCP server that provides Invar tools to AI agents.

## Available Tools

| Tool | Replaces | Purpose |
|------|----------|---------|
| `invar_guard` | `pytest`, `crosshair` | Smart Guard verification |
| `invar_sig` | `Read` entire file | Show contracts and signatures |
| `invar_map` | `Grep` for functions | Symbol map with reference counts |

## Configuration

Add MCP config manually using one of the templates below.

### Recommended: project-local environment

First, install Invar in your project dev dependencies:

```bash
uv add --dev invar-tools invar-runtime
```

Then configure MCP to use the project environment:

```json
{
  "mcpServers": {
    "invar": {
      "command": "uv",
      "args": ["run", "invar", "mcp"]
    }
  }
}
```

### Alternative: direct Python path

```json
{
  "mcpServers": {
    "invar": {
      "command": "/path/to/your/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  }
}
```

Find your Python path: `python -c "import sys; print(sys.executable)"`

### Fallback: uvx (isolated, not recommended)

Use this only if you cannot install invar-tools in the project:

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

Note: uvx runs in an isolated environment and may not have access to project dependencies, which can cause issues with CrossHair and Hypothesis.

## Testing

Run the MCP server directly:

```bash
# Using project environment
uv run invar mcp

# Or if installed globally
invar mcp
```

The server communicates via stdio and should be managed by your AI agent.
