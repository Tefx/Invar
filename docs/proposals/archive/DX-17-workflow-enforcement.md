# DX-17: Workflow Enforcement

**Status:** Phase 1 Complete → Evolved to Check-In format
**Priority:** High
**Created:** 2025-12-22
**Updated:** 2025-12-24
**Source:** Real-world feedback from invar-python-test-1 project

> **Note:** "Session Start" has evolved into "Check-In" — a single-line sign-in format:
> `✓ Check-In: guard PASS | top: entry1, entry2`
> See INVAR.md for current specification.

## Problem

Even with INVAR.md and CLAUDE.md, agents skip the workflow:

| Expected | Actual | Gap |
|----------|--------|-----|
| Read .invar/examples/ | Skipped | 100% miss |
| Read .invar/context.md | Skipped | 100% miss |
| Run invar guard --changed | Skipped | 100% miss |
| Run invar map --top 10 | Skipped | 100% miss |
| Explicit Intent declaration | Implicit | Hidden |
| Contract BEFORE code | Simultaneous | Order violation |
| Final invar guard | Skipped | No verification |

**Root Causes:**

| RC | Description | Current Solution |
|----|-------------|------------------|
| RC-1 | CLAUDE.md read as "reference" not "command" | None |
| RC-2 | `□` checkboxes feel optional | None |
| RC-3 | Workflow not part of "task complete" definition | None |
| RC-4 | No technical enforcement | DX-16 (tools only) |

## Relationship to DX-16

| Aspect | DX-16 | DX-17 |
|--------|-------|-------|
| Problem | Agent uses wrong tools | Agent skips workflow |
| Solution | Provide correct tools (MCP) | Force workflow execution |
| Layer | Technical (MCP server) | Cognitive + Structural + Technical |
| Status | Phase 1 Complete | Proposed |

**Complementary:** DX-16 ensures correct tools when used. DX-17 ensures they ARE used.

## Solution: 4-Layer Defense

```
┌─────────────────────────────────────────────────────────────────┐
│                        4-Layer Defense                          │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Cognitive (CLAUDE.md language)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ⛔ Mandatory signals + Consequence statements            │   │
│  │ "Must execute" / "Skip = Fail" / "Not optional"          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 2: Structural (Task completion definition)               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Done = Session Start ✓ + ICIDIV ✓ + invar guard ✓       │   │
│  │ Workflow is part of success criteria, not optional       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 3: Verification (Checkable entry point)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ First message MUST contain invar guard output            │   │
│  │ Agent and user can immediately verify compliance         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  Layer 4: Technical (Hook safety net)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ pre-tool-call hook detects Write/Edit                    │   │
│  │ No invar record → Warning (not blocking)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation

### Phase 1: Template Updates (Zero Cost)

Update `src/invar/templates/CLAUDE.md.template`:

**Before:**
```markdown
## Session Start

□ Read INVAR.md (protocol - 90 lines)
□ Read .invar/examples/ (Core/Shell patterns, contracts)
...
```

**After:**
```markdown
## Session Start — MANDATORY

⛔ **Complete these steps BEFORE writing any code. Skipping = Task Failure.**

### Entry Verification

Your **first message** for any implementation task MUST include:

```bash
$ invar guard --changed
[actual output here]
$ invar map --top 10
[actual output here]
```

No output = Session not started correctly. Stop, run commands, restart.

### Context Loading

1. Read INVAR.md (protocol definition)
2. Read .invar/examples/ (Core/Shell patterns)
3. Read .invar/context.md (project state, lessons)

---

## Task Completion Definition

A task is complete ONLY when ALL conditions are met:

| Condition | Verification |
|-----------|--------------|
| Session Start executed | First message has invar output |
| Intent explicitly stated | Message contains Intent declaration |
| Contract before code | @pre/@post appears before implementation |
| Final invar guard passed | Last message shows success |
| User requirement met | Feature works as requested |

**Missing any = Task incomplete.**
```

### Phase 2: Workflow Hook (Optional)

Add pre-tool-call hook to detect Write/Edit without prior invar guard:

```python
# .claude/hooks/workflow_check.py
def check_workflow(tool_name: str, context: dict) -> dict:
    if tool_name not in ("Write", "Edit"):
        return {"continue": True}

    if not context.get("invar_guard_executed"):
        return {
            "continue": True,  # Warn, don't block
            "message": """
⚠️ Workflow Warning: Writing code without running invar guard first.

Please execute:
1. invar guard --changed
2. invar map --top 10

Then continue with your implementation.
"""
        }
    return {"continue": True}
```

## Expected Effect

| Layer | Mechanism | Effect |
|-------|-----------|--------|
| L1 Cognitive | ⛔ signals, consequences | Agent takes seriously |
| L2 Structural | Completion definition | Workflow = part of done |
| L3 Verification | First message check | Human can verify |
| L4 Technical | Hook warning | Last-resort catch |

**Combined effect:** ~90% workflow compliance (vs ~20% current)

## Metrics

| Metric | Current (Est.) | Target |
|--------|----------------|--------|
| Session Start completion | ~20% | >90% |
| ICIDIV compliance | ~30% | >85% |
| First commit passes guard | ~40% | >80% |

## Timeline

- [x] Phase 1a: Update CLAUDE.md.template
- [x] Phase 1b: Update INVAR.md template (universal Session Start, Task Completion)
- [x] Phase 1c: Agent-agnostic templates (.cursorrules, .aider.conf.yml)
- [ ] Phase 1d: Test with real project
- [ ] Phase 2: Workflow hook (if Phase 1 insufficient)

## Commits

- `52266ac` - feat(DX-17): Workflow enforcement via stronger templates
- (pending) - feat(DX-17): Agent-agnostic workflow enforcement

## References

- Source feedback: `docs/feedback/INVAR-COMPLIANCE-ANALYSIS.md`
- Related: DX-16 (Agent Tool Enforcement)
- Claude Code hooks: https://docs.anthropic.com/claude-code/hooks
