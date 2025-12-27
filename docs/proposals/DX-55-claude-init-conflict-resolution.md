# DX-55: Claude /init Conflict Resolution

**Status:** Draft
**Created:** 2025-12-27
**Problem:** Running Claude `/init` after `invar init` destroys Invar configuration

## Problem Statement

### Scenario

```
1. User runs: invar init
   → Creates CLAUDE.md with <!--invar:managed-->, <!--invar:project-->, <!--invar:user--> regions
   → Creates .claude/skills/, .mcp.json, etc.

2. Time passes...

3. User runs: claude /init (or clicks "Initialize" in Claude Code)
   → Claude overwrites CLAUDE.md with fresh project analysis
   → All Invar regions lost ❌
```

### Impact

| File | Consequence |
|------|-------------|
| `CLAUDE.md` | All Invar regions destroyed |
| `.claude/skills/` | May be overwritten or conflicted |
| `.mcp.json` | May be overwritten |
| `INVAR.md` | Protected by pre-commit (safe) |
| `.invar/` | Not touched by Claude (safe) |

### Why This Happens

1. Claude `/init` doesn't know about Invar's region markers
2. Invar doesn't protect CLAUDE.md like it protects INVAR.md
3. No mechanism to merge content from both tools

## Design Goals

1. **Detection**: Recognize when CLAUDE.md has been overwritten
2. **Recovery**: Restore Invar regions without losing Claude's content
3. **Prevention**: Warn users before the problem occurs
4. **Transparency**: Make the conflict and resolution visible

## Detailed Design

### Phase 1: Detection & Warning (Immediate)

#### 1.1 Region Detection in `invar update`

```python
def detect_claude_md_state(path: Path) -> Literal["intact", "partial", "missing", "absent"]:
    """
    Detect the state of CLAUDE.md Invar regions.

    Returns:
        "intact": All regions present and valid
        "partial": Some regions missing (corruption)
        "missing": File exists but no Invar regions (overwritten)
        "absent": File doesn't exist
    """
    if not path.exists():
        return "absent"

    content = path.read_text()
    has_managed = "<!--invar:managed-->" in content
    has_user = "<!--invar:user-->" in content

    if has_managed and has_user:
        return "intact"
    elif has_managed or has_user:
        return "partial"
    else:
        return "missing"  # File exists but no Invar markers
```

#### 1.2 Warning Output

When `invar update` detects "missing" state:

```
⚠ CLAUDE.md exists but has no Invar regions.
  This usually happens after running 'claude /init'.

  Current CLAUDE.md content will be preserved in <!--invar:user--> section.
  Invar managed sections will be restored from template.

  Options:
  A: Merge (recommended) - Restore regions, keep existing content in user section
  B: Overwrite - Replace entirely with Invar template
  C: Skip - Leave CLAUDE.md unchanged

  Choice? [A/B/C]
```

#### 1.3 Init-time Warning

When `invar init` completes:

```
✓ Invar initialized successfully.

⚠ Note: If you later run 'claude /init', it will overwrite CLAUDE.md.
  Run 'invar update' afterward to restore Invar configuration.
```

### Phase 2: Smart Merge (Core Feature)

#### 2.1 Merge Strategy

```
Before (Claude-generated CLAUDE.md):
┌─────────────────────────────────────┐
│ # Project Guide                     │
│                                     │
│ This project uses Python 3.12...   │
│ Key files: src/main.py, tests/...  │
│                                     │
│ ## Architecture                     │
│ [Claude's analysis]                 │
└─────────────────────────────────────┘

After (Merged):
┌─────────────────────────────────────┐
│ <!--invar:managed version="5.0"-->  │
│ # Project Development Guide         │
│ [Invar managed content]             │
│ <!--/invar:managed-->               │
│                                     │
│ <!--invar:project-->                │
│ [Project-specific if applicable]    │
│ <!--/invar:project-->               │
│                                     │
│ <!--invar:user-->                   │
│ ## Claude Analysis (Preserved)      │  ← Original content moved here
│                                     │
│ This project uses Python 3.12...   │
│ Key files: src/main.py, tests/...  │
│                                     │
│ ## Architecture                     │
│ [Claude's analysis]                 │
│ <!--/invar:user-->                  │
└─────────────────────────────────────┘
```

#### 2.2 Implementation

