# Invar + Continue Integration Guide

[Continue](https://continue.dev/) is an open-source AI coding assistant for VS Code and JetBrains. It was the first to fully support MCP, making it excellent for Invar integration.

## Quick Start

### 1. Install Invar

```bash
uv add --dev invar-tools invar-runtime
```

### 2. Configure Continue

Open Continue configuration (`Ctrl+Shift+P` → "Continue: Open config.json"):

```json
{
  "models": [
    {
      "title": "Claude Sonnet",
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "apiKey": "YOUR_API_KEY"
    }
  ],
  "mcpServers": [
    {
      "name": "invar",
      "command": "uv",
      "args": ["run", "invar", "mcp"]
    }
  ],
  "customCommands": [
    {
      "name": "guard",
      "description": "Run Invar verification",
      "prompt": "Run invar_guard to verify the code. Report any errors or warnings."
    },
    {
      "name": "sig",
      "description": "Show function signatures",
      "prompt": "Use invar_sig to show the signatures and contracts for {{{ input }}}"
    }
  ],
  "systemMessage": "You follow the Invar development protocol. Always write @pre/@post contracts before implementation. Use invar_guard for verification, never pytest directly."
}
```

### 3. Create Rules

Create `.continue/rules/invar.md`:

```markdown
# Invar Development Rules

## Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | Use invar_guard MCP tool — NOT pytest |
| **Core** | @pre/@post + doctests, NO I/O imports |
| **Shell** | Returns Result[T, E] from returns library |
| **Flow** | Contracts first → Build → Validate |

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```

## Workflow

1. **SPECIFY** - Write contracts first (@pre/@post, doctests)
2. **BUILD** - Implement following contracts
3. **VALIDATE** - Run invar_guard

## Verification

Always use the invar_guard MCP tool:
- `invar_guard(changed=true)` for incremental
- `invar_guard()` for full verification

Never use pytest or crosshair directly.
```

---

## MCP Configuration

Continue has complete MCP support. Configure in `config.json`:

### Option A: Using project environment (Recommended)

```json
{
  "mcpServers": [
    {
      "name": "invar",
      "command": "uv",
      "args": ["run", "invar", "mcp"]
    }
  ]
}
```

### Option B: Using Project Venv Python Directly

```json
{
  "mcpServers": [
    {
      "name": "invar",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  ]
}
```

### Option C: One-off uvx fallback

```json
{
  "mcpServers": [
    {
      "name": "invar",
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  ]
}
```

### Verify MCP Connection

Ask Continue:
```
What MCP tools are available?
```

It should list `invar_guard`, `invar_sig`, `invar_map`.

---

## Custom Commands

Continue supports custom slash commands. Add to `config.json`:

```json
{
  "customCommands": [
    {
      "name": "guard",
      "description": "Run Invar verification",
      "prompt": "Run invar_guard(changed=true) to verify recent changes. Report results clearly."
    },
    {
      "name": "guard-full",
      "description": "Run full Invar verification",
      "prompt": "Run invar_guard() for complete verification. Report all errors and warnings."
    },
    {
      "name": "sig",
      "description": "Show function signatures and contracts",
      "prompt": "Use invar_sig to show signatures for: {{{ input }}}"
    },
    {
      "name": "map",
      "description": "Show symbol map",
      "prompt": "Use invar_map to show the symbol map with reference counts."
    }
  ]
}
```

### Using Custom Commands

```
/guard              # Run verification
/sig src/core/...   # Show signatures
```

---

## System Message

Set a system message for all conversations:

```json
{
  "systemMessage": "You are an Invar-compliant developer. Follow these rules:\n\n1. ALWAYS write @pre/@post contracts before implementation\n2. Use invar_guard for verification, NEVER pytest directly\n3. Follow Core/Shell separation (core=pure, shell=Result[T,E])\n4. Include doctests for all public functions\n5. Contracts first, then build, then validate"
}
```

---

## Rules Directory

Continue supports a rules directory for organized instructions:

```
.continue/
└── rules/
    ├── invar-core.md
    ├── invar-shell.md
    └── invar-workflow.md
```

### `invar-core.md`

```markdown
# Core Module Rules

Files in `src/*/core/` must follow these rules:

## Requirements

1. **Pure functions only** - No I/O operations
2. **Contracts required** - @pre/@post on all public functions
3. **Doctests required** - Usage examples in docstrings
4. **Forbidden imports** - No pathlib, os, requests, subprocess

## Example

```python
from invar_runtime import pre, post

@pre(lambda items: len(items) > 0)
@post(lambda result: result is not None)
def first(items: list[str]) -> str:
    """
    Get first item.

    >>> first(["a", "b"])
    'a'
    """
    return items[0]
```
```

### `invar-shell.md`

```markdown
# Shell Module Rules

Files in `src/*/shell/` must follow these rules:

## Requirements

1. **Result return type** - Use Result[T, E] for fallible operations
2. **Explicit error handling** - No bare exceptions
3. **Dependency injection** - For testability

## Example

```python
from returns.result import Result, Success, Failure
from pathlib import Path

def read_config(path: str) -> Result[Config, str]:
    """Read configuration file."""
    try:
        data = Path(path).read_text()
        return Success(parse_config(data))
    except FileNotFoundError:
        return Failure(f"Config not found: {path}")
    except Exception as e:
        return Failure(f"Failed to read config: {e}")
```
```

---

## Feature Mapping

### What Works

| Invar Feature | Continue Support |
|---------------|------------------|
| Guard Verification | ✅ Via MCP (best support) |
| Sig/Map Tools | ✅ Via MCP |
| Core/Shell Rules | ✅ Via rules |
| Custom Commands | ✅ Similar to skills |

### What's Different

| Claude Code | Continue Alternative |
|-------------|---------------------|
| CLAUDE.md | .continue/rules/ |
| MCP tools | Same MCP protocol |

**Historical note:** Pre-DX-91 versions supported USBV workflow (Understand → Specify → Build → Validate), skills, and hooks. These were removed per [DX-91](../proposals/DX-91-simplification.md) in favor of guard-enforced contracts before code.

---

## Complete Configuration

### Full config.json

```json
{
  "models": [
    {
      "title": "Claude Sonnet",
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "apiKey": "YOUR_API_KEY"
    },
    {
      "title": "GPT-4o",
      "provider": "openai",
      "model": "gpt-4o",
      "apiKey": "YOUR_API_KEY"
    }
  ],
  "mcpServers": [
    {
      "name": "invar",
      "command": "uv",
      "args": ["run", "invar", "mcp"]
    }
  ],
  "customCommands": [
    {
      "name": "guard",
      "description": "Run Invar verification",
      "prompt": "Run invar_guard(changed=true). Report errors and warnings."
    },
    {
      "name": "sig",
      "description": "Show signatures",
      "prompt": "Use invar_sig for: {{{ input }}}"
    },
    {
      "name": "map",
      "description": "Show symbol map",
      "prompt": "Use invar_map to show symbols."
    }
  ],
  "systemMessage": "Follow Invar protocol: @pre/@post contracts, Core/Shell separation, invar_guard for verification.",
  "tabAutocompleteModel": {
    "title": "Starcoder",
    "provider": "ollama",
    "model": "starcoder2:3b"
  }
}
```

### Directory Structure

```
your-project/
├── .continue/
│   ├── config.json        # Continue configuration
│   └── rules/
│       ├── invar-core.md
│       ├── invar-shell.md
│       └── invar-workflow.md
├── CLAUDE.md              # Invar guidance (from init)
├── INVAR.md               # Protocol reference (from init)
├── src/
│   └── your_package/
│       ├── core/          # Pure logic
│       └── shell/         # I/O operations
└── .pre-commit-config.yaml
```

---

## Troubleshooting

### MCP Tools Not Available

1. Check MCP configuration in config.json
2. Verify invar-tools: `pip show invar-tools`
3. Test MCP: `uv run invar mcp`
4. Restart Continue extension

### Custom Commands Not Working

1. Check config.json syntax
2. Ensure command has `name`, `description`, `prompt`
3. Reload Continue configuration

### Rules Not Applied

1. Verify `.continue/rules/` directory exists
2. Check file names end in `.md`
3. Rules should be at project root

### Model Doesn't Follow Instructions

1. Check systemMessage is set
2. Add explicit instructions to rules
3. Use custom commands to enforce workflow

---

## Tips

1. **Leverage MCP fully** - Continue has excellent MCP support
2. **Use customCommands** - They're like lightweight skills
3. **Organize rules** - One file per concern
4. **Set systemMessage** - Persistent context across chats

---

## Next Steps

- [Pi Integration](./pi.md)
- [Cursor Integration](./cursor.md)
- [Cline Integration](./cline.md)
- [Aider Integration](./aider.md)
