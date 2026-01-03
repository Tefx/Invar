# Using Invar with Different Coding Agents

Invar's core value—USBV workflow, contract-driven development, and automated verification—works with any AI coding agent. This guide covers integration with popular alternatives to Claude Code.

## Agent Support Status

| Agent | Status | Setup |
|-------|--------|-------|
| **Claude Code** | ✅ Full | `invar init --claude` |
| **Pi** | ✅ Full | `invar init --pi` |
| **Multi-Agent** | ✅ Full | `invar init --claude --pi` (DX-81) |
| **Cursor** | ✅ MCP | `invar init` → select Other, add MCP |
| **Other** | 📝 Manual | `invar init` → select Other, include `AGENT.md` in prompt |

## Quick Comparison

| Agent | Instruction File | MCP Support | Hooks | Effort |
|-------|------------------|-------------|-------|--------|
| [Claude Code](../agents.md) | CLAUDE.md | ✅ Full | ✅ 4 types | Native |
| [Pi](#pi) | CLAUDE.md (shared) | ❌ | ✅ TypeScript | Native |
| [Cline](#cline) | .clinerules | ✅ Full | ❌ | Manual |
| [Cursor](#cursor) | .cursorrules | ✅ Full | ✅ Beta | Manual |
| [Aider](#aider) | CONVENTIONS.md | ⚠️ CLI | ❌ | Manual |
| [Continue](#continue) | config.yaml | ✅ Full | ❌ | Manual |

## What Works Everywhere

| Feature | Mechanism | Portability |
|---------|-----------|-------------|
| USBV Workflow | Instruction file | ✅ 100% |
| Core/Shell Separation | Instruction file | ✅ 100% |
| Contract Requirements | Instruction file | ✅ 100% |
| Guard Verification | MCP or CLI | ✅ 100% |
| Sig/Map Tools | MCP or CLI | ✅ 100% |

## What's Claude Code Specific

| Feature | Alternative |
|---------|-------------|
| Skills (auto-routing) | Pi: skills work / Others: Manual triggers |
| Hooks (pytest blocking) | Pi: TypeScript hooks / Cursor: Beta / Others: Manual |
| Commands (/audit, /guard) | Direct tool calls |

---

## Pi

**Terminal-based coding agent with CLAUDE.md support**

→ [Full Guide: Pi Integration](./pi.md)

```bash
# Setup
invar init    # Select "Pi Coding Agent"
```

**Key discovery:** Pi reads CLAUDE.md and .claude/skills/ directly — no separate configuration needed!

**Features:**
- **Same instruction file** — CLAUDE.md (shared with Claude Code)
- **Same workflow skills** — .claude/skills/ work natively
- **TypeScript hooks** — .pi/hooks/invar.ts for pytest blocking
- **Protocol injection** — `pi.send()` for long conversation support
- Pre-commit hooks

**What's installed:**
- `.pi/hooks/invar.ts` — pytest/crosshair blocking + protocol refresh

---

## Cline

**VS Code extension with Plan & Act modes**

→ [Full Guide: Cline Integration](./cline.md)

```bash
# Setup
invar init    # Select "Other (AGENT.md)", then copy to .clinerules
```

**Key features:**
- Plan Mode aligns with USBV workflow
- Full MCP support
- Open source, active community

---

## Cursor

**AI-first IDE with hooks support**

→ [Full Guide: Cursor Integration](./cursor.md)

```bash
# Setup
invar init    # Select "Other (AGENT.md)", then copy to .cursorrules
```

**Key features:**
- Hooks (beta) for command interception
- Largest user base
- .cursor/rules/ for organized rules

---

## Aider

**Terminal-based pair programmer**

→ [Full Guide: Aider Integration](./aider.md)

```bash
# Quick setup - use with auto-lint
aider --lint-cmd "invar guard --changed" --auto-lint
```

**Key features:**
- Built-in auto-lint/test verification
- Git-aware editing
- CONVENTIONS.md as persistent memory

---

## Continue

**Open-source VS Code/JetBrains extension**

→ [Full Guide: Continue Integration](./continue.md)

```bash
# Quick setup - add to .continue/config.yaml
```

**Key features:**
- First full MCP implementation
- customCommands for workflows
- Works with any model

---

## MCP Configuration

All MCP-supporting agents can use Invar's tools:

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

Or if installed in a virtual environment:

```json
{
  "mcpServers": {
    "invar": {
      "command": "/path/to/project/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  }
}
```

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `invar_guard` | Smart verification (static + doctests + symbolic) |
| `invar_sig` | Show function signatures and contracts |
| `invar_map` | Symbol map with reference counts |

---

## Feature Parity Matrix

| Feature | Claude | Pi | Cursor | Cline | Continue | Aider |
|---------|--------|-----|--------|-------|----------|-------|
| USBV Workflow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Guard via MCP | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ CLI |
| Guard via CLI | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| pytest Blocking | ✅ Hook | ✅ Hook | ⚠️ Beta | ❌ | ❌ | ✅ Built-in |
| Auto-routing | ✅ Skills | ✅ Skills | ❌ | ⚠️ Modes | ⚠️ Commands | ❌ |
| Protocol Refresh | ✅ Hook | ✅ Hook | ❌ | ❌ | ❌ | ❌ |
| Plan Mode | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

---

## Choosing an Agent

| If you want... | Choose |
|----------------|--------|
| Full Invar experience | Claude Code |
| Terminal + skill sharing | Pi |
| IDE integration + hooks | Cursor |
| Open source + Plan Mode | Cline |
| Terminal + git-aware | Aider |
| Model flexibility | Continue |

---

## Multi-Agent Setup (DX-81)

**Use multiple agents in the same project**

```bash
# Setup both Claude Code and Pi
invar init --claude --pi

# Or interactive mode (select multiple with Space key)
invar init  # Choose both "Claude Code" and "Pi Coding Agent"
```

**What gets installed:**
- `.claude/hooks/` — Claude Code hooks (4 files)
- `.pi/hooks/` — Pi hooks (1 file)
- Shared files: `CLAUDE.md`, `.claude/skills/`, `.invar/`

**Use cases:**
- **Team collaboration** — Different team members use different agents
- **Agent switching** — Have both configured, use either
- **Open source** — Contributors can choose their preferred agent

**File structure:**
```
project/
├── CLAUDE.md              # Shared by both agents
├── .claude/
│   ├── skills/            # Shared by both agents
│   └── hooks/             # Claude Code only
├── .pi/
│   └── hooks/             # Pi only
└── .mcp.json              # Claude Code MCP config
```

**No conflicts:** All files designed for coexistence. Shared files (CLAUDE.md, skills) work identically for both agents. Isolated files (.claude/hooks/, .pi/hooks/) never interfere.

---

## Migration Path

### Adding a Second Agent

Already using Claude Code or Pi? Add the other agent:

```bash
# Already have Claude Code, add Pi
invar init --pi

# Already have Pi, add Claude Code
invar init --claude

# Or use combined command (safe, no duplicates)
invar init --claude --pi
```

All shared files (CLAUDE.md, skills) are safely merged. Only agent-specific hooks are added.

### From Claude Code to Pi

No migration needed! Pi reads the same files:
- CLAUDE.md → works in Pi
- .claude/skills/ → works in Pi
- Just run `invar init --pi` to add Pi hooks

### From Claude Code to Others

1. Run `invar init` → select "Other (AGENT.md)"
2. Copy AGENT.md content to target instruction file
3. Configure MCP (if supported)

### From Others to Claude Code

1. Run `invar init --claude`
2. All features auto-configured (skills, hooks, MCP)

---

## Troubleshooting

### MCP Connection Issues

```bash
# Test MCP server directly
uvx invar-tools mcp

# Check if invar is installed
pip show invar-tools
```

### Guard Not Found

```bash
# Install invar-tools
pip install invar-tools

# Or use uvx (no install needed)
uvx invar-tools guard
```

### Instruction File Not Loaded

Each agent has specific file locations:
- Cline: `.clinerules` in project root
- Cursor: `.cursorrules` or `.cursor/rules/*.mdc`
- Aider: `CONVENTIONS.md` in project root
- Continue: `.continue/config.yaml`

---

## Next Steps

- [Pi Integration Guide](./pi.md) — Native support, shares CLAUDE.md
- [Cline Integration Guide](./cline.md)
- [Cursor Integration Guide](./cursor.md)
- [Aider Integration Guide](./aider.md)
- [Continue Integration Guide](./continue.md)
- [Claude Code Setup](../agents.md) (native)
