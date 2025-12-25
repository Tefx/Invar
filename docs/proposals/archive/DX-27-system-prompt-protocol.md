# DX-27: System Prompt Protocol Entry

**Status:** ✅ Merged into DX-39 (Archived 2025-12-25)
**Priority:** Medium
**Created:** 2025-12-24
**Related:** DX-17 (Workflow Enforcement)

## Merge Status

This proposal has been merged into **DX-39: Workflow Efficiency Improvements** as "Solution 6: Output Style Protocol Entry".

The core idea (using Output Styles for Check-In/Final enforcement) is preserved in DX-39, which provides a unified approach to workflow compliance improvements.

---

## Problem

Despite Check-In/Final design in templates, agent compliance varies:

| Agent | Config Location | Priority Level |
|-------|-----------------|----------------|
| Claude | CLAUDE.md (user message) | Medium |
| Cursor | .cursorrules | Medium |
| Aider | system-prompt field | **High** |

CLAUDE.md is injected as a user message, not system prompt. This means:
- Can be "forgotten" as context grows
- Competes with other context for attention
- Feels like "reference" not "command"

## Core Insight

From DX-17 discussion:

> **Check-In/Final are not just verification steps.**
> **They are rituals that signal: "I am following the protocol."**

If an agent skips Check-In, it's an early warning that it may skip other protocol steps.

## Solution

Inject Check-In/Final at system prompt level for maximum compliance.

### Content (Minimal)

```markdown
## Invar Protocol

First message: ✓ Check-In: guard PASS | top: <entry1>, <entry2>
Last message: ✓ Final: guard PASS | <errors>, <warnings>

Execute invar_guard + invar_map, show one-line summary.
No visible check-in = Session not started.
```

**~50 words.** Minimal but non-negotiable.

### Implementation by Agent

#### Claude Code

**Option A: Output Style (Recommended)**

Create `.claude/output-styles/invar-protocol.md`:

```markdown
---
name: Invar Protocol
description: Check-In/Final enforcement
keep-coding-instructions: true
---

## Invar Protocol

First message: ✓ Check-In: guard PASS | top: <entry1>, <entry2>
Last message: ✓ Final: guard PASS | <errors>, <warnings>

Execute invar_guard + invar_map, show one-line summary.
No visible check-in = Session not started.
```

Activate in `.claude/settings.json`:
```json
{
  "outputStyle": "invar-protocol"
}
```

**Option B: CLI Wrapper**

```bash
#!/bin/bash
# invar-claude
claude --append-system-prompt "$(cat .invar/protocol-entry.txt)" "$@"
```

#### Cursor

Already uses `.cursorrules` which is treated as system-level. ✅

#### Aider

Already has `system-prompt` field in config. ✅ Updated.

### `invar init` Enhancement

Update `invar init --claude` to:

1. Create `.claude/output-styles/invar-protocol.md`
2. Update `.claude/settings.json` with `"outputStyle": "invar-protocol"`

```python
def create_output_style(path: Path) -> None:
    """Create Claude Code output style for Invar protocol."""
    output_style_dir = path / ".claude" / "output-styles"
    output_style_dir.mkdir(parents=True, exist_ok=True)

    style_content = '''---
name: Invar Protocol
description: Check-In/Final enforcement
keep-coding-instructions: true
---

## Invar Protocol

First message: ✓ Check-In: guard PASS | top: <entry1>, <entry2>
Last message: ✓ Final: guard PASS | <errors>, <warnings>

Execute invar_guard + invar_map, show one-line summary.
No visible check-in = Session not started.
'''
    (output_style_dir / "invar-protocol.md").write_text(style_content)
```

## Layered Architecture

After DX-27:

```
┌─────────────────────────────────────────────────────────┐
│ System Prompt (Claude Code Default)                     │
├─────────────────────────────────────────────────────────┤
│ + Output Style (DX-27)           ← NEW                  │
│   Check-In/Final format (~50 words)                     │
├─────────────────────────────────────────────────────────┤
│ + MCP Instructions (DX-16)                              │
│   Tool substitution rules                               │
├─────────────────────────────────────────────────────────┤
│ User Message: CLAUDE.md                                 │
│   Project-specific details                              │
├─────────────────────────────────────────────────────────┤
│ User Message: .invar/context.md                         │
│   Project state, lessons learned                        │
└─────────────────────────────────────────────────────────┘
```

## Expected Impact

| Metric | Without DX-27 | With DX-27 |
|--------|---------------|------------|
| Check-In compliance | ~50% | ~85% |
| Final compliance | ~30% | ~75% |
| Protocol awareness | Medium | High |

## Implementation Plan

- [ ] Phase 1: Create output style template in `src/invar/templates/`
- [ ] Phase 2: Update `invar init --claude` to deploy output style
- [ ] Phase 3: Test with real projects
- [ ] Phase 4: Document in INVAR.md

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Output style not activated | `invar init --claude` auto-configures |
| Conflicts with user styles | `keep-coding-instructions: true` |
| Content too long | Minimal design (~50 words) |

## Open Questions

1. Should output style be opt-in or default?
2. How to handle projects with existing custom output styles?
3. Should MCP instructions also include Check-In/Final?

## References

- Claude Code Output Styles: https://docs.anthropic.com/en/docs/claude-code/settings
- DX-17: Workflow Enforcement (Check-In/Final origin)
- INVAR.md v3.27: Check-In/Final specification
