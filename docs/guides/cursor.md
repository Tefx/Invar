# Invar + Cursor Integration Guide

[Cursor](https://cursor.com/) is an AI-first IDE. This guide shows how to use Invar with Cursor via MCP and rule files.

## Quick Start

### 1. Install Invar

```bash
pip install invar-tools
```

### 2. Initialize Project

```bash
cd your-project
uvx invar-tools init
```

This creates:
- `CLAUDE.md` — Agent guidance (can be referenced by any agent)
- `INVAR.md` — Protocol reference
- `.pre-commit-config.yaml` — Verification hook

### 3. Create `.cursorrules` (Optional)

Create `.cursorrules` in your project root for Cursor-specific guidance:

```markdown
# Invar Development Protocol

## Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | Use invar_guard MCP tool — NOT pytest, NOT crosshair |
| **Core** | @pre/@post + doctests, NO I/O imports in core/ |
| **Shell** | Returns Result[T, E] from returns library |
| **Flow** | Contracts first → Build → Validate |

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```

## Workflow

### 1. SPECIFY
- Write @pre/@post BEFORE implementation
- Add doctests for expected behavior

### 2. BUILD
- Follow the contracts from SPECIFY
- Run invar_guard frequently

### 3. VALIDATE
- Run invar_guard (full verification)
- Ensure all requirements met

## Verification

ALWAYS use invar_guard instead of pytest:

```
# Good
invar_guard(changed=true)

# Bad - Don't use directly
pytest ...
crosshair ...
```

## Contract Example

```python
from invar_runtime import pre, post

@pre(lambda x: x > 0, "x must be positive")
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    >>> calculate(10)
    100
    """
    return x * x
```
```

### 4. Configure MCP

In Cursor settings, add MCP server configuration:

**Option A: Using uvx**

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

**Option B: Using project venv**

```json
{
  "mcpServers": {
    "invar": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  }
}
```

---

## Project Rules (Modern Approach)

Cursor supports `.cursor/rules/` directory:

### Create Rule Files

```
.cursor/
└── rules/
    ├── invar-core.mdc
    └── invar-verification.mdc
```

### `invar-core.mdc`

```markdown
---
description: Invar core development rules
globs: ["src/**/core/**/*.py"]
alwaysApply: true
---

# Core Module Rules

This is a **core** module. Follow these rules:

1. **Pure functions only** - No I/O operations
2. **Contracts required** - Every public function needs @pre/@post
3. **Doctests required** - Include usage examples
4. **No forbidden imports** - No pathlib, os.path, requests, etc.

## Example

```python
from invar_runtime import pre, post

@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def process(x: int) -> int:
    """
    >>> process(5)
    25
    """
    return x * x
```
```

### `invar-verification.mdc`

```markdown
---
description: Verification rules
globs: ["**/*.py"]
alwaysApply: true
---

# Verification

**NEVER** use pytest or crosshair directly.
**ALWAYS** use the invar_guard MCP tool.

```
# Correct
invar_guard(changed=true)

# Wrong - use invar_guard instead
pytest ...
```
```

---

## Feature Mapping

### What Works

| Invar Feature | Cursor Support |
|---------------|----------------|
| Guard Verification | ✅ Via MCP |
| Sig/Map Tools | ✅ Via MCP |
| Core/Shell Rules | ✅ Via rules |

### What's Different

| Claude Code | Cursor Alternative |
|-------------|-------------------|
| CLAUDE.md | .cursorrules or .cursor/rules/ |
| MCP tools | Same MCP protocol |

**Historical note:** Pre-DX-91 versions supported hooks, skills, and USBV workflow ceremony. These were removed per [DX-91](../proposals/DX-91-simplification.md) in favor of guard-enforced outcomes over process ceremony.

---

## Complete Setup

### Directory Structure

```
your-project/
├── .cursorrules           # Simple rules (or use .cursor/rules/)
├── .cursor/               # Optional: rules directory
│   └── rules/
│       ├── invar-core.mdc
│       └── invar-verification.mdc
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

### MCP Tools Not Working

1. Check Cursor MCP settings
2. Verify installation: `pip show invar-tools`
3. Test directly: `uvx invar-tools mcp`

### Rules Not Applied

1. Use `.cursor/rules/*.mdc` format (recommended)
2. Check `globs` patterns match your files
3. Verify `alwaysApply` setting

### Agent Uses pytest Anyway

Add explicit instruction to .cursorrules:

```markdown
## IMPORTANT

NEVER run pytest or crosshair directly.
ALWAYS use the invar_guard MCP tool for verification.
```

---

## Tips

1. **Use MDC rules** - More organized than single .cursorrules
2. **Be explicit** - "Run invar_guard" not "run tests"
3. **Glob patterns** - Target rules to specific directories

---

## Next Steps

- [Pi Integration](./pi.md)
- [Cline Integration](./cline.md)
- [Continue Integration](./continue.md)
