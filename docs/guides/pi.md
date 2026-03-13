# Invar + Pi Integration Guide

> **ARCHIVE:** This guide describes historical pre-DX-91 integration approaches. Current Invar is Python-only with agent-agnostic MCP support. See [DX-91 Simplification](../proposals/DX-91-simplification.md) for current direction.

[Pi](https://github.com/badlogic/pi-mono) is a terminal-based coding agent. This guide documents historical integration approaches; current Invar uses the same agent-agnostic protocol for all agents.

## Quick Start (DX-91)

### 1. Install Invar

```bash
# Install runtime contracts (add to your project)
pip install invar-runtime

# Development tools (use with uvx)
uvx invar-tools guard
```

### 2. Initialize Project

```bash
cd your-project

# Initialize DX-91 managed files
uvx invar-tools init

# This installs:
# - CLAUDE.md (agent guidance)
# - INVAR.md (protocol reference)
# - .pre-commit-config.yaml (verification hook)
```

### 3. Start Pi Session

```bash
pi
# Pi will read CLAUDE.md for project context
```

---

## What Gets Installed

| File/Directory | Purpose |
|----------------|---------|
| `CLAUDE.md` | Agent guidance with managed Invar block |
| `INVAR.md` | Protocol document |
| `.pre-commit-config.yaml` | Pre-commit hooks |

**Historical note:** Pre-DX-91 versions generated `.claude/skills/`, `.pi/hooks/`, and other agent-specific files. These were removed per [DX-91](../proposals/DX-91-simplification.md) in favor of a minimal, agent-agnostic surface.

---

## Verification

Pi doesn't support MCP, so use CLI commands:

```bash
# Full verification
invar guard

# Only changed files
invar guard --changed

# Show signatures
invar sig src/core/module.py

# Symbol map
invar map --top 10
```

---

## DX-91 Workflow

Current Invar follows a simplified contracts-first workflow:

1. **Specify** — Write @pre/@post contracts BEFORE implementation
2. **Build** — Implement following the contracts
3. **Validate** — Run `invar guard` for verification

**Historical note:** The four-phase USBV workflow (Understand → Specify → Build → Validate) and Check-In/Final ceremony were removed per [DX-91](../proposals/DX-91-simplification.md). The essential intent survives: write contracts before code.

---

## Feature Comparison

| Feature | Claude Code | Pi |
|---------|-------------|-----|
| CLAUDE.md | ✅ | ✅ |
| MCP Tools | ✅ | ❌ CLI only |
| Guard via CLI | ✅ | ✅ |
| Pre-commit | ✅ | ✅ |

**Key difference:** Pi uses CLI (`invar guard`) instead of MCP (`invar_guard`).

---

## Troubleshooting

### Guard Command Not Found

```bash
# Install invar-tools
pip install invar-tools

# Or use uvx (no install needed)
uvx invar-tools guard
```

---

## Migration

### From Claude Code to Pi

No migration needed. Both agents read the same `CLAUDE.md` and `INVAR.md` files installed by `invar init`.

---

## Example Session

```
$ pi

Pi: I'll read the project context from CLAUDE.md.

You: Add a function to calculate compound interest

Pi: I'll write the contract first, then implement:

@pre(lambda principal, rate, years: principal > 0 and rate >= 0 and years > 0)
@post(lambda result: result >= principal)
def compound_interest(principal: float, rate: float, years: int) -> float:
    """
    >>> compound_interest(1000, 0.05, 1)
    1050.0
    """
    ...

[implements function]

$ invar guard --changed
Guard passed. (1 file, 0 errors)
```

---

## Next Steps

- [Cursor Integration](./cursor.md)
- [Cline Integration](./cline.md)
- [Continue Integration](./continue.md)