```python
@pre(lambda content: isinstance(content, str))
@post(lambda result: "<!--invar:managed-->" in result)
def merge_claude_md(
    existing_content: str,
    managed_template: str,
    project_additions: str | None = None
) -> str:
    """
    Merge existing CLAUDE.md content with Invar regions.

    Args:
        existing_content: Current CLAUDE.md (possibly Claude-generated)
        managed_template: Invar managed section template
        project_additions: Optional project-specific content

    Returns:
        Merged content with all regions

    >>> merge_claude_md("# My Project\\nSome content", "<managed>", None)
    '...<!--invar:managed-->...<managed>...<!--invar:user-->...# My Project...'
    """
    # Check if already has Invar regions
    if "<!--invar:managed-->" in existing_content:
        # Extract and preserve user region content
        existing_user = extract_region(existing_content, "user")
        # Rebuild with fresh managed + preserved user
        return build_claude_md(managed_template, project_additions, existing_user)

    # No Invar regions - treat entire content as user content
    user_content = f"## Claude Analysis (Preserved)\n\n{existing_content}"
    return build_claude_md(managed_template, project_additions, user_content)
```

#### 2.3 Conflict Markers for Manual Review

When content seems complex (multiple headers, code blocks), add markers:

```markdown
<!--invar:user-->
<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init -->
<!-- Merge date: 2025-12-27 -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

[original content...]

<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->
<!--/invar:user-->
```

### Phase 3: Pre-commit Protection (Optional)

#### 3.1 Hook Definition

```yaml
# .pre-commit-config.yaml
- id: invar-claude-md-regions
  name: CLAUDE.md Region Protection
  entry: bash -c 'if [ -f CLAUDE.md ] && ! grep -q "<!--invar:managed-->" CLAUDE.md; then echo "Warning: CLAUDE.md missing Invar regions. Run: invar update"; exit 1; fi'
  language: system
  files: ^CLAUDE\.md$
  pass_filenames: false
```

#### 3.2 Warning Message

```
CLAUDE.md Region Protection.............................................Failed
- hook id: invar-claude-md-regions
- exit code: 1

Warning: CLAUDE.md missing Invar regions.

This usually happens after running 'claude /init'.
Run 'invar update' to restore Invar configuration.

Your content will be preserved in the <!--invar:user--> section.
```

### Phase 4: Skills Directory Handling

#### 4.1 Detection

```python
def detect_skill_conflicts(skills_dir: Path) -> list[SkillConflict]:
    """
    Detect conflicts in .claude/skills/ directory.

    Conflicts occur when:
    - Invar skill file exists without <!--invar:skill--> marker
    - File modification time suggests external modification
    """
    conflicts = []
    for skill_name in ["develop", "review", "investigate", "propose"]:
        skill_file = skills_dir / skill_name / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text()
            if "<!--invar:skill-->" not in content:
                conflicts.append(SkillConflict(
                    skill=skill_name,
                    reason="missing_marker",
                    file=skill_file
                ))
    return conflicts
```

#### 4.2 Resolution

Skills are simpler than CLAUDE.md - they can be regenerated:

```
⚠ Skill files missing Invar markers:
  - .claude/skills/develop/SKILL.md
  - .claude/skills/review/SKILL.md

  Options:
  A: Regenerate from template (recommended)
  B: Skip - Keep current files

  Choice? [A/B]
```

## Implementation Plan

| Phase | Scope | Effort | Priority |
|-------|-------|--------|----------|
| 1.1 | Detection logic in `invar update` | Low | High |
| 1.2 | Warning output and prompts | Low | High |
| 1.3 | Init-time warning | Low | High |
| 2.1-2.3 | Smart merge implementation | Medium | High |
| 3.1-3.2 | Pre-commit hook | Low | Medium |
| 4.1-4.2 | Skills handling | Low | Medium |

**Recommended order:** 1.1 → 1.2 → 2.1 → 1.3 → 2.2 → 2.3 → 3.1 → 4.1

## Success Criteria

1. **Detection**: `invar update` correctly identifies overwritten CLAUDE.md
2. **Recovery**: User can restore Invar regions with one command
3. **Preservation**: Claude-generated content is not lost
4. **Prevention**: Users are warned before/after potential conflicts
5. **Transparency**: Merge process is visible and reviewable

## Alternative Approaches Considered

### A: Separate Files

Use `INVAR-CLAUDE.md` instead of modifying `CLAUDE.md`.

**Pros:** No conflict possible
**Cons:** Fragmented configuration, two files to maintain

**Decision:** Rejected - fragmentation is worse than occasional merge

### B: Claude /init Integration

Modify Claude Code to recognize Invar regions.

**Pros:** Perfect integration
**Cons:** Requires Claude Code changes, out of our control

**Decision:** Not feasible - we can't modify Claude Code

### C: File Lock

Prevent any modification to CLAUDE.md except through Invar.

**Pros:** Absolute protection
**Cons:** Too restrictive, blocks legitimate edits

**Decision:** Rejected - users need to edit CLAUDE.md

## Open Questions

1. Should merge be automatic or always prompt?
2. How to handle `.mcp.json` conflicts?
3. Should we backup CLAUDE.md before merge?

## References

- DX-49: Protocol distribution unification (region architecture)
- DX-54: Agent native context management (CLAUDE.md structure)
- Lesson #19: Enforcement timing matters (pre-commit vs runtime)
