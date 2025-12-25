# DX-43: Cross-Platform Distribution

> **"Invar everywhere: from Claude Code to Cursor to manual."**

**Status:** Draft
**Created:** 2025-12-25
**Updated:** 2025-12-25
**Origin:** Merged from DX-35 Phase 5 + DX-36 Phase 5-6 + DX-11 remnants
**Effort:** Medium
**Risk:** Low

## Problem Statement

Current state:
- Invar tools work with any platform (CLI)
- Workflow skills only work with Claude Code
- No support for Cursor/Windsurf `.cursorrules`
- `invar init` doesn't create skill templates

**Goal:** Make Invar protocol accessible across platforms.

## Platform Tiers

| Tier | Platform | Current | After DX-43 |
|------|----------|---------|-------------|
| **Tier 1** | Claude Code | Full (skills, MCP, sub-agents) | ✅ Same |
| **Tier 2** | Cursor/Windsurf | CLI only | + `.cursorrules` template |
| **Tier 3** | Others | CLI only | + INVAR.md reference |

## Proposed Features

### 1. `invar init --claude` (from DX-36 Phase 5)

Generate Claude Code skill files automatically:

```bash
$ invar init --claude

Created:
  .claude/skills/investigate/SKILL.md
  .claude/skills/propose/SKILL.md
  .claude/skills/develop/SKILL.md
  .claude/skills/review/SKILL.md
  .claude/settings.json (MCP server config)
```

### 2. `invar init --cursor` (new)

Generate Cursor-compatible rules file:

```bash
$ invar init --cursor

Created:
  .cursorrules
```

**`.cursorrules` template:**

```markdown
# Invar Protocol for Cursor

## Check-In (Start of session)
Run: `invar guard --changed`

## Check-Out (Before commit)
Run: `invar guard`

## Tool Preferences
- Use `invar guard` instead of `pytest`
- Use `invar sig <file>` to see contracts
- Use `invar map --top 10` for codebase overview

## Architecture
- src/*/core/ — Pure logic, no I/O
- src/*/shell/ — I/O with Result[T, E]

## Quick Reference
See: INVAR.md
```

### 3. Migration Documentation (from DX-36 Phase 6 + DX-11)

Create migration guide for existing projects:

```bash
$ invar migrate --from v4 --to v5

Migration Guide:
1. Run `invar init --claude` to create skill files
2. Update CLAUDE.md (see diff below)
3. Test with `invar guard`

CLAUDE.md changes:
- Remove workflow details (now in skills)
- Keep project-specific rules only
+ Add workflow triggers
```

**From DX-11:** The `invar migrate` command was originally proposed in DX-11 for documentation restructuring. It should support:

```bash
# Detect current version and suggest migration steps
$ invar migrate --detect
Current: v4.2 (ICIDIV workflow in CLAUDE.md)
Target:  v5.0 (USBV workflow in skills)

Recommended steps:
1. Run: invar init --claude
2. Remove: CLAUDE.md workflow section (lines 45-120)
3. Verify: invar guard

# Dry-run mode
$ invar migrate --from v4 --to v5 --dry-run
Would create: .claude/skills/develop/SKILL.md
Would create: .claude/skills/investigate/SKILL.md
Would modify: CLAUDE.md (remove 75 lines)
```

## Implementation Plan

### Phase 1: CLI Updates

```
src/invar/shell/
├── init_cmd.py      # Update with --claude, --cursor flags
└── migrate_cmd.py   # New migration command
```

### Phase 2: Templates

```
src/invar/templates/
├── claude/
│   ├── investigate.md
│   ├── propose.md
│   ├── develop.md
│   └── review.md
├── cursorrules.template
└── migration/
    └── v4_to_v5.md
```

### Phase 3: Documentation

- Platform comparison guide
- Setup instructions per platform
- Migration guide for existing projects

## Success Criteria

- [ ] `invar init --claude` creates skill files
- [ ] `invar init --cursor` creates .cursorrules
- [ ] Migration guide documented
- [ ] Templates are self-contained (no external deps)

## Related

- DX-11: Documentation Restructure for Multi-Agent Support (archived, migrate command origin)
- DX-35: Workflow-based Phase Separation (Phase 5 origin)
- DX-36: Documentation Restructuring (Phase 5-6 origin)
- Templates: `src/invar/templates/`
