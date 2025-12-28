# Invar + Continue Integration Guide

[Continue](https://continue.dev/) is an open-source AI coding assistant for VS Code and JetBrains. It was the first to fully support MCP, making it excellent for Invar integration.

## Quick Start

### 1. Install Invar

```bash
pip install invar-tools
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
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
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
| **Flow** | USBV: Understand → Specify → Build → Validate |

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```

## Workflow

1. **UNDERSTAND** - Analyze requirements
2. **SPECIFY** - Write contracts first
3. **BUILD** - Implement following contracts
4. **VALIDATE** - Run invar_guard

## Verification

Always use the invar_guard MCP tool:
- `invar_guard(changed=true)` for incremental
- `invar_guard()` for full verification

Never use pytest or crosshair directly.
```

---

## MCP Configuration

Continue has the most complete MCP support. Configure in `config.json`:

### Option A: Using uvx (Recommended)

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

### Option B: Using Project Venv

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

### Option C: Global Installation

```json
{
  "mcpServers": [
    {
      "name": "invar",
      "command": "python",
      "args": ["-m", "invar.mcp"]
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
    },
    {
      "name": "develop",
      "description": "USBV development workflow",
      "prompt": "Follow the USBV workflow for: {{{ input }}}\n\n1. UNDERSTAND: Analyze what needs to be done\n2. SPECIFY: Write @pre/@post contracts first\n3. BUILD: Implement following contracts\n4. VALIDATE: Run invar_guard"
    },
    {
      "name": "review",
      "description": "Adversarial code review",
      "prompt": "Review the code as an adversarial reviewer:\n1. Check if contracts have semantic value\n2. Find bugs and edge cases\n3. Question escape hatches\n4. Verify code matches contracts\n\nReport issues with severity (CRITICAL/MAJOR/MINOR)."
    }
  ]
}
```

### Using Custom Commands

```
/guard              # Run verification
/sig src/core/...   # Show signatures
/develop Add login  # Start USBV workflow
/review             # Code review
```

---

## System Message

Set a system message for all conversations:

```json
{
  "systemMessage": "You are an Invar-compliant developer. Follow these rules:\n\n1. ALWAYS write @pre/@post contracts before implementation\n2. Use invar_guard for verification, NEVER pytest directly\n3. Follow Core/Shell separation (core=pure, shell=Result[T,E])\n4. Include doctests for all public functions\n5. Follow USBV: Understand → Specify → Build → Validate"
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

### `invar-workflow.md`

```markdown
# USBV Workflow

For all implementation tasks, follow USBV:

## 1. UNDERSTAND

- What exactly needs to be done?
- Use `invar_sig` to see existing contracts
- Read relevant code

## 2. SPECIFY

- Write @pre/@post BEFORE implementation
- Add doctests for expected behavior
- Consider edge cases

## 3. BUILD

- Implement following the contracts
- Run `invar_guard` frequently

## 4. VALIDATE

- Run `invar_guard` (full verification)
- All tests must pass
- Review any warnings
```

---

## Feature Mapping

### What Works

| Invar Feature | Continue Support |
|---------------|------------------|
| USBV Workflow | ✅ Via rules + commands |
| Guard Verification | ✅ Via MCP (best support) |
| Sig/Map Tools | ✅ Via MCP |
| Core/Shell Rules | ✅ Via rules |
| Custom Commands | ✅ Similar to skills |

### What's Different

| Claude Code | Continue Alternative |
|-------------|---------------------|
| Skills (auto-routing) | customCommands |
| Hooks | Not available |
| CLAUDE.md | .continue/rules/ |
| Check-In/Final | Include in rules |

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
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
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
    },
    {
      "name": "develop",
      "description": "USBV workflow",
      "prompt": "Follow USBV for: {{{ input }}}\n1. UNDERSTAND\n2. SPECIFY (contracts first)\n3. BUILD\n4. VALIDATE (invar_guard)"
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
├── src/
│   └── your_package/
│       ├── core/          # Pure logic
│       └── shell/         # I/O operations
└── .invar/
    ├── context.md         # Project state
    └── examples/          # Pattern examples
```

---

## Troubleshooting

### MCP Tools Not Available

1. Check MCP configuration in config.json
2. Verify invar-tools: `pip show invar-tools`
3. Test MCP: `uvx invar-tools mcp`
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

1. **Leverage MCP fully** - Continue has the best MCP support
2. **Use customCommands** - They're like lightweight skills
3. **Organize rules** - One file per concern
4. **Set systemMessage** - Persistent context across chats

---

## Next Steps

- [Multi-Agent Overview](./multi-agent.md)
- [Cline Integration](./cline.md)
- [Cursor Integration](./cursor.md)
- [Aider Integration](./aider.md)
