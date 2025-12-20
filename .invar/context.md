# Invar Project Context

*Last updated: 2025-12-20*

## Current State

- **PyPI:** `python-invar` v0.1.0
- **Protocol:** v3.17
- **Phase 1-11:** Complete
- **Blockers:** None

## Core Principle

> **"Agent-Native Execution, Human-Directed Purpose"**

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

- Protocol and Tools are Agent-Native (Agent is primary user)
- Ultimate goal is Human success through Agent effectiveness
- See `docs/VISION.md` for full philosophy

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1-8 | Complete | Core Guard, Perception, Agent-Native features |
| 9 | Complete | PyPI release, CI/CD, documentation |
| 10 | Complete | P7 (tautology detection), P17, P18, P19 |
| 11 | Complete | P24, P25, P27, P28 (Agent decision support) |

## Phase 11 Complete

Implemented P24, P25, P27, P28 - Agent decision support features.

### Implemented

**P24: Contract Coverage Statistics** (Priority: Low)
```
Design: Simplified from "strength scoring" to pure statistics
Original idea: Score contracts as STRONG/MODERATE/WEAK
Problem: "Strength" requires semantic understanding (Guard can't do)
Simplified: Just report distribution, no judgment

Output in Guard summary:
  Contract coverage: 90% (45/50 functions)
  Issues: 3 tautology, 5 type-check only

Principle: Facts only, no subjective "strength" rating
```

**P25: Automatic Extraction Analysis** (Priority: High)
```
Design: Guard enhancement, NOT a separate command
Trigger: file_size >= warning_threshold
Output: Structured list of extractable groups with dependencies
  [A] pattern_matching (88L): _match_pattern, get_excluded_rules
      Deps: fnmatch, RuleConfig
Principle: Automatic > Opt-in, Sufficient Context for Decision
```

**P27: Enhanced Context for Agent Decision** (Priority: Medium)
```
Design: Improve suggestion quality, NOT auto-fix
Changes:
  1. Suggestion wording: "Add X" → "Patterns: X | Y | Z"
  2. Include docstring/param info in --agent output
  3. Mark confidence level (HIGH/MEDIUM/LOW)
Principle: Guard provides options, Agent decides
```

**P28: Partial Contract Detection** (Priority: Medium)
```
Design: Guard rule, NOT a command (replaces P26)
Severity: WARN (not INFO) - Force Agent to think about boundaries
Detects: @pre lambda has all params but doesn't use all

Example:
  @pre(lambda x, y: x > 0)  # y is not checked
  def f(x: int, y: int): ...
  → WARN: @pre checks 'x' but not 'y'
    Signature: (x: int, y: int) -> int
    → Add constraint for 'y' or verify it needs none

Rationale for WARN:
  - Prevents hidden formal compliance (checking only 1 param to "have a contract")
  - Consistent with P7 (empty_contract is also WARN)
  - WARN allows pass, Agent can decide "this is intentional"

Note: Different from param_mismatch (P8.3):
  - P8.3: lambda param count != function param count (ERROR)
  - P28: lambda has all params but doesn't USE all (WARN)

Principle: Automatic detection, Sufficient Context for Decision
```

### Rejected

- **P26:** `invar check-contract <file>:<line>` - Rejected
  - Reason: Violates "Automatic > Opt-in"
  - Agent can read code and reason about contracts
  - Mechanical analysis covered by P7/P27/P28

### Key Design Decisions (Phase 11)

1. **Guard vs Agent boundary**: Guard does mechanical analysis, Agent does semantic reasoning
2. **No auto-fix**: Guard doesn't know correct answers, only patterns
3. **Automatic embedding**: New info appears in existing output, not new commands
4. **Sufficient Context for Decision**: Output should include enough info for Agent to act directly
   - Don't optimize for "concise" (human habit)
   - Include: signature, relevant context, action options
   - Avoid: redundant info, info Agent already knows
5. **WARN for formal compliance risks**: P28 uses WARN to force Agent to think about boundaries

### Implementation Order

```
P28 → P25 → P27 → P24
 │      │      │      │
 │      │      │      └─ Statistics (depends on rules)
 │      │      └─ Suggestion format (affects all)
 │      └─ Extraction analysis (independent)
 └─ New rule (independent, P27 will update its suggestion)
```

See `.invar/proposals/` for historical details.

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol (90 lines) |
| docs/INVAR-GUIDE.md | Why & How (130 lines) |
| docs/VISION.md | Design philosophy |
| CLAUDE.md | Development guide |

## Archived Documents

Historical documents moved to `docs/archive/`:
- INVAR-DETAILED-v3.16.md (superseded by compressed protocol + Guard hints)
- VISION-ORIGINAL.md (pre-revision)
- PHASE3_REVIEW.md
- FIRST_PRINCIPLES_REVIEW.md
- PROTOCOL_EVOLUTION.md
- decisions-2024.md

## Lessons Learned (Key Insights)

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Documentation ≠ Behavior** - Only automatic mechanisms change behavior
4. **Don't Force, Show** - Auto-embed info in output agents will see
5. **Formal compliance ≠ verification** - `@pre(lambda: True)` is worthless
6. **Mechanical vs Reasoning** - Tool time for mechanics, Agent time for reasoning
7. **Protocol compression** - Info in commands/hints doesn't need to be in protocol
8. **Meta-detection works** - P7 caught tautologies in its own implementation
9. **Guard provides options, not answers** - Guard can't understand business semantics
10. **New commands = cognitive load** - Enhance existing commands instead
11. **Sufficient Context > Concise** - Agent needs info to decide, not minimal output
12. **Hidden formal compliance** - `@pre(lambda x,y: x>0)` looks valid but ignores y

Full list in `.invar/proposals/AGENT-IMPROVEMENTS.md` Discussion Log.

---

*Update this file when: completing phases, making design decisions, discovering pitfalls.*
