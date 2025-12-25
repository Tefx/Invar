# DX-32: USBV Workflow (ICIDIV Iteration)

> **"Process should match cognition, not fight it."**

**Status:** ✅ Implemented (Archived 2025-12-25)
**Created:** 2024-12-25
**Updated:** 2024-12-25
**Relates to:** DX-30 (Visible Workflow), DX-31 (Adversarial Reviewer)

## Completion Status

USBV workflow is now the standard, replacing ICIDIV:

| Feature | Status |
|---------|--------|
| USBV phases (Understand → Specify → Build → Validate) | ✅ Implemented |
| Workflow skills integration | ✅ /develop uses USBV |
| Variable depth based on task | ✅ Skill descriptions reflect this |
| Explicit iteration paths | ✅ VALIDATE → back to appropriate phase |

**Implementation locations:**
- `.claude/skills/develop/SKILL.md` — USBV workflow
- `INVAR.md` — Protocol v5.0 with workflow sections
- `sections/develop.md` — Detailed USBV reference

## Problem

### Current ICIDIV Order

```
I(ntent) → C(ontract) → I(nspect) → D(esign) → I(mplement) → V(erify)
```

### Core Issue: Contract Before Inspect

The current workflow places Contract **before** Inspect:

```
Intent → Contract → Inspect → ...
             ↑
    How can you write a good contract
    without understanding existing code?
```

**Evidence from DX-31 implementation:** The developer naturally inspected existing code before writing contracts. This suggests **Inspect-before-Contract is cognitively natural**.

### What We Learned

1. **Contract-before-Inspect is unnatural** for brownfield development
2. **Different tasks need different depths**, not different workflows
3. **Explicit task classification adds friction** without clear benefit
4. **Iteration should be explicit**, not hidden

## Solution: USBV Unified Framework

### The Four Phases

```
UNDERSTAND → SPECIFY → BUILD → VALIDATE
     │           │        │        │
  [depth]    [depth]  [depth]  [depth]
     │           │        │        │
     └───────────┴────────┴────────┘
              Depth varies naturally
              based on resistance encountered
```

### Phase Definitions

| Phase | Purpose | Core Activities |
|-------|---------|-----------------|
| **UNDERSTAND** | Know what and why | Intent, Inspect, Constraints |
| **SPECIFY** | Define boundaries | Contract, Design, Test Cases |
| **BUILD** | Write code | Implement leaves, Compose |
| **VALIDATE** | Confirm correctness | Verify, Integrate, Reflect |

### Key Design Decisions

#### 1. Unified Framework, Variable Depth

**Not** different workflows for different tasks. Same 4 phases, but depth adjusts naturally:

| Task Type | U | S | B | V |
|-----------|---|---|---|---|
| Pure algorithm | Shallow | **Deep** | Normal | **Deep** |
| Feature addition | **Deep** | Normal | Normal | Normal |
| Bug fix | **Deep** | Shallow | Shallow | **Deep** |
| Refactoring | Normal | Shallow | **Deep** | Normal |

**No explicit classification needed.** Depth emerges from resistance encountered.

#### 2. Spike as Implicit Activity

Exploration is **not** a formal phase. It happens within UNDERSTAND when needed:

```
UNDERSTAND
├── Intent: What is the task?
├── Inspect: What exists?
│     └── (explore if uncertain) ← Implicit, not listed
└── Constraints: Edge cases, limits?
```

**Trigger:** High uncertainty about approach
**Exit:** Enough clarity to write Contract

#### 3. Core vs Shell: Same Workflow, Different Emphasis

Not different workflows. Different focus within same phases:

| Phase | Core Emphasis | Shell Emphasis |
|-------|---------------|----------------|
| SPECIFY | @pre/@post completeness | Error path coverage |
| SPECIFY | Boundary doctests | Result[T,E] patterns |
| BUILD | Pure function implementation | I/O + error handling |
| VALIDATE | Property testing | Integration testing |

#### 4. Explicit Iteration

When VALIDATE fails, explicit backtracking:

```
VALIDATE failure
    │
    ├── Logic error in code → Return to BUILD
    ├── Missing edge case → Return to SPECIFY (add doctest)
    └── Misunderstood requirement → Return to UNDERSTAND
```

## Detailed Specification

### Phase 1: UNDERSTAND

**Goal:** Sufficient clarity to write contracts.

**Activities:**
1. **Intent** - What is the task? What problem does it solve?
2. **Inspect** - What exists in codebase? Similar code? Patterns?
3. **Constraints** - Edge cases? Performance? Security? Compatibility?

**Exploration (when needed):**
- If multiple approaches possible, briefly evaluate
- If technical feasibility unclear, quick prototype
- Document findings, then proceed

**Exit Criteria:**
- Can articulate what the function should do
- Know where it fits in codebase
- Identified main edge cases

**Depth Signals:**
- Greenfield (new feature): Focus on Intent + Constraints
- Brownfield (modification): Focus on Inspect

### Phase 2: SPECIFY

**Goal:** Complete specification before implementation.

**Activities:**
1. **Contract** - @pre/@post that uniquely determine behavior
2. **Design** - Decomposition into sub-functions (leaves first)
3. **Test Cases** - Doctests covering normal, boundary, error cases

