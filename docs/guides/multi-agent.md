# Using Invar with Different Coding Agents

> **ARCHIVE:** This guide describes historical pre-DX-91 multi-agent approaches (skills, hooks, USBV workflow ceremony). 
> Per [DX-91](../proposals/DX-91-simplification.md), Invar is now **Python-only and agent-agnostic**.
> 
> **Current approach:** Use `invar init` for any single agent. See `CLAUDE.md` and `INVAR.md` for current protocol.

---

## Current Agent Support

| Agent | Status | Setup |
|-------|--------|-------|
| **Claude Code** | ✅ MCP | `invar init` → Use MCP tools |
| **Cursor** | ✅ MCP | `invar init` → Configure MCP |
| **Cline** | ✅ MCP | `invar init` → Configure MCP |
| **Continue** | ✅ MCP | `invar init` → Configure MCP |
| **Pi** | ✅ CLI | `invar init` → Use CLI commands |
| **Aider** | ✅ CLI | `invar init` → Use CLI commands |

All agents use the same `CLAUDE.md` and `INVAR.md` files installed by `invar init`.

---

## What Works Everywhere

| Feature | Mechanism |
|---------|-----------|
| Core/Shell Separation | `CLAUDE.md` / `INVAR.md` |
| Contract Requirements | `CLAUDE.md` / `INVAR.md` |
| Guard Verification | MCP (`invar_guard`) or CLI (`invar guard`) |
| Sig/Map Tools | MCP or CLI |

---

## Current Documentation

| Document | Purpose |
|----------|---------|
| `CLAUDE.md` (project root) | Active — Agent guidance (~50 lines) |
| `INVAR.md` (project root) | Active — Protocol reference |
| [DX-91 Simplification](../proposals/DX-91-simplification.md) | Active — Authoritative direction |

---

## Historical Reference

The following sections describe pre-DX-91 approaches for historical context only.

### Pre-DX-91 Agent Table (Historical)

| Agent | Status | Notes |
|-------|--------|-------|
| Claude Code | Full | Skills, hooks, MCP |
| Pi | Full | Shared CLAUDE.md, TypeScript hooks |
| Cursor | MCP | Beta hooks support |
| Cline | MCP | Plan/Act modes |
| Aider | CLI | Auto-lint integration |
| Continue | MCP | First full MCP implementation |

### Historical Feature Parity Matrix

| Feature | Claude | Pi | Cursor | Cline | Continue | Aider |
|---------|--------|-----|--------|-------|----------|-------|
| USBV Workflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Guard via MCP | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ CLI |
| Guard via CLI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| pytest Blocking | ✅ Hook | ✅ Hook | ⚠️ Beta | ❌ | ❌ | ✅ Built-in |
| Auto-routing | ✅ Skills | ✅ Skills | ❌ | ⚠️ Modes | ⚠️ Commands | ❌ |
| Protocol Refresh | ✅ Hook | ✅ Hook | ❌ | ❌ | ❌ | ❌ |

> **Note:** USBV workflow ceremony, skills, hooks, and TypeScript support were removed per [DX-91](../proposals/DX-91-simplification.md).

### Multi-Agent Setup (Historical)

> **Note:** Multi-agent init (`invar init --claude --pi`) was removed per [DX-87](../proposals/DX-87-remove-multi-agent-init.md) as part of DX-91 simplification.

**Current approach:** Run `invar init` separately for each agent you need. Shared files (CLAUDE.md, .invar/) are safely merged.

---

## Next Steps

- See `CLAUDE.md` in your project root for current agent guidance
- See `INVAR.md` for protocol reference
- [DX-91 Simplification](../proposals/DX-91-simplification.md) — Current architectural direction
