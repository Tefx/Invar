# DX-32: ICIDIV Workflow Iteration

> **"Process should match cognition, not fight it."**

**Status:** Proposed
**Created:** 2024-12-25
**Relates to:** DX-30 (Visible Workflow), DX-31 (Adversarial Reviewer)

## Problem

### Current ICIDIV Order

```
I(ntent) → C(ontract) → I(nspect) → D(esign) → I(mplement) → V(erify)
```

### The Core Issue: Contract Before Inspect

The current workflow places Contract **before** Inspect:

```
Intent → Contract → Inspect → ...
             ↑
    How can you write a good contract
    without understanding existing code?
```

**Problems with Contract-before-Inspect:**

| Scenario | Problem |
|----------|---------|
| Adding function | Don't know if similar functionality already exists |
| Modifying function | Don't know existing signature and callers |
| Integration | Don't know existing patterns and conventions |

### Evidence from DX-31 Implementation

During DX-31 implementation, the actual workflow was:

```
Intent → Inspect (invar sig) → [Contract + Implement mixed] → Verify
```

The developer **naturally** inspected existing code before writing contracts. This suggests **Inspect-before-Contract is cognitively natural**.

### Two Conflicting Goals

| Goal | Optimal Order | Reason |
|------|---------------|--------|
| Human Checkpoints | Contract visible early | User can correct direction |
| Code Quality | Inspect before Contract | Contracts must fit context |

Current ICIDIV optimizes for neither clearly.

## Analysis

### Linear vs Iterative

ICIDIV attempts to **linearize an iterative process**:

```
Actual cognitive process (iterative):

     ┌─────────────────────────────────┐
     ↓                                 │
[Rough Contract] → [Implement] → [Test] → [Discover Issue] → [Refine]
                                       │                        │
                                       └────────────────────────┘

Protocol expectation (linear):

Intent → Contract → Inspect → Design → Implement → Verify
```

High-quality code comes from **iteration**, not one-pass correctness.

### Task-Type Variation

Different tasks need different workflows:

| Task Type | Optimal Order | Reason |
|-----------|---------------|--------|
| Pure algorithm | Contract → Design → Implement → Verify | Spec is clear, no integration |
| Feature addition | Inspect → Contract → Design → Implement → Verify | Must understand context first |
| Bug fix | Inspect → Contract → Implement → Verify | Must understand failure first |
| Refactoring | Inspect → Design → Implement → Verify | Contract unchanged |
| Exploratory | Inspect → Prototype → Verify → Contract | Don't know solution yet |

**No single order is optimal for all tasks.**

### Core vs Shell Difference

| Code Type | Priority | Why |
|-----------|----------|-----|
| **Core** | Contract completeness | Pure functions can be fully specified |
| **Shell** | Error handling coverage | I/O is inherently impure, contracts less useful |

**Core optimal:**
```
Intent → Inspect → Contract (complete!) → Design → Implement → Verify
```

**Shell optimal:**
```
Intent → Inspect → Design (error paths!) → Implement → Integration Test → Verify
```

### Missing Phases in ICIDIV

| Missing Phase | Purpose |
|---------------|---------|
| **Spike/Prototype** | Quick validation when uncertain, before committing to design |
| **Integration** | Unit correct ≠ Integration correct |
| **Reflect** | Guard catches errors, doesn't catch design smells |
| **Iteration** | Allow backtracking from Verify to Contract |

## Proposed Solution

### Option A: Reorder ICIDIV

Move Inspect before Contract:

```
Current:  I(ntent) → C(ontract) → I(nspect) → D(esign) → I(mplement) → V(erify)
Proposed: I(ntent) → I(nspect) → C(ontract) → D(esign) → I(mplement) → V(erify)
```

**Mnemonic change:** ICIDIV → IICDIV

### Option B: Merge Intent and Inspect

Combine into single "Understand" phase:

```
U(nderstand) → C(ontract) → D(esign) → I(mplement) → V(erify)
    ↓
 Intent + Inspect + Constraints
```

**Mnemonic:** UCDIV (5 phases instead of 6)

