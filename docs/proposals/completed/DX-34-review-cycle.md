# DX-34: Multi-Round Review Cycle

> ⚠️ **This proposal has been superseded by [DX-35](./DX-35-workflow-phase-separation.md).**
>
> The `/review` workflow in DX-35 implements all concepts from this document:
> - Convergence criteria (max 3 rounds, no CRITICAL/MAJOR, no improvement)
> - Role isolation (isolated sub-agent with fresh context)
> - Review-fix loop (review → fix → re-review)
> - Trigger conditions (Guard's `review_suggested`)
> - Stall detection (Q6 in DX-35)
>
> This document is retained for historical reference and design rationale.

**Status:** Superseded by DX-35
**Created:** 2025-12-25
**Updated:** 2025-12-25
**Related:** DX-31 (Adversarial Reviewer), DX-33 (Verification Blind Spots), **DX-35 (Workflow-based Phase Separation)**

## Problem Statement

Single-round adversarial review has coverage gaps:

| Evidence | Implication |
|----------|-------------|
| Round 1 found 26 issues | Good coverage |
| Round 2 found 24 different issues | Single round incomplete |
| "Limitation" comments became targets | Documentation ≠ Fix |
| Surface fixes expose deeper issues | Problems have layers |

**Core issues:**
1. Single review has blind spots (sampling randomness)
2. "Fix by documentation" gets challenged in next round
3. Surface problems mask deeper logic issues
4. No convergence criteria → could loop forever

## Proposed Solution

### Design Principles

1. **Separation of Concerns**: Development vs Review are distinct phases
2. **Trigger-Based**: Not every change needs multi-round review
3. **Role Isolation**: Separate agents for review vs fix (prevent confirmation bias)
4. **Bounded Iteration**: Clear convergence criteria to prevent infinite loops

### Workflow Integration

```
┌─────────────────────────────────────────────────────────┐
│                 Development Phase                        │
│    USBV → Guard(static) → Tests(functional) → PASS      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                  Guard: review_suggested?
                           │
              ┌────────────┴────────────┐
              │ NO                      │ YES
              ▼                         ▼
           Done                ┌────────────────────┐
                               │   Quality Phase     │
                               │  (separate session) │
                               └────────────────────┘
                                        │
                                        ▼
                               ┌────────────────┐
                               │ Review (isolated)│◄──┐
                               └────────────────┘    │
                                        │            │
                                        ▼            │
                               ┌────────────────┐    │
                               │  Fix issues    │    │
                               └────────────────┘    │
                                        │            │
                                        ▼            │
                                  Converged?         │
                                   (see below)       │
                                        │            │
                              ┌─────────┴─────────┐  │
                              │ YES              │ NO│
                              ▼                   └──┘
                            Done              (max 3 rounds)
```

### Trigger Conditions

Enter Quality Phase when Guard reports `review_suggested`:

| Trigger | Threshold | Rationale |
|---------|-----------|-----------|
| Escape hatches | >= 3 | Many suppressions need validation |
| Contract coverage | < 50% | Low coverage = high risk |
| Security-sensitive | path detected | Security requires scrutiny |
| **New (proposed):** | | |
| Large change | > 500 lines added | More code = more risk |
| Pre-release | version bump | Quality gate before release |

### Convergence Criteria

Exit Quality Phase when ANY condition met:

```python
def should_exit_review_cycle(
    round: int,
    current: ReviewResult,
    previous: ReviewResult | None
) -> tuple[bool, str]:
    """Determine if review cycle should end."""

    # Hard limit: max 3 rounds
    if round >= 3:
        return (True, "max_rounds_reached")

    # Quality target: no blocking issues
    if current.critical == 0 and current.major == 0:
        return (True, "quality_target_met")

    # Diminishing returns: no improvement
    if previous and current.total >= previous.total:
        return (True, "no_improvement")

    # Continue cycling
    return (False, "continue")
```

### Role Separation

| Role | Responsibility | Context |
|------|----------------|---------|
| **Development Agent** | USBV, write code, Guard | Has full dev context |
| **Review Agent** | Find problems, report | Fresh context (isolated) |
| **Fix Agent** | Apply fixes from report | Can be dev agent |

**Key rule:** Review Agent must NOT have development conversation history.

This prevents:
- Confirmation bias ("I wrote it, so it's good")
- Rationalization ("I know why I did this, it's fine")
- Context bleeding ("The user said this was okay")

### Implementation Phases

#### Phase 1: Process Documentation (Current)

Add to CLAUDE.md:

```markdown
### Review Cycle (when review_suggested triggered)

1. Complete development (USBV + Guard PASS)
2. If Guard reports `review_suggested`:
   a. Start new session for isolated review: `/review --isolated`
   b. Fix CRITICAL and MAJOR issues
   c. Run `/review --isolated` again
   d. Exit when: no CRITICAL/MAJOR OR 3 rounds completed
3. Document remaining MINOR issues for backlog
```

#### Phase 2: Tooling Support (Future)

```bash
# Proposed command
invar review-cycle [options]

Options:
  --max-rounds N      Maximum review rounds (default: 3)
  --until LEVEL       Exit when no issues at LEVEL or above
                      (critical, major, minor; default: major)
  --fix-between       Auto-run fix suggestions between rounds
  --report FILE       Output cycle report to file
```

#### Phase 3: Metrics & Learning (Future)

Track across review cycles:
- Issues found per round (expect diminishing)
- Issue categories by round (expect depth increase)
- False positive rate (reviewer finds non-issues)
- Fix quality (issues that recur)

## Trade-offs

### Pros

| Benefit | Impact |
|---------|--------|
| Higher coverage | Multiple passes find different issues |
| Depth progression | Surface → deep issue discovery |
| Role clarity | Separate agents, clear responsibilities |
| Bounded cost | Convergence criteria prevent infinite loops |

### Cons

| Cost | Mitigation |
|------|------------|
| Longer cycle time | Only triggered by review_suggested |
| More tokens/cost | Bounded by max rounds |
| Complexity | Phase 1 is just documentation |
| Agent confusion | Role separation helps |

## Open Questions

1. **Should fixes be atomic or batched?**
   - Atomic: Fix one issue, re-review (slow, thorough)
   - Batched: Fix all issues, re-review (fast, may miss interactions)
   - Proposed: Batched for MINOR, atomic for CRITICAL

2. **What about MINOR issues?**
   - Option A: Must fix all (expensive)
   - Option B: Document for backlog (tech debt)
   - Proposed: Option B, with periodic MINOR cleanup sprints

3. **Cross-session state?**
   - Review Agent is isolated (no dev context)
   - But needs to see previous review results?
   - Proposed: Pass only structured report, not conversation

4. **When to bypass?**
   - Hotfix scenarios?
   - User explicit override?
   - Proposed: `--skip-review-cycle` flag with logged justification

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Issues per round | Decreasing | Round N+1 < Round N |
| Cycle completion | < 3 rounds avg | Mean rounds to converge |
| Recurrence rate | < 10% | Issues that reappear |
| False positive rate | < 20% | Reviewer finds non-issues |

## References

- DX-31: Adversarial Reviewer (defines /review command)
- DX-33: Verification Blind Spots (why automation misses issues)
- [Empirical evidence from this session's two review rounds]

## Appendix: Session Evidence

### Round 1 vs Round 2 Comparison

| Aspect | Round 1 | Round 2 |
|--------|---------|---------|
| Issues found | 26 | 24 |
| CRITICAL | 3 | 5 |
| Focus | Preconditions, dead code | Logic completeness, security |
| Fix style | Many "add documentation" | Challenged documentation fixes |

### Why Different Results?

1. **Code changed**: Round 1 fixes (comments) became Round 2 targets
2. **LLM sampling**: Different exploration paths each run
3. **Problem layers**: Surface fixes exposed deeper issues
4. **No shared context**: Round 2 had no confirmation bias

This empirical evidence supports the multi-round, isolated approach.
