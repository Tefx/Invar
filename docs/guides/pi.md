# Invar + Pi Integration Guide

[Pi](https://github.com/badlogic/pi-mono) is a terminal-based coding agent that reads CLAUDE.md and .claude/skills/ directly, making it the closest alternative to Claude Code for Invar users.

## Key Discovery

**Pi shares configuration with Claude Code!**

| File | Claude Code | Pi | Sharing |
|------|-------------|-----|---------|
| CLAUDE.md | ✅ Native | ✅ Reads directly | Same file |
| .claude/skills/ | ✅ Native | ✅ Reads directly | Same files |
| .claude/hooks/ | ✅ Bash | ❌ | Separate |
| .pi/hooks/ | ❌ | ✅ TypeScript | Separate |

This means you can use **both agents on the same project** without duplicating configuration.

## Quick Start

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

# Interactive mode
uvx invar-tools init
# → Select "Pi Coding Agent"

# This installs:
# - CLAUDE.md (shared with Claude Code)
# - .claude/skills/ (shared with Claude Code)
# - .pi/hooks/invar.ts (Pi-specific hooks)
# - INVAR.md, .invar/, pre-commit hooks
```

### 3. Start Pi Session

```bash
pi
# Pi will automatically read CLAUDE.md and follow USBV workflow
```

---

## What Gets Installed

| File/Directory | Purpose | Shared with Claude? |
|----------------|---------|---------------------|
| `CLAUDE.md` | Agent instructions | ✅ Yes |
| `.claude/skills/` | Workflow automation | ✅ Yes |
| `.pi/hooks/invar.ts` | pytest blocking + protocol refresh | ❌ Pi only |
| `INVAR.md` | Protocol document | ✅ Yes |
| `.invar/` | Config, context, examples | ✅ Yes |
| `.pre-commit-config.yaml` | Pre-commit hooks | ✅ Yes |

---

## Pi Hooks

Pi supports TypeScript hooks in `.pi/hooks/`. Invar installs one hook file:

### invar.ts

```typescript
// .pi/hooks/invar.ts
// - Blocks pytest/crosshair → redirects to invar guard
// - Protocol refresh at message 15, 25, 35, ...
```

**Features:**

1. **pytest/crosshair Blocking**
   - Intercepts `pytest` and `crosshair` commands
   - Returns block message: "Use invar guard instead"
   - Allows debug flags (--pdb, --cov)

2. **Protocol Refresh (Long Conversations)**
   - Message 15: Lightweight checkpoint reminder
   - Message 25+: Full protocol injection every 10 messages
   - Uses `pi.send()` to inject reminders

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

## USBV Workflow in Pi

Pi reads `.claude/skills/` and follows the same USBV workflow as Claude Code:

### 1. UNDERSTAND
- Read context.md and relevant code
- Use `invar sig` to see existing contracts

### 2. SPECIFY
- Write @pre/@post contracts first
- Add doctests for expected behavior

### 3. BUILD
- Follow the contracts from SPECIFY
- Run `invar guard --changed` frequently

### 4. VALIDATE
- Run `invar guard` (full verification)
- Ensure all requirements met

---

## Feature Comparison

| Feature | Claude Code | Pi |
|---------|-------------|-----|
| CLAUDE.md | ✅ | ✅ |
| Skills | ✅ | ✅ |
| MCP Tools | ✅ | ❌ CLI only |
| Hooks | ✅ Bash | ✅ TypeScript |
| pytest Blocking | ✅ | ✅ |
| Protocol Refresh | ✅ | ✅ |
| Pre-commit | ✅ | ✅ |

**Key differences:**
- Pi uses CLI (`invar guard`) instead of MCP (`invar_guard`)
- Pi hooks are TypeScript, Claude Code hooks are Bash

---

## Troubleshooting

### Hooks Not Working

1. Check Pi version (requires 0.30.2+):
   ```bash
   pi --version
   ```

2. Verify hook file exists:
   ```bash
   ls -la .pi/hooks/invar.ts
   ```

3. Check hook syntax:
   ```bash
   # Pi should report hook loading errors on startup
   pi
   ```

### Skills Not Recognized

1. Verify skills directory:
   ```bash
   ls -la .claude/skills/
   ```

2. Check SKILL.md format:
   ```bash
   cat .claude/skills/develop/SKILL.md | head -20
   ```

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

No migration needed! Just run:
```bash
invar init    # Select Pi to add hooks
```

Pi will read your existing CLAUDE.md and .claude/skills/.

### From Pi to Claude Code

```bash
invar init    # Select Claude Code
```

This adds Claude-specific hooks while keeping shared files.

### Using Both Agents

You can use both Claude Code and Pi on the same project:

```
your-project/
├── CLAUDE.md              # Shared
├── .claude/
│   ├── skills/            # Shared (both read)
│   └── hooks/             # Claude Code only
└── .pi/
    └── hooks/             # Pi only
```

---

## Example Session

```
$ pi

Pi: I'll read the project context.

✓ Check-In: my-project | main | clean

You: Add a function to calculate compound interest

Pi: I'll follow the USBV workflow.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First, I'll define the contract:

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

✓ Final: guard PASS | 0 errors, 0 warnings
```

---

## Next Steps

- [Multi-Agent Overview](./multi-agent.md)
- [Cursor Integration](./cursor.md)
- [Aider Integration](./aider.md)