### Option C: Phase-Based with Iteration (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: UNDERSTAND                                             │
│  ├── Intent: What is the task?                                   │
│  ├── Inspect: What exists in codebase?                           │
│  └── Constraints: Edge cases, performance, security?             │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: SPECIFY                                                │
│  ├── Contract: Interface with @pre/@post                         │
│  ├── Design: Decomposition into sub-functions                    │
│  └── Test Cases: Doctests including edge cases                   │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: BUILD                                                  │
│  ├── Implement Leaves: Smallest units first                      │
│  └── Compose: Combine into complete feature                      │
├─────────────────────────────────────────────────────────────────┤
│  Phase 4: VALIDATE                                               │
│  ├── Verify: Run invar guard                                     │
│  ├── Integrate: Test with rest of system                         │
│  └── Reflect: Check for design smells                            │
│         ↓                                                        │
│    If Reflect finds issues → Return to SPECIFY                   │
└─────────────────────────────────────────────────────────────────┘
```

**Mnemonic:** USBV (Understand → Specify → Build → Validate)

**Key improvements:**
1. Inspect merged into Understand (before Contract)
2. Explicit iteration path from Validate back to Specify
3. Reflect phase for design quality review
4. Separate Integration testing

### Option D: Task-Type Dispatch

Different workflows for different task types:

```python
def get_workflow(task_type: TaskType) -> Workflow:
    match task_type:
        case TaskType.ALGORITHM:
            return ["Contract", "Design", "Implement", "Verify"]
        case TaskType.FEATURE:
            return ["Inspect", "Contract", "Design", "Implement", "Verify"]
        case TaskType.BUGFIX:
            return ["Inspect", "Contract", "Implement", "Verify"]
        case TaskType.REFACTOR:
            return ["Inspect", "Design", "Implement", "Verify"]
        case TaskType.EXPLORATORY:
            return ["Inspect", "Spike", "Contract", "Implement", "Verify"]
```

**Intent phase** determines task type, then dispatches to appropriate workflow.

## Visibility vs Quality Trade-off

### The Dual Purpose of Workflow

| Purpose | Optimizes For | Key Requirement |
|---------|---------------|-----------------|
| **Human Oversight** | User can correct direction | Checkpoints visible early |
| **Code Quality** | Correct, maintainable code | Informed by context |

### Proposal: Separate Cognitive Order from Display Order

**Cognitive order** (what agent does):
```
Understand → Specify → Build → Validate
     ↑____________________________|  (iterate)
```

**Display order** (what user sees):
```
[Understand Summary] → User confirms
[Specification] → User reviews ← KEY CHECKPOINT
[Implementation] → User can see
[Validation Results] → User approves
```

The agent may internally iterate, but **displays stable checkpoints** to user.

## Implementation Plan

### Phase 1: Documentation Update
- Update INVAR.md workflow section
- Update CLAUDE.md template
- Add task-type guidance

### Phase 2: Visible Workflow Enhancement
- Modify TodoList conventions for new phases
- Add iteration indicators in output

### Phase 3: Tooling Support (Optional)
- Guard rule to detect workflow violations
- Suggest workflow based on detected task type

## Comparison

| Aspect | Current ICIDIV | Proposed USBV |
|--------|----------------|---------------|
| Phases | 6 | 4 (with sub-phases) |
| Inspect timing | After Contract | Before Contract (in Understand) |
| Iteration | Not explicit | Explicit Validate → Specify loop |
| Task-type variance | None | Acknowledged |
| Core/Shell difference | None | Recommended different emphasis |

## Success Criteria

1. Agent naturally follows workflow without fighting it
2. Contracts are informed by codebase context
3. User has clear checkpoints for oversight
4. Iteration is allowed without "breaking protocol"
5. Different task types can follow appropriate sub-workflows

## Open Questions

1. Should Spike/Prototype be a formal phase or optional sub-phase?
2. How to indicate task type without adding friction?
3. Should Core and Shell have formally different workflows?
4. How to balance iteration allowance with visible progress?

---

*Proposal originated from reflection on DX-31 implementation experience.*