**Core Code:**
```python
@pre(lambda x: x > 0)  # What inputs are valid?
@post(lambda result: result >= 0)  # What outputs are guaranteed?
def calculate(x: int) -> int:
    """
    >>> calculate(1)  # Normal
    1
    >>> calculate(0)  # Boundary (rejected by @pre)
    Traceback...
    """
```

**Shell Code:**
```python
def load_config(path: Path) -> Result[Config, str]:
    """
    Returns:
        Success(config) - Valid config loaded
        Failure("not found") - File doesn't exist
        Failure("parse error: ...") - Invalid format
    """
```

**Exit Criteria:**
- Contract is complete (could someone else implement from it?)
- Sub-function decomposition clear
- Doctests cover key cases

**Depth Signals:**
- Algorithm: Deep (contract IS the solution)
- Integration: Normal (focus on interfaces)
- Bug fix: Shallow (contract usually unchanged)

### Phase 3: BUILD

**Goal:** Code that passes all doctests.

**Activities:**
1. **Implement Leaves** - Smallest units first (no dependencies)
2. **Compose** - Combine into complete feature
3. **Incremental Verify** - Run doctests after each function

**Order:**
```
Leaf functions (no deps) → Helper functions → Main function → Integration
```

**Exit Criteria:**
- All doctests pass
- No obvious code smells
- Follows existing patterns

**Depth Signals:**
- New algorithm: Deep (core logic)
- Glue code: Shallow (mostly wiring)
- Refactoring: Deep (restructuring)

### Phase 4: VALIDATE

**Goal:** Confirm correctness and quality.

**Activities:**
1. **Verify** - `invar guard` (static + doctests + property tests)
2. **Integrate** - Test with rest of system (if applicable)
3. **Reflect** - Design smell check, review suggestion evaluation

**Iteration Triggers:**

| Guard Result | Action |
|--------------|--------|
| Errors | Fix in BUILD, re-validate |
| Warnings in modified files | Fix (you touched it, you own it) |
| `review_suggested` | Consider independent /review |

**Backtracking:**

| Issue Found | Return To |
|-------------|-----------|
| Code bug | BUILD |
| Missing edge case | SPECIFY (add doctest) |
| Contract incomplete | SPECIFY (strengthen @pre/@post) |
| Misunderstood requirement | UNDERSTAND |

**Exit Criteria:**
- Guard passes (0 errors)
- Warnings addressed in touched files
- Integration works (if applicable)

## Depth Adjustment Signals

The framework is self-balancing. These signals indicate where to focus:

| Signal | Meaning | Action |
|--------|---------|--------|
| Contract hard to write | UNDERSTAND incomplete | Go deeper in Inspect |
| Don't know where code goes | UNDERSTAND incomplete | More Inspect |
| Doctests keep failing | SPECIFY incomplete | Refine contract |
| Guard finds contract issues | SPECIFY incomplete | Strengthen @pre/@post |
| Implementation unclear | SPECIFY incomplete | Better decomposition |
| Integration fails | BUILD incomplete | Check interfaces |

**Key Insight:** Don't classify tasks. Notice where resistance is and adjust.

## Comparison: ICIDIV vs USBV

| Aspect | ICIDIV | USBV |
|--------|--------|------|
| Phases | 6 | 4 (with sub-activities) |
| Inspect timing | After Contract | Before Contract (in UNDERSTAND) |
| Task-type handling | Same for all | Same framework, variable depth |
| Iteration | Not explicit | Explicit backtracking paths |
| Spike/Explore | Not addressed | Implicit in UNDERSTAND |
| Core/Shell | Same | Same workflow, different emphasis |

## Visible Workflow Integration (DX-30)

For complex tasks, show phases in TodoList:

```
□ [UNDERSTAND] Task: Add caching to API
  - Intent: Reduce response time for repeated queries
  - Inspect: Found existing cache in utils/cache.py
  - Constraints: Must be thread-safe, max 1GB memory

□ [SPECIFY] Contracts and design
  - cache_get: @pre(key is str), @post(result is T | None)
  - cache_set: @pre(key, value, ttl > 0)
  - Decomposition: get, set, evict, stats

□ [BUILD] Implementation
  - Implement LRU eviction
  - Implement thread-safe access
  - Wire into API layer

□ [VALIDATE] Verification
  - Guard: PASS
  - Integration: API tests pass
```

## Implementation Plan

### Phase 1: Documentation
- [ ] Update INVAR.md workflow section (ICIDIV → USBV)
- [ ] Update CLAUDE.md template
- [ ] Update .invar/context.md with decision

### Phase 2: Examples
- [ ] Add USBV examples to .invar/examples/
- [ ] Show depth variation for different task types

### Phase 3: Tooling (Optional)
- [ ] Guard hint for incomplete UNDERSTAND (can't write contract)
- [ ] Backtracking suggestions in validation output

## Success Criteria

1. Agent naturally follows USBV without fighting it
2. Contracts are informed by codebase context (Inspect before Contract)
3. Depth varies appropriately without explicit classification
4. Iteration is allowed without "breaking protocol"
5. User can track progress via 4-phase structure

## Open Questions (Resolved)

| Original Question | Resolution |
|-------------------|------------|
| Spike as formal phase? | No, implicit in UNDERSTAND |
| How to indicate task type? | Don't. Depth adapts naturally |
| Core/Shell different workflows? | No. Same workflow, different emphasis |
| Iteration vs visible progress? | 4 stable phases, internal iteration allowed |

---

*Proposal refined through discussion on 2024-12-25.*
