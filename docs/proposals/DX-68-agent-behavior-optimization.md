# DX-68: Agent Behavior Optimization

**Status:** Draft
**Priority:** Low (P3-P5)
**Category:** Developer Experience
**Created:** 2025-12-30
**Based on:** LX-04 Phase 1.5 analysis, Agent Information Hierarchy design
**Reference:** [docs/reference/agent-information-hierarchy.md](../reference/agent-information-hierarchy.md)

---

## Summary

Optimize agent reading behavior to improve reliability of information consumption across the 6-layer hierarchy.

---

## Problem Statement

Current agent reading reliability:

| Layer | Target | Current | Gap |
|-------|--------|---------|-----|
| L0/L1 (CLAUDE.md) | 100% | 100% | — |
| L2 (context.md) | 100% | 80% | 20% |
| L3 (SKILL.md) | 100% | 95% | 5% |
| L4 (INVAR.md) | 80% | 40% | 40% |
| L5 (examples/) | 80% | 60% | 20% |

**Key gaps:**
- 20% of agents skip context.md at Check-In
- 40% of agents don't follow INVAR.md links
- 40% of agents don't check Task Router before coding

---

## Proposed Optimizations

### Phase A: Context Enforcement (P3)

**Goal:** Increase L2 read reliability from 80% to 95%

#### A.1: Hook-based Context Verification

Add verification hook that checks if context.md was read before Skill execution.

**Implementation:**

```bash
# .claude/hooks/pre-skill.sh
# Triggered before any Skill tool call

if [ ! -f ".invar/.context-read-marker" ]; then
    echo "⚠️ context.md not read. Run Check-In first."
    exit 1
fi
```

**Mechanism:**
1. Check-In creates marker file `.invar/.context-read-marker`
2. Pre-Skill hook verifies marker exists
3. Marker cleared at session end

**Risk:** Medium - hook mechanism may not be reliable for all agents
**Effort:** 0.5 days

#### A.2: Skill Entry Action Enforcement

Modify SKILL.md to make context.md reading mandatory with explicit confirmation.

**Before:**
```markdown
## Entry Actions (REQUIRED)
1. Read `.invar/context.md`
2. Check Task Router
3. Display routing announcement
```

**After:**
```markdown
## Entry Actions (REQUIRED)

### Step 1: Context Verification
Read `.invar/context.md` and confirm:
- [ ] Read Key Rules section
- [ ] Checked Task Router
- [ ] Noted any Lessons Learned

If unable to read, STOP and inform user.

### Step 2: Routing Announcement
...
```

**Risk:** Low
**Effort:** 0.5 days

---

### Phase B: Example Inlining (P4)

**Goal:** Increase L5 read reliability from 60% to 90%

#### B.1: Critical Examples in SKILL.md

Inline the most common example patterns directly in SKILL.md develop.

**Current:** Reference to examples/
```markdown
See `.invar/examples/contracts.py` for patterns.
```

**Proposed:** Inline critical pattern
```markdown
### Core Function Template

```python
from deal import pre, post

@pre(lambda x, y=0: x > 0)  # ALL params, even defaults
@post(lambda result: result >= 0)  # Only 'result' available
def calculate(x: int, y: int = 0) -> int:
    """
    >>> calculate(10, 2)
    8
    """
    return x - y
```

For more patterns, see `.invar/examples/contracts.py`.
```

**Trade-off:**
- Pro: 90% reliability (no file reading needed)
- Con: +15 lines in SKILL.md, potential drift from examples/

**Risk:** Low
**Effort:** 1 day

#### B.2: Task Router with Inline Snippets

Modify Task Router to include mini-examples.

**Current:**
```markdown
| Write code in `core/` | `.invar/examples/contracts.py` |
```

**Proposed:**
```markdown
| Write code in `core/` | `.invar/examples/contracts.py` |
|                        | Pattern: `@pre(lambda ALL_PARAMS: ...)` |
```

**Risk:** Low
**Effort:** 0.5 days

---

### Phase C: Agent Behavior Monitoring (P5)

**Goal:** Collect data on actual agent reading patterns

#### C.1: Reading Telemetry

Add optional telemetry to track which files agents read.

**Implementation:**

```python
# In guard command or MCP server
def log_agent_file_access(file_path: str, session_id: str):
    """Log file access for analysis."""
    with open(".invar/.telemetry.jsonl", "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "session": session_id,
            "file": file_path,
        }) + "\n")
```

**Analysis:**
```bash
# Analyze reading patterns
invar analyze-behavior --session-log .invar/.telemetry.jsonl
```

**Output:**
```
Session Analysis:
- context.md read: 85% of sessions
- Task Router checked: 62% of sessions
- examples/ accessed: 58% of sessions
- INVAR.md accessed: 35% of sessions
```

**Risk:** Medium - privacy concerns, opt-in only
**Effort:** 2 days

#### C.2: Compliance Scoring

Add compliance score to Final output.

**Current:**
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

**Proposed:**
```
✓ Final: guard PASS | 0 errors, 2 warnings | Protocol: 85%
```

**Protocol score based on:**
- Check-In displayed (+25%)
- context.md read (+25%)
- Task Router checked (+25%)
- Final with guard (+25%)

**Risk:** Low
**Effort:** 1 day

---

## Implementation Priority

| Phase | Priority | Effort | Impact | Recommendation |
|-------|----------|--------|--------|----------------|
| A.1 Hook Verification | P3 | 0.5d | Medium | Implement if context gaps persist |
| A.2 Entry Action Enforcement | P3 | 0.5d | Medium | Low risk, implement |
| B.1 Example Inlining | P4 | 1d | High | Consider if Task Router insufficient |
| B.2 Task Router Snippets | P4 | 0.5d | Medium | Low risk, implement |
| C.1 Reading Telemetry | P5 | 2d | Low | Only if data needed for decisions |
| C.2 Compliance Scoring | P5 | 1d | Low | Nice-to-have, not critical |

**Total estimated effort:** 5.5 days

---

## Decision Criteria

### When to implement Phase A (Context Enforcement)?

Implement if:
- Observed agent failures due to missing context.md reading > 10%
- Users report agents not following Check-In protocol

### When to implement Phase B (Example Inlining)?

Implement if:
- Contract Rules errors persist despite L1 inclusion
- Task Router triggers but agents still make Core/Shell mistakes

### When to implement Phase C (Monitoring)?

Implement if:
- Need data to justify further optimization investment
- Planning to publish agent behavior research

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| L2 read reliability | 80% | 95% | Telemetry or user reports |
| L5 read reliability | 60% | 90% | Telemetry or user reports |
| Contract Rules errors | Unknown | -50% | Guard output analysis |
| Core/Shell errors | Unknown | -50% | Guard output analysis |

---

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Hook mechanism unreliable | Medium | Low | Use soft warnings, not hard blocks |
| Example inlining causes drift | Low | Medium | Sync check in dev sync command |
| Telemetry privacy concerns | Medium | Low | Opt-in only, local storage |
| Over-optimization diminishing returns | Medium | Low | Measure before implementing |

---

## Related Work

- **LX-04:** Phase 1 + 1.5 established current information hierarchy
- **DX-54:** Context management baseline
- **DX-62:** Task Router implementation
- **DX-57:** Hook system foundation

---

## Appendix: Current Information Hierarchy

See [docs/reference/agent-information-hierarchy.md](../reference/agent-information-hierarchy.md) for complete design documentation.

---

*Proposal created as outcome of LX-04 Phase 1.5 analysis.*
