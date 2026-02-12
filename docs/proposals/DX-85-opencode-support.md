# DX-85: OpenCode Agent Support (Consolidated)

**Status**: Draft
**Created**: 2026-01-05
**Updated**: 2026-02-12 (Aligned with latest OpenCode docs + single-agent init)
**Priority**: Medium
**Type**: Enhancement

---

## Executive Summary

This proposal outlines native support for **OpenCode** agents in Invar.

OpenCode uses **`AGENTS.md`** as the project rule file (created by OpenCode's `/init`) and **`opencode.json`** as the per-project config file (including MCP server configuration).

**Key Decisions (sources: user decision + OpenCode docs):**
- **Instruction file**: `AGENTS.md` (OpenCode project rules).
- **Project config**: `opencode.json` (MCP + instructions aggregation).
- **Optional config dir**: `.opencode/` (skills/agents/commands/plugins) — only created when needed.
- **Single-agent init only**: `invar init --opencode` is supported; multi-agent combined init is intentionally not supported.
- **Manual coexistence without ambiguity**: if `.claude/skills/` exists, do **not** generate `.opencode/skills/` to avoid duplicate skill definitions.

---

## 1. Architecture

### 1.1 File Structure
OpenCode introduces its own file conventions, separate from Claude Code:

```
project_root/
├── AGENTS.md          # OpenCode project rules (loaded by OpenCode)
├── opencode.json      # OpenCode project config (MCP, instructions, agents, permissions)
├── .opencode/         # Optional OpenCode project dir (skills/agents/commands/plugins)
│   └── ...
├── CLAUDE.md          # Claude Code/Pi instructions (existing, independent)
└── .invar/            # Shared Invar configuration
```

### 1.2 Coexistence Strategy
Because OpenCode uses `AGENTS.md` (and treats `CLAUDE.md` only as a fallback), coexistence is primarily a documentation + file layout concern.

Invar's approach is:
1. **Native OpenCode setup** writes `AGENTS.md` + `opencode.json`.
2. **Other agent setup** (Claude/Pi) continues to write `CLAUDE.md` + `.claude/*`.
3. **Avoid duplicate skills**: if `.claude/skills/` exists, do not generate `.opencode/skills/` (OpenCode can discover `.claude/skills/` via compatibility paths).

| Agent | Instruction File | Config Dir | Status |
|-------|------------------|------------|--------|
| Claude Code | `CLAUDE.md` | `.claude/` | ✅ Supported |
| Pi | `CLAUDE.md` | `.pi/` | ✅ Supported |
| **OpenCode** | **`AGENTS.md`** | **`.opencode/`** | **PROPOSED** |

---

## 2. Implementation Plan

### 2.1 Init Command (`invar init`)
Support explicit OpenCode initialization:

```bash
# Initialize OpenCode only
invar init --opencode
```

**Behavior:**
- Generates `AGENTS.md` (OpenCode protocol & instructions).
- Generates/merges `opencode.json` (OpenCode config) with:
  - `mcp.invar` (local MCP server)
  - `instructions` including `INVAR.md`
- Creates `.opencode/` only if we are installing OpenCode-native skills/agents/commands.
- Does **not** generate `.mcp.json` (OpenCode config uses `opencode.json`, not `.mcp.json`).

### 2.2 Configuration Updates
Update `src/invar/shell/commands/init.py` to recognize the new agent type.

```python
AGENT_CONFIGS = {
    "opencode": {
        "name": "OpenCode",
        "category": "opencode",
        "files": [
            ("AGENTS.md", "Agent instructions (OpenCode)"),
            ("opencode.json", "OpenCode project config (MCP + instructions)"),
            (".opencode/", "OpenCode project directory (skills/agents/commands/plugins)"),
        ]
    }
}
```

### 2.3 Detection Logic
Auto-detect OpenCode environments in `init.py`:

```python
def detect_opencode(path: Path) -> bool:
    # 1. Check for instruction file
    if (path / "AGENTS.md").exists():
        return True
    # 2. Check for project config
    if (path / "opencode.json").exists():
        return True
    # 3. Check for config folder
    if (path / ".opencode").exists():
        return True
    return False
```

### 2.4 Template Management
- Create `src/invar/templates/protocol/opencode/AGENTS.md`.
- Create `src/invar/templates/config/opencode.json` (project config template).
- `invar update` will sync `AGENTS.md` + merge `opencode.json` when OpenCode is detected.
- **Skills policy:**
  - If `.claude/skills/` exists: do not generate `.opencode/skills/`.
  - Else: generate `.opencode/skills/<name>/SKILL.md` for Invar skills.

---

## 3. OpenCode Specific Protocol (`AGENTS.md`)

The `AGENTS.md` template will define the **Invar × OpenCode** protocol:

```markdown
# OpenCode Protocol

> **System Prompt**: You are an OpenCode agent working in an Invar project.

## Tool Usage
- **Verification**: MUST use `invar_guard` (MCP).
- **Exploration**: MUST use `invar_map` (MCP) first.
- **Reading**: Use `invar_sig` (MCP) for signature scans.

## Workflow (USBV)
1. **Understand**: Read task, map structure.
2. **Specify**: Define contracts (@pre/@post).
3. **Build**: Implement core logic + shell adapters.
4. **Validate**: Run `invar_guard` until pass.

## Rules
- **Check-In**: Required at session start.
- **Final**: Required at task completion.
- **Core/Shell**: Strictly separate pure logic from I/O.
```

### 3.1 MCP wiring (OpenCode)

OpenCode configures MCP servers in `opencode.json` under the `mcp` field.

Example (local MCP server):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "invar": {
      "type": "local",
      "command": ["uvx", "invar-tools", "mcp"],
      "enabled": true
    }
  },
  "instructions": ["INVAR.md"]
}
```

---

## 4. Documentation

- Update `docs/guides/multi-agent.md` to include OpenCode (`AGENTS.md`).
- Create `docs/guides/opencode.md` detailing the setup.

---

## 5. Success Criteria

1.  `invar init --opencode` creates/merges `AGENTS.md` and `opencode.json`.
2.  OpenCode correctly uses `AGENTS.md` as its project rules file.
3.  OpenCode MCP tools are available via `opencode.json` → `mcp` configuration.
4.  Manual coexistence works without ambiguity:
    - both `AGENTS.md` and `CLAUDE.md` can exist
    - `.opencode/skills/` is not generated when `.claude/skills/` exists

---

## References

- OpenCode Intro (/init creates `AGENTS.md`): https://opencode.ai/docs/
- OpenCode Rules (AGENTS.md precedence + `instructions`): https://opencode.ai/docs/rules/
- OpenCode Config (`opencode.json` locations + merge semantics): https://opencode.ai/docs/config/
- OpenCode MCP servers (`mcp` config format): https://opencode.ai/docs/mcp-servers/
- OpenCode Skills discovery paths (includes `.opencode/skills/` and `.claude/skills/`): https://opencode.ai/docs/skills/
