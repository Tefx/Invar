# DX-63: Contracts-First Enforcement

**Status:** ✅ Complete
**Created:** 2024-12-28
**Updated:** 2024-12-29
**Completed:** 2024-12-29
**Category:** Workflow / Agent Behavior
**Related:** DX-51 (Phase Visibility), DX-54 (Context Management), DX-61 (Pattern Guidance)

---

## Executive Summary

Agents consistently bypass the SPECIFY phase by batch-creating file structures and then filling implementations without contracts. Phase-level gates fail because the batch creation happens before any gate can trigger.

**Solution:** Function-level gates + batch creation detection + incremental development enforcement.

---

## Problem Statement

### The Batch Creation Bypass

```
DX-63 original assumption:
  UNDERSTAND → SPECIFY (all contracts) → BUILD (all implementations) → VALIDATE
                    ↑
              Gate here

Actual agent behavior:
  Create 8 file skeletons → Fill implementations one by one → VALIDATE (81 errors)
       ↑
  Gate never triggered - files exist but are empty
```

### Evidence (DX-61 Case Study)

| Metric | Expected | Actual |
|--------|----------|--------|
| Contract coverage at BUILD end | 80%+ | **0%** |
| Files created without contracts | 0 | **8** |
| missing_contract errors | 0 | **81** |
| Guard rework cycles | 1 | **4+** |

### Root Causes

| Cause | Psychology |
|-------|------------|
| **Momentum** | Once coding starts, stopping for contracts feels like interruption |
| **Uncertainty** | "AST is complex, I need to see implementation before writing contracts" |
| **Batch mindset** | "Let me set up the structure first, then add contracts" |
| **Context pressure** | Context filling up → rush to finish → skip contracts |

### Contract Quality Degradation

When contracts are added after implementation:

```python
# After implementation (descriptive - just documents behavior)
@post(lambda result: isinstance(result, list))

# Before implementation (prescriptive - constrains design)
@post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
@post(lambda result: all(0.0 <= s.confidence <= 1.0 for s in result))
```

Contracts-after are documentation. Contracts-before are specification.

---

## Core Principles

```
┌─────────────────────────────────────────────────────────────┐
│  1. Function-Level Gates > Phase-Level Gates                │
│     Each function: SPECIFY → BUILD, not all functions batch │
│                                                             │
│  2. Batch Creation = Red Flag                               │
│     Detect and warn on multi-file creation without contracts│
│                                                             │
│  3. Incremental Development                                 │
│     One file → contracts → implement → verify → next file   │
│                                                             │
│  4. No Placeholder Contracts                                │
│     @post(lambda: True) is trivial and must be rejected     │
│                                                             │
│  5. Contracts Must Constrain                                │
│     Contracts are specification, not documentation          │
└─────────────────────────────────────────────────────────────┘
```

---

## Solution Components

### Component 1: Guard `--contracts-only` Mode

**Command:**

```bash
invar guard --contracts-only [path]
invar guard -c [path]
```

**Checks:**

| Check | Description |
|-------|-------------|
| Coverage | X/Y functions have @pre or @post |
| Trivial | Reject `lambda: True` and similar |
| Batch | Warn on multiple new files with low coverage |

**Output Examples:**

Pass:
```
Contract Coverage Check
========================================
Files: 3 | Functions: 12

Coverage: 12/12 (100%) ✓
Trivial:  0/12 (0%)   ✓
Batch:    No new uncovered files ✓

Ready for BUILD phase.
```

Fail:
```
Contract Coverage Check
========================================
Files: 8 | Functions: 35

Coverage: 5/35 (14%) ✗
Trivial:  2/35 (6%)  ✗

⚠ BATCH WARNING: 6 new files with 0% coverage
  - src/core/patterns/p0_exhaustive.py (0/4)
  - src/core/patterns/p0_validation.py (0/5)
  - src/core/patterns/p0_newtype.py (0/4)
  - src/core/patterns/p0_literal.py (0/3)
  - src/core/patterns/p0_nonempty.py (0/4)
  - src/core/patterns/detector.py (0/6)

✗ Trivial contracts detected:
  - src/core/utils.py:10 helper @post(lambda: True)
  - src/core/utils.py:25 wrapper @pre(lambda x: True)

Recommendation: Add contracts incrementally, one file at a time.

Not ready for BUILD phase.
```

**Trivial Contract Patterns:**

