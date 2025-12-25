# DX-41: Automatic Review Orchestration

> **"Agent-Native review: triggered by condition, not by command."**

**Status:** Draft
**Created:** 2025-12-25
**Origin:** Merged from DX-31 Phase 2 + DX-35 Phase 3
**Effort:** Medium
**Risk:** Medium

## Problem Statement

Current state:
- DX-31 implemented isolated adversarial review via `/review` skill
- DX-35 implemented workflow skills with manual transitions
- Guard outputs `review_suggested` when conditions are met

**Gap:** User must manually invoke `/review` after seeing `review_suggested`.

**Desired:** Review automatically triggers when conditions are met.

## Current Flow (Manual)

```
Agent: ✓ Final: guard PASS | 0 errors, 2 warnings
       ℹ review_suggested: New Core file with 5 public functions

User: /review  ← Extra step required

Agent: [Spawns review sub-agent...]
```

## Proposed Flow (Automatic)

```
Agent: ✓ Final: guard PASS | 0 errors, 2 warnings
       ℹ review_suggested: New Core file with 5 public functions

       Auto-initiating review... (type 'skip' to bypass)

       [Spawns review sub-agent in background]

Agent: Review complete. 2 MAJOR issues found:
       1. [file:line] Contract doesn't capture error case
       2. [file:line] Missing boundary condition doctest

       Fixing MAJOR issues...
```

## Design

### Trigger Conditions

Guard outputs `review_suggested` when:

```python
def should_suggest_review(file_info: FileInfo, violations: list[Violation]) -> bool:
    """DX-31 trigger conditions."""
    return (
        file_info.escape_hatch_count >= 3 or
        file_info.contract_ratio < 0.7 or
        file_info.is_new_core_file or
        any(v.severity == Severity.WARNING and "security" in v.rule for v in violations)
    )
```

### Auto-Trigger Logic

```python
# In /develop skill's Final stage
async def handle_final(guard_result: GuardReport):
    if guard_result.review_suggested:
        # Check if user wants to skip
        if not await user_confirms_skip(timeout=5):
            # Spawn isolated review
            review_result = await Task(
                prompt=REVIEW_PROMPT,
                subagent_type="general-purpose",
            )

            # Process findings
            if review_result.has_critical_or_major:
                # Enter fix cycle
                await fix_review_issues(review_result.issues)
            else:
                # Report minor issues for backlog
                report_minor_issues(review_result.issues)
```

### Review-Fix Loop

From DX-34 convergence criteria:

```
Auto-Review Triggered
    │
    ├── Round 1: Isolated Review
    │   └── Find issues, categorize by severity
    │
    ├── CRITICAL/MAJOR? ──No──→ Done (report MINOR for backlog)
    │       │
    │      Yes
    │       ↓
    ├── Fix Issues (auto)
    │
    ├── Round 2: Re-review
    │   └── Check fixes, find new issues
    │
    ├── Convergence check:
    │   ├── No CRITICAL/MAJOR → Exit
    │   ├── Round >= 3 → Exit
    │   └── No improvement → Exit
    │
    └── Report: remaining MINOR issues for backlog
```

### Convergence Criteria

```python
def should_exit_review_cycle(
    round: int,
    current: ReviewResult,
    previous: ReviewResult | None
) -> bool:
    if round >= 3:
        return True  # Hard limit
    if current.critical == 0 and current.major == 0:
        return True  # Quality target met
    if previous and current.total >= previous.total:
        return True  # No improvement
    return False
```

## User Control

| Control | Mechanism |
|---------|-----------|
| Skip this review | Type "skip" within 5s timeout |
| Disable auto-review | `auto_review = false` in config |
| Force review | `/review` skill (manual) |

## Configuration

```toml
[tool.invar.workflow]
auto_review = true          # Enable automatic review
review_timeout = 5          # Seconds to wait before auto-trigger
max_review_rounds = 3       # Maximum fix-review cycles
```

## Implementation Plan

1. **Update /develop skill** — Add auto-review trigger in Final stage
2. **Create review orchestrator** — Handle multi-round cycle
3. **Add skip mechanism** — Allow user to bypass
4. **Integrate with Guard** — Use `review_suggested` output

## Platform Support

| Platform | Auto-Review | Manual Review |
|----------|-------------|---------------|
| Claude Code | ✅ Full support | ✅ /review skill |
| Cursor/Windsurf | ❌ Not supported | ⚠️ Manual only |
| Others | ❌ Not supported | ❌ Not available |

## Success Criteria

- [ ] Review triggers automatically when `review_suggested`
- [ ] User can skip within timeout
- [ ] Multi-round cycle converges correctly
- [ ] MAJOR issues fixed before completion
- [ ] MINOR issues reported for backlog

## Related

- DX-31: Independent Adversarial Reviewer (review design, Phase 2 origin)
- DX-35: Workflow-based Phase Separation (Phase 3 origin)
- `/review` skill: `.claude/skills/review/SKILL.md`
