# Invar MCP Server Setup

This project includes an MCP server that provides Invar tools to AI agents.

## Available Tools

| Tool | Replaces | Purpose |
|------|----------|---------|
| `invar_guard` | `pytest`, `crosshair` | Smart Guard verification |
| `invar_sig` | `Read` entire file | Show contracts and signatures |
| `invar_map` | `Grep` for functions | Symbol map with reference counts |

## Configuration

`invar init` automatically creates `.mcp.json` with smart detection of available methods.

### Recommended: uvx (isolated environment)

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

### Alternative: invar command

```json
{
  "mcpServers": {
    "invar": {
      "command": "invar",
      "args": ["mcp"]
    }
  }
}
```

### Fallback: Python path

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

## Installation

```bash
# Recommended: use uvx (no installation needed)
uvx invar-tools guard

# Or install globally
pip install invar-tools

# Or install in project
pip install invar-tools
```

## Testing

Run the MCP server directly:

```bash
# Using uvx
uvx invar-tools mcp

# Or if installed
invar mcp
```

The server communicates via stdio and should be managed by your AI agent.