```python
TRIVIAL_PATTERNS = [
    r"lambda\s*:\s*True",           # lambda: True
    r"lambda\s+\w+\s*:\s*True",     # lambda x: True
    r"lambda\s+[\w,\s]+:\s*True",   # lambda x, y: True
    r"lambda\s+\*\w+\s*:\s*True",   # lambda *args: True
    r"lambda\s+result\s*:\s*True",  # lambda result: True (post)
]
```

**Implementation Location:**

```
src/invar/core/coverage.py  # NEW
├── calculate_contract_coverage(path) -> CoverageReport
├── detect_trivial_contracts(path) -> list[TrivialContract]
├── detect_batch_creation(path, git_status) -> BatchWarning | None
└── format_coverage_report(report) -> str

src/invar/shell/commands/guard.py
└── add --contracts-only / -c flag
```

---

### Component 2: SKILL.md Function-Level Gates

Add to `/develop` skill:

```markdown
## SPECIFY Phase: Function-Level Gates

### Incremental Development Rule

When creating new modules:

1. Create ONE file
2. Write contracts for all functions (body = `...`)
3. Run `invar guard -c <file>`
4. Implement functions
5. Run `invar guard --changed`
6. Proceed to next file

❌ Do NOT create multiple file skeletons at once
❌ Do NOT "structure first, fill later"

### TodoList Pattern: Interleaved SPECIFY/BUILD

For each function:

```
□ [SPECIFY] Write contract for validate_input
□ [BUILD] Implement validate_input
□ [SPECIFY] Write contract for process_data
□ [BUILD] Implement process_data
```

NOT:

```
□ [SPECIFY] Write all contracts
□ [BUILD] Implement all functions
```

### Per-Function Checkpoint

After writing each function's contract, show in response:

```python
@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def calculate_average(items: list[float]) -> float:
    """Calculate average of non-empty list."""
    ...
```

Then run:
```
$ invar guard -c src/module.py
Coverage: 1/1 (100%) ✓
```

Only then implement.

### Violation Self-Check

Before writing ANY implementation code, ask:

1. "Have I written the contract for THIS function?"
2. "Have I shown it in my response?"
3. "Have I run `invar guard -c`?"

If any NO → Stop. Write contract first.
```

---

### Component 3: Batch Creation Detection

```python
def detect_batch_creation(
    path: Path,
    git_status: GitStatus,
    threshold: int = 3
) -> BatchWarning | None:
    """
    Detect batch file creation without contracts.

    @pre: path.exists()
    @post: lambda result: result is None or result.file_count >= threshold
    """
    new_files = git_status.untracked + git_status.added
    new_py_files = [f for f in new_files if f.suffix == '.py']

    uncovered = []
    for file in new_py_files:
        coverage = calculate_file_coverage(file)
        if coverage.percentage < 50:
            uncovered.append((file, coverage))

    if len(uncovered) >= threshold:
        return BatchWarning(
            file_count=len(uncovered),
            files=uncovered,
            message="Multiple new files with low contract coverage"
        )

    return None
```

---

### Component 4: Layered Supervision

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Self-Check (SKILL.md) - 0 tokens                  │
│  ├── Violation Self-Check questions                         │
│  ├── Interleaved TodoList pattern                           │
│  └── Incremental file creation rule                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Guard Check (~0.2s) - per function/file           │
│  ├── invar guard -c (contract coverage)                     │
│  ├── Trivial contract rejection                             │
│  └── Batch creation warning                                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: /review Adversarial Review (on-demand)            │
│  ├── Triggered by review_suggested from Guard               │
│  ├── Checks contract semantic quality                       │
│  └── High-risk scenarios (security, low coverage)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Comparison

### Before (Failure Mode)

```
User: Implement pattern detection system

Agent:
━━━ /develop → UNDERSTAND ━━━
[Analyze requirements]

━━━ /develop → SPECIFY ━━━
"I'll create the module structure..."
[Create 8 file skeletons at once]
"Structure created."

━━━ /develop → BUILD ━━━
[Implement each file, no contracts]

━━━ /develop → VALIDATE ━━━
$ invar guard
ERROR: 81 missing_contract violations

[Retrofit contracts...]
[Re-run guard...]
[Multiple cycles]
```

### After (Correct Mode)

