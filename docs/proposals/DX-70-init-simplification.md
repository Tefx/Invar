# DX-70: Init Command Simplification

**Status:** ✅ Complete
**Created:** 2024-12-30
**Author:** Claude

## Problem Statement

The current `invar init` command has multiple issues:

1. **`claude /init` integration fails** - Interactive subprocess cannot be reliably executed
2. **Too many CLI options** - `--yes`, `--no-hooks`, `--no-skills`, `--no-dirs`, `--force`, `--reset` are confusing
3. **Inconsistent behavior** - Different code paths for `--claude` vs normal init
4. **No agent selection** - Hardcoded for Claude Code, no support for other agents
5. **Config file location** - `invar.toml` in root directory clutters project

### Evidence

User reports:
- "invar init --claude 卡在 'claude /init'" (hanging issue)
- "太复杂了，不需要这么多选项"

## Solution

### Core Principles

```
┌────────────────────────────────────────────────────────┐
│  invar init = SAFE MERGE                               │
│                                                        │
│  • File doesn't exist → Create                         │
│  • File exists → Merge (update invar regions,          │
│                         preserve user content)         │
│  • Never overwrite user content                        │
│  • Never delete files                                  │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  Full Reset = invar uninstall && invar init            │
│                                                        │
│  • Two-step operation prevents accidents               │
│  • uninstall has confirmation prompt                   │
└────────────────────────────────────────────────────────┘
```

### CLI Interface (Simplified)

```
invar init [OPTIONS]

Options:
  --claude          Auto-select Claude Code, skip all prompts
  --preview         Show what would be done (dry run)
```

**Removed options:**
- ~~`--yes`~~ → No Y/N confirmation, use menu selection
- ~~`--no-hooks`~~ → Uncheck in menu
- ~~`--no-skills`~~ → Uncheck in menu
- ~~`--no-dirs`~~ → Uncheck in menu
- ~~`--force`~~ → Not needed, always merge
- ~~`--reset`~~ → Use `invar uninstall && invar init`

### Interactive Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        invar init                               │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  --claude flag?      │
                    └─────────────────────┘
                      │                │
                  Yes │                │ No
                      │                ▼
                      │      ┌──────────────────────┐
                      │      │ Step 1: Select Agent │
                      │      │ [Multi-select menu]  │
                      │      └──────────────────────┘
                      │                │
                      │                ▼
                      │      ┌──────────────────────┐
                      │      │ Step 2: Select Files │
                      │      │ [Checkbox menu]      │
                      │      └──────────────────────┘
                      │                │
                      └───────┬────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Execute file gen   │
                    └─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  Show completion    │
                    │  (with Claude tip)  │
                    └─────────────────────┘
```

### UI Design

#### Step 1: Agent Selection (interactive mode only)

```
Invar v1.7.0 - Project Setup
=============================

Select code agent(s):  [Space to toggle, Enter to confirm]

  ▸ ◉ Claude Code
    ○ Other (AGENT.md)
```

#### Step 2: File Selection (interactive mode only)

```
File Selection:  [Space to toggle, Enter to confirm]
Existing files will be MERGED (your content preserved).

  Required:
    ◉ INVAR.md                  Protocol and contract rules
    ◉ .invar/                   Config, context, examples

  Optional:
  ▸ ◉ .pre-commit-config.yaml   Verification before commit
    ◉ src/core/                 Pure logic directory
    ◉ src/shell/                I/O operations directory

  Claude Code:
    ◉ CLAUDE.md                 Agent instructions
    ◉ .claude/skills/           Workflow automation
    ◉ .claude/commands/         User commands (/audit, /guard)
    ◉ .claude/hooks/            Tool guidance
    ◉ .mcp.json                 MCP server config
```

#### Execution Output

```
Creating files...
  ✓ INVAR.md                    created
  ✓ .invar/                     created
  ↻ CLAUDE.md                   merged
  ✓ .claude/skills/             created
  ✓ .claude/commands/           created
  ✓ .claude/hooks/              created
  ✓ .mcp.json                   created
  ✓ .pre-commit-config.yaml     created
  ✓ src/core/                   created
  ✓ src/shell/                  created

✓ Initialized Invar v1.7.0

📌 If you run 'claude /init' afterward, run 'invar init' again to restore protocol.
```

### `--claude` Quick Mode

```
$ invar init --claude

Invar v1.7.0 - Quick Setup (Claude Code)
=========================================
Existing files will be MERGED (your content preserved).

  ✓ INVAR.md                    created
  ✓ .invar/                     created
  ✓ CLAUDE.md                   created
  ...

✓ Initialized Invar v1.7.0

📌 If you run 'claude /init' afterward, run 'invar init' again to restore protocol.
```

### File Categories

```python
from invar import __version__

FILE_CATEGORIES = {
    "required": [
        ("INVAR.md", "Protocol and contract rules"),
        (".invar/", "Config, context, examples"),
    ],
    "optional": [
        (".pre-commit-config.yaml", "Verification before commit"),
        ("src/core/", "Pure logic directory"),
        ("src/shell/", "I/O operations directory"),
    ],
    "claude": [
        ("CLAUDE.md", "Agent instructions"),
        (".claude/skills/", "Workflow automation"),
        (".claude/commands/", "User commands (/audit, /guard)"),
        (".claude/hooks/", "Tool guidance"),
        (".mcp.json", "MCP server config"),
    ],
    "generic": [
        ("AGENT.md", "Universal agent instructions"),
    ],
}

AGENT_CONFIGS = {
    "claude": {"name": "Claude Code", "category": "claude"},
    "generic": {"name": "Other (AGENT.md)", "category": "generic"},
    # Future: "cursor", "windsurf", etc.
}
```

### Config File Location Change

| Old | New |
|-----|-----|
| `invar.toml` (root) | `.invar/config.toml` |

**Backward compatibility:** Still reads from `pyproject.toml` and `invar.toml`.

### Output Status Icons

| Icon | Meaning |
|------|---------|
| ✓ | Created |
| ↻ | Merged |
| ○ | Skipped (by user) |
| ⚠ | Warning |

## Implementation Checklist

- [x] Fix .pre-commit-config.yaml marker issue (already done)
- [ ] Create simplified init command
  - [ ] Remove `run_claude_init()` function
  - [ ] Remove `--yes`, `--no-*`, `--force`, `--reset` options
  - [ ] Add interactive agent selection menu
  - [ ] Add interactive file selection menu
  - [ ] Implement `--claude` quick mode
- [ ] Change config file location
  - [ ] Generate `.invar/config.toml` instead of `invar.toml`
  - [ ] Update uninstall to handle new location
  - [ ] Keep read compatibility for old locations
- [ ] Create AGENT.md template for generic agent support
- [ ] Update tests
- [ ] Update documentation
  - [ ] README.md
  - [ ] Quick Start guide
  - [ ] Agent support documentation

## Alternatives Considered

### Alternative 1: Keep `claude /init` integration
Rejected: Interactive subprocess is unreliable, causes hanging.

### Alternative 2: Keep all CLI options
Rejected: Too complex, confusing for users.

### Alternative 3: Interactive menu (chosen)
Pros: Intuitive, flexible, shows all options at once.
Cons: Requires terminal UI library.

## Dependencies

- Rich library for terminal UI (already a dependency)
- `questionary>=2.0` - Interactive prompts with cursor-based selection (arrow keys + space to toggle)

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing scripts using old flags | Show deprecation warnings, support old flags temporarily |
| Interactive menu in non-TTY | Detect TTY, fall back to `--claude` behavior |
| Config migration | Keep reading old locations, only write to new |
