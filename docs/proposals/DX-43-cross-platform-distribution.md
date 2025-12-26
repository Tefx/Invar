# DX-43: Cross-Platform Distribution

> **"Invar everywhere: from Claude Code to Cursor to manual."**

**Status:** ✅ Complete (implemented in DX-49)
**Created:** 2025-12-25
**Updated:** 2025-12-26
**Origin:** Merged from DX-35 Phase 5 + DX-36 Phase 5-6 + DX-11 remnants
**Effort:** Medium → **Absorbed by DX-49**
**Risk:** Low

## Resolution

All features from DX-43 were implemented as part of DX-49 (Protocol Distribution Unification).

### Implementation Status

| Feature | Proposed | Implemented | How |
|---------|----------|-------------|-----|
| Skills auto-creation | `invar init --claude` | ✅ `invar init` (default) | `--skills` flag, default ON |
| Cursor support | `invar init --cursor` | ✅ Auto-detect | `detect_agent_configs()` finds/creates `.cursorrules` |
| Aider support | — | ✅ Auto-detect | Creates `.aider.conf.yml` |
| Templates | Manual | ✅ `templates/` directory | Jinja2 with syntax switching |
| Migration command | `invar migrate` | ❌ Not needed | `invar init -y` handles upgrades |

### Why No Migrate Command

1. **New projects**: `invar init` creates everything automatically
2. **Existing projects**: `invar init -y` detects configs and fills gaps
3. **No complex migration**: v4→v5 is documentation-only (no code changes)
4. **Idempotent init**: Running `invar init` multiple times is safe

### Platform Tiers (Achieved)

| Tier | Platform | Support Level |
|------|----------|---------------|
| **Tier 1** | Claude Code | Full (skills, MCP, commands) |
| **Tier 2** | Cursor/Windsurf | `.cursorrules` + CLI |
| **Tier 2** | Aider | `.aider.conf.yml` + CLI |
| **Tier 3** | Others | INVAR.md + CLI |

## Files Implemented (DX-49)

```
src/invar/templates/
├── cursorrules.template          # Cursor/Windsurf rules
├── aider.conf.yml.template       # Aider configuration
├── skills/                       # Claude Code skills
│   ├── develop/SKILL.md.jinja
│   ├── investigate/SKILL.md.jinja
│   ├── propose/SKILL.md.jinja
│   └── review/SKILL.md.jinja
└── commands/                     # Claude Code commands
    ├── audit.md.jinja
    └── guard.md.jinja

src/invar/shell/templates.py
├── detect_agent_configs()        # Auto-detect claude/cursor/aider
├── create_agent_config()         # Create from template
└── AGENT_CONFIGS                 # Config definitions
```

## Related

- **DX-49**: Protocol Distribution Unification (supersedes this proposal)
- DX-11: Documentation Restructure (archived)
- DX-35: Workflow-based Phase Separation (archived)
- DX-36: Documentation Restructuring (archived)