```
User: Implement pattern detection system

Agent:
━━━ /develop → UNDERSTAND ━━━
[Analyze requirements, plan 8 files]

TodoList:
□ [SPECIFY] contracts for detector.py
□ [BUILD] implement detector.py
□ [SPECIFY] contracts for p0_exhaustive.py
□ [BUILD] implement p0_exhaustive.py
... (interleaved pattern)

━━━ /develop → SPECIFY (detector.py) ━━━

@pre(lambda self, tree, file_path: isinstance(tree, ast.AST))
@post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
    ...

$ invar guard -c src/core/patterns/detector.py
Coverage: 3/3 (100%) ✓

━━━ /develop → BUILD (detector.py) ━━━
[Implement detector.py]

$ invar guard --changed
Guard passed.

━━━ /develop → SPECIFY (p0_exhaustive.py) ━━━
[Next file...]
```

---

## Token/Context Analysis

### Concern: Does This Increase Token Usage?

**Per-function overhead:**
- Showing contract in response: ~50-100 tokens
- Running `guard -c`: ~20 tokens output
- Per function total: ~70-120 tokens

**But consider rework cost without DX-63:**

| Scenario | Token Cost |
|----------|------------|
| Write 8 files without contracts | ~2000 |
| Guard fails with 81 errors | ~1500 |
| Read and understand errors | ~500 |
| Retrofit contracts | ~2000 |
| Re-run guard (multiple times) | ~1000 |
| **Total without DX-63** | **~7000** |

| Scenario | Token Cost |
|----------|------------|
| Write contracts incrementally (8 files) | ~800 |
| Show contracts (8 × 100) | ~800 |
| Run guard -c (8 times) | ~160 |
| Implement (8 files) | ~2000 |
| Final guard (once) | ~200 |
| **Total with DX-63** | **~3960** |

**Net effect: ~43% token reduction** for complex tasks.

### Simple Task Fast Path

For simple tasks (1-2 functions, single file):
- Skip explicit contract display
- Write implementation with inline contracts
- Guard still verifies

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Batch creation (no contracts) | Common | Detected + warned |
| Contract coverage @ BUILD end | 0% | 90%+ |
| Trivial contracts | Allowed | Rejected |
| Contract quality (constraining) | Low | High |
| Guard rework cycles | 3-5 | 1 |
| Token efficiency | Low | High |

---

## Implementation Plan

```
Phase 1: Guard --contracts-only (Core)          [1 day]
├── Create src/invar/core/coverage.py
├── Add -c flag to guard command
├── Implement trivial detection
├── Implement batch warning
└── Add MCP parameter: invar_guard(contracts_only=True)

Phase 2: SKILL.md Updates                       [0.5 day]
├── Add function-level gate rules
├── Add interleaved TodoList pattern
├── Add incremental file creation rule
├── Add Violation Self-Check
└── Run invar sync-self

Phase 3: Documentation                          [0.5 day]
├── Update this proposal
├── Add workflow example to .invar/examples/
└── Update INVAR.md if needed

Total: ~2 days
```

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Simple task overhead | Low | Single-function changes can skip gate |
| Agent ignores warnings | Medium | Guard can be configured ERROR vs WARN |
| Contracts hard to design upfront | Medium | Allow iteration, but must have constraining contract first |
| Context usage increase | Low | Interleaved mode reduces rework, net decrease |

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Allow placeholder contracts? | **No.** Trivial contracts defeat the purpose. |
| Per-function or per-phase gate? | **Per-function.** Prevents batch bypass. |
| Supervisor agent needed? | **No.** Layered approach (self-check + Guard + /review) sufficient. |
| Token overhead acceptable? | **Yes.** Net reduction due to avoided rework. |

---

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│  DX-63: Contracts-First Enforcement                         │
│                                                             │
│  Core Changes:                                              │
│  1. Phase-level gates → Function-level gates                │
│  2. Allow batch creation → Detect and warn batch creation   │
│  3. Allow placeholder → Reject trivial contracts            │
│  4. All-at-once SPECIFY → Interleaved SPECIFY/BUILD         │
│                                                             │
│  New Tools:                                                 │
│  • invar guard --contracts-only / -c                        │
│  • Trivial contract detection                               │
│  • Batch creation warning                                   │
│                                                             │
│  Expected Outcomes:                                         │
│  • Contracts precede implementation                         │
│  • Contract quality improves (constraining vs descriptive)  │
│  • Reduce rework cycles                                     │
│  • Improve token efficiency                                 │
│  • Batch creation bypass eliminated                         │
└─────────────────────────────────────────────────────────────┘
```

---

## References

- DX-51: Workflow Phase Visibility
- DX-54: Agent-Native Context Management
- DX-61: Functional Pattern Guidance (case study)
- DX-62: Proactive Reference Reading
