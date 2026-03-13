# Invar + Aider Integration Guide

> **ARCHIVE:** This guide describes historical pre-DX-91 integration approaches. Current Invar is Python-only with agent-agnostic MCP support. See [DX-91 Simplification](../proposals/DX-91-simplification.md) for current direction.
> 
> **Current approach:** Use `invar init` for any agent. See `CLAUDE.md` and `INVAR.md` for current protocol.

[Aider](https://aider.chat/) is a terminal-based AI pair programmer with Git-aware editing. This guide documents historical integration approaches.

## Quick Start (Current)

```bash
# Install Invar in the project environment
uv add --dev invar-tools invar-runtime

# Initialize project (creates CLAUDE.md, INVAR.md)
uv run invar init

# Use Aider with Invar verification
aider --lint-cmd "uv run invar guard --changed" --auto-lint
```

See `CLAUDE.md` and `INVAR.md` (installed by `invar init`) for current Invar protocol.

---

## Historical Integration

> The following describes pre-DX-91 approaches. Skills, hooks, and USBV workflow ceremony were removed per [DX-91](../proposals/DX-91-simplification.md).

### Legacy Configuration

```yaml
# .aider.conf.yml (historical)
lint-cmd: invar guard --changed
auto-lint: true
auto-commits: true
read: CONVENTIONS.md  # Pre-DX-91 file, removed per DX-91
```

### Legacy Workflow

Pre-DX-91 used USBV four-phase workflow (Understand → Specify → Build → Validate) with ceremony. Current Invar preserves the essential intent (contracts before code) without the ceremony.

---

## Current Verification

Use Invar CLI directly:

```bash
# Full verification
invar guard

# Only changed files
invar guard --changed

# Show signatures
invar sig <file>

# Symbol map
invar map
```

---

## Next Steps

- See `CLAUDE.md` in your project root for current agent guidance
- See `INVAR.md` for protocol reference
- [DX-91 Simplification](../proposals/DX-91-simplification.md) — Current architectural direction
