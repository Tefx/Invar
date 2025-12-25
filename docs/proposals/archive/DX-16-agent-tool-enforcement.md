# DX-16: Agent Tool Enforcement

**Status:** ✅ Complete (Phase 1 implemented, Phase 2 extracted to DX-40)
**Priority:** High
**Created:** 2025-12-22
**Archived:** 2025-12-25

## Resolution

| Phase | Description | Resolution |
|-------|-------------|------------|
| Phase 1 | MCP Server + Strong Prompt | ✅ Implemented |
| Phase 2 | Smart Hook (PreToolUse) | → Extracted to **DX-40** |

## Implemented Components (Phase 1)

- `src/invar/mcp/` — MCP server with `invar_guard`, `invar_sig`, `invar_map` tools
- Strong prompt instructions in MCP server configuration
- Tool substitution rules documented
- `invar init` integration for MCP server setup

## Problem

Even with clear documentation in CLAUDE.md, agents default to generic tools instead of Invar-specific tools:

| Desired Behavior | Actual Behavior |
|------------------|-----------------|
| `invar guard --changed` | `Bash("pytest ...")` |
| `invar guard --prove` | `Bash("crosshair ...")` |
| `invar sig <file>` | `Read` entire .py file |
| `invar map --top 10` | `Grep` for function definitions |

**Root Cause:** Documentation is Human-Native (requires reading and remembering), not Agent-Native (automatic enforcement).

## Agent-Native Analysis

| Level | Type | Agent-Native? | Effect |
|-------|------|---------------|--------|
| Level 1: Documentation | Education | ❌ Human-Native | ~10% |
| Level 2: Skills | Shortcuts | ⚠️ Mostly Human-Native | ~20% |
| Level 3: Hooks | Constraints | ✅ Agent-Native | ~95% |
| Level 4: MCP Server | Environment Design | ✅ Agent-Native | ~50-60% |

**Key Insight:** Level 1-2 rely on agent "remembering" rules. Level 3-4 modify the environment.

## Solution

### Phase 1: MCP Server + Strong Prompt (Implemented)

Create `invar-mcp` server with:
- First-class tools: `invar_guard`, `invar_sig`, `invar_map`
- Strong instructions in system prompt
- Clear tool substitution rules

**Expected Effect:** ~50-60%

### Phase 2: Smart Hook (Proposed)

Add PreToolUse hook with intelligent pattern matching:

```python
# Only block basic patterns, allow advanced usage
blocked_patterns = [
    r"pytest\s+[\w/]+\.py(\s+--doctest-modules)?\s*$",
    r"crosshair\s+check\s+[\w/]+\.py\s*$",
]

allowed_patterns = [
    r"pytest.*(-k\s|--pdb|--cov|--tb=|--lf|--ff)",  # Debug/specific tests
    r"crosshair\s+(watch|diffbehavior|cover)",       # Advanced features
]
```

**Expected Effect:** ~95%

## Implementation

### Phase 1: MCP Server

Location: `src/invar/mcp/`

```
src/invar/mcp/
├── __init__.py
├── server.py      # MCP server entry point
└── __main__.py    # CLI entry: python -m invar.mcp
```

Tools provided:
1. `invar_guard` - Smart Guard verification
2. `invar_sig` - Function signatures and contracts
3. `invar_map` - Symbol map with reference counts

Strong prompt instructions:
- MANDATORY tool substitution rules
- Common mistakes to avoid
- Correct patterns to follow

### Phase 2: Smart Hook

Location: `.claude/hooks/invar_tool_redirect.py`

Features:
- Intelligent pattern matching
- Block basic pytest/crosshair (redirectable to invar)
- Allow advanced usage (debugging, coverage, etc.)
- Clear error messages with correct alternative

## Configuration

### MCP Server Registration

```json
// ~/.claude/settings.json or project .claude/settings.json
{
  "mcpServers": {
    "invar": {
      "command": "python",
      "args": ["-m", "invar.mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

### Hook Registration (Phase 2)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "python .claude/hooks/invar_tool_redirect.py"
      }
    ]
  }
}
```

## Success Metrics

| Metric | Before | Phase 1 | Phase 2 |
|--------|--------|---------|---------|
| Agent uses invar for verification | ~10% | ~50-60% | ~95% |
| False positive blocks | N/A | 0% | <5% |
| User experience | N/A | Smooth | Smooth |

## Risks and Mitigations

### Phase 1 Risks
- **Risk:** Agent still uses Bash for pytest
- **Mitigation:** Strong prompt with MANDATORY language
- **Severity:** Medium (50-60% still effective)

### Phase 2 Risks
- **Risk:** Hook blocks legitimate pytest usage
- **Mitigation:** Smart pattern matching allows advanced usage
- **Severity:** Low (allow patterns cover edge cases)

## Timeline

- [x] Phase 1a: Create proposal (this document)
- [x] Phase 1b: Implement MCP server
- [x] Phase 1c: Integrate with `invar init`
- [ ] Phase 2: Implement smart hook (future)

## Init Integration

`invar init` now automatically:
1. Creates `.invar/mcp-server.json` (universal config)
2. Creates `.invar/mcp-setup.md` (setup instructions)
3. If `.claude/` exists, updates `.claude/settings.json`

Safe merge: preserves existing settings, only adds invar MCP server.

## References

- Agent-Native design principles: INVAR.md
- MCP specification: https://modelcontextprotocol.io/
- Claude Code hooks: https://docs.anthropic.com/claude-code/hooks
