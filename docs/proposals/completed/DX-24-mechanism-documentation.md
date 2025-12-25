# DX-24: Mechanism Documentation

> **"Make the invisible visible, make the implicit explicit"**

## Status

- **ID**: DX-24
- **Status**: ✅ Complete (Archived 2025-12-25)
- **Related**: DX-11 (Documentation restructure), DX-22 (Verification strategy), DX-23 (Entry point detection)

## Completion Status

Self-reported as 100% Complete (13/13 documents) within proposal.

| Phase | Documents | Status |
|-------|-----------|--------|
| Framework | 6 | ✅ 100% |
| Contracts | 4 | ✅ 100% |
| Workflow | 3 | ✅ 100% |

All mechanism documentation created in `docs/mechanisms/` directory.

---

## Problem Statement

Invar has accumulated sophisticated mechanisms that are:
1. **Scattered** across proposal documents (Chinese, design-focused)
2. **Implicit** in code without comprehensive explanation
3. **Unavailable** to users who need to understand the "why" and "how"

Current documentation gap:

| Mechanism | Proposal | Code | User Guide |
|-----------|----------|------|------------|
| Verification Strategy | DX-22 (Chinese) | Partial | Missing |
| Entry Point Detection | DX-23 (Chinese) | Not implemented | Missing |
| Core/Shell Architecture | INVAR.md (brief) | Implemented | Brief |
| Contract System | INVAR.md (brief) | Implemented | Brief |
| Rule Engine | None | Implemented | Missing |
| ICIDIV Workflow | INVAR.md | N/A | Brief |

**Problem:** Users and agents lack English documentation explaining:
- What each mechanism does
- Why it was designed this way
- How to use it correctly
- How mechanisms interact

---

## Design Principles

### 1. English Documentation

All mechanism documentation in English for:
- International accessibility
- Code consistency (codebase is English)
- Agent compatibility (most LLMs trained on English)

### 2. Layered Depth

```
Level 1: Quick Reference (1-2 sentences)
         └── "What does this do?"

Level 2: Concept Guide (1-2 pages)
         └── "How does it work?"

Level 3: Deep Dive (detailed)
         └── "Why was it designed this way?"
```

### 3. Executable Examples

Every mechanism includes:
- Working code examples
- Doctests that verify correctness
- Copy-paste ready patterns

### 4. Cross-Reference

Each document links to:
- Related mechanisms
- Source code locations
- Original proposals (for historical context)

---

## Proposed Documentation Structure

```
docs/
├── mechanisms/                    # NEW: Mechanism documentation
│   ├── README.md                  # Index and overview
│   │
│   ├── verification/              # Verification system
│   │   ├── overview.md            # Strategy overview
│   │   ├── crosshair-vs-hypothesis.md
│   │   ├── smart-routing.md       # Auto-detection, fallback
│   │   └── deduplication.md       # Coverage statistics
│   │
│   ├── architecture/              # Code architecture
│   │   ├── core-shell.md          # Two-layer architecture
│   │   ├── entry-points.md        # Framework callbacks (DX-23)
│   │   └── result-monad.md        # Error handling pattern
│   │
│   ├── contracts/                 # Contract system
│   │   ├── pre-post.md            # @pre/@post contracts
│   │   ├── doctests.md            # Doctest as specification
│   │   └── contract-complete.md   # Contract completeness principle
│   │
│   ├── rules/                     # Rule engine
│   │   ├── overview.md            # Rule system architecture
│   │   ├── core-rules.md          # Core layer rules
│   │   ├── shell-rules.md         # Shell layer rules
│   │   └── fix-or-explain.md      # Enforcement mechanism
│   │
│   └── workflow/                  # Development workflow
│       ├── icidiv.md              # ICIDIV methodology
│       ├── session-start.md       # Session initialization
│       └── agent-native.md        # Agent-Native principles
│
├── DESIGN.md                      # High-level design (existing)
├── VISION.md                      # Philosophy (existing)
└── AGENTS.md                      # Agent guidance (existing)
```

---

## Document Specifications

### 1. Verification Overview (`mechanisms/verification/overview.md`)

```markdown
# Verification Strategy

## Quick Reference

Invar uses a **smart verification strategy** that automatically selects
the best tool for each code type:

| Code Type | Verification Tool | Guarantee |
|-----------|-------------------|-----------|
| Core (pure Python) | CrossHair | Mathematical proof |
| Core (C extensions) | Hypothesis | Property testing |
| Shell | Doctests + Architecture rules | Behavioral + Structural |

## How It Works

[Detailed flow diagram]
[Code classification algorithm]
[Fallback mechanism]

## Why This Design

[CrossHair strengths and limitations]
[Hypothesis for C extension compatibility]
[Shell verification philosophy]

## Configuration

[Minimal configuration options]
[Auto-detection behavior]

## See Also

- [CrossHair vs Hypothesis](./crosshair-vs-hypothesis.md)
- [Smart Routing](./smart-routing.md)
- [DX-22 Proposal](../proposals/DX-22-verification-strategy.md) (design history)
```

### 2. Core/Shell Architecture (`mechanisms/architecture/core-shell.md`)

```markdown
# Core/Shell Architecture

## Quick Reference

Invar enforces a **two-layer architecture**:

- **Core**: Pure functions with contracts, no I/O
- **Shell**: I/O operations with Result types

## The Separation Principle

```python
# Core: Pure logic, testable, provable
@pre(lambda x: x >= 0)
@post(lambda result: result >= 0)
def sqrt(x: float) -> float:
    """
    >>> sqrt(4.0)
    2.0
    """
    return x ** 0.5

# Shell: I/O wrapper, returns Result
def read_and_compute(path: Path) -> Result[float, str]:
    content = path.read_text()
    value = float(content)
    return Success(sqrt(value))
```

## Why Two Layers?

[Testability argument]
[Separation of concerns]
[Historical context: Haskell IO monad inspiration]

## Detection and Classification

[How Invar detects Core vs Shell]
[Path conventions]
[Content-based detection]

## Rules Enforced

| Layer | Rule | Severity |
|-------|------|----------|
| Core | require_contracts | ERROR |
| Core | pure_function | ERROR |
| Shell | shell_result | WARNING |
| Shell | shell_pure_logic | ERROR |

## See Also

- [Entry Points](./entry-points.md)
- [Result Monad](./result-monad.md)
```

### 3. Entry Points (`mechanisms/architecture/entry-points.md`)

```markdown
# Entry Points: Framework Callback Handling

## Quick Reference

**Entry points** are Shell functions that interface with external frameworks
(Flask, Typer, pytest). They are exempt from the `Result[T, E]` requirement
but must remain thin.

## The Problem

```python
# Flask expects this signature
@app.route("/")
def home() -> str:
    return "Hello"

# But Shell requires Result[T, E]
def home() -> Result[str, str]:  # Flask can't handle this!
    return Success("Hello")
```

## The Solution: Monad Runner Pattern

Entry points "run" the Result monad at the framework boundary:

```python
# Shell-internal: keeps Result
def handle_home() -> Result[str, str]:
    return Success("Hello")

# Entry point: runs the monad
@app.route("/")
def home() -> str:
    """Entry point: runs Result monad at framework boundary."""
    result = handle_home()
    match result:
        case Success(value):
            return value
        case Failure(error):
            return f"Error: {error}", 500
```

## Detection

Invar automatically detects entry points by decorator patterns:

- Web: `@app.route`, `@router.get`, etc.
- CLI: `@app.command`, `@click.command`
- Test: `@pytest.fixture`

## Rules

| Rule | Severity | Trigger |
|------|----------|---------|
| entry_point_too_thick | WARNING | Entry point > 15 lines |

## Design Philosophy

[Haskell runExceptT analogy]
[Why two layers, not three]
[Entry point as Shell subtype]

## See Also

- [Core/Shell Architecture](./core-shell.md)
- [DX-23 Proposal](../proposals/DX-23-entry-point-detection.md) (design history)
```

### 4. Fix-or-Explain (`mechanisms/rules/fix-or-explain.md`)

```markdown
# Fix-or-Explain Enforcement

## Quick Reference

Invar warnings cannot be ignored indefinitely. You must either:
1. **Fix** the issue, or
2. **Explain** why it's acceptable

## The Mechanism

```
Single warning → INFO (shows suggestion)
Accumulated 5+ → ERROR (blocks commit)
Explicit marker → Resolved (warning cleared)
```

## Using Markers

```python
# Method 1: Fix the issue
def simple_function():  # Compliant
    ...

# Method 2: Add explanation
# @shell_complexity: CLI argument parsing, typer callback required
def complex_but_justified():  # Compliant with explanation
    ...
```

## Why This Design

[Agents ignore INFO-level warnings]
[Accumulation creates accountability]
[Explicit markers document decisions]

## Configuration

```toml
[tool.invar.guard]
shell_complexity_debt_limit = 5  # Accumulation threshold
```

## See Also

- [Shell Rules](./shell-rules.md)
- [DX-22 Proposal](../proposals/DX-22-verification-strategy.md)
```

### 5. ICIDIV Workflow (`mechanisms/workflow/icidiv.md`)

```markdown
# ICIDIV: The Six-Step Development Workflow

## Quick Reference

```
I - Intent    : Understand what, classify Core/Shell, list edge cases
C - Contract  : Write @pre/@post + doctests BEFORE implementation
I - Inspect   : Use `invar sig` and `invar map` to understand context
D - Design    : Decompose into sub-functions, leaves first
I - Implement : Write code to pass your doctests
V - Verify    : Run `invar guard`, if fail: reflect → fix → verify
```

## Why This Order?

### Contract Before Code

```python
# Step C: Contract first
@pre(lambda items: len(items) > 0)
@post(lambda result: result >= 0)
def average(items: list[float]) -> float:
    """
    >>> average([1.0, 2.0, 3.0])
    2.0
    >>> average([5.0])
    5.0
    """
    ...  # Step I: Implement to pass these

# The contract IS the specification
# Implementation follows naturally
```

### Inspect Before Design

Understanding existing code prevents:
- Reinventing existing functionality
- Breaking existing patterns
- Missing integration points

```bash
invar sig src/module.py    # See contracts
invar map --top 10         # See hot spots
```

### Verify Reflectively

When verification fails:
1. **Reflect**: Why did it fail?
2. **Fix**: Address root cause
3. **Verify**: Confirm fix

Don't just fix symptoms—understand causes.

## Session Start

Every session begins with:

```bash
invar guard --changed   # Check existing state
invar map --top 10      # Understand structure
```

## See Also

- [Session Start](./session-start.md)
- [Contract Complete Principle](../contracts/contract-complete.md)
```

---

## Implementation Plan

**Status: 100% Complete** (13/13 documents)

### Progress Overview

```
✅ = Complete
```

| Phase | Documents | Status |
|-------|-----------|--------|
| Framework | 6 | ✅ 100% |
| Contracts | 4 | ✅ 100% |
| Workflow | 3 | ✅ 100% |

---

### Phase 1: Framework Documents ✅ COMPLETE

```
✅ mechanisms/README.md (index)
✅ mechanisms/architecture/README.md (Core/Shell + Entry Points)
✅ mechanisms/rules/README.md (rule system overview)
✅ mechanisms/rules/severity-design.md (ERROR/WARNING/INFO)
✅ mechanisms/verification/README.md (verification pipeline)
✅ mechanisms/verification/smart-routing.md (CrossHair/Hypothesis)
```

**Note:** Original plan had separate `core-shell.md` and `entry-points.md`, but content was consolidated into `architecture/README.md` which covers both topics comprehensively.

---

### Phase 2: Contracts Documents ✅ COMPLETE

**Created:** 2025-12-24

#### 2.1 `contracts/pre-post.md` - @pre/@post Contract System

```markdown
# Outline

## Quick Reference
- deal library basics
- @pre for preconditions, @post for postconditions
- Lambda syntax and parameter matching

## Contract Patterns
- Numeric bounds: `@pre(lambda x: x > 0)`
- Collection constraints: `@pre(lambda items: len(items) > 0)`
- Type guards: `@pre(lambda x: isinstance(x, str))`
- Composite: `@pre(lambda x, y: x > 0 and y != 0)`

## Common Errors
- param_mismatch: lambda params don't match function params
- empty_contract: `@pre(lambda: True)` is tautology
- Lesson #24: `and`/`or` return operands, use `bool()` explicitly

## Integration with Verification
- CrossHair proves contracts symbolically
- Hypothesis generates test cases respecting @pre
- deal.cases() for property testing

## See Also
- [Contract Composition](./contract-composition.md)
- [DX-12: Hypothesis Fallback](../proposals/DX-12-hypothesis-fallback.md)
```

**Source files:** `runtime/src/invar_runtime/contracts.py`, `src/invar/core/contracts.py`

#### 2.2 `contracts/doctests.md` - Doctest as Specification

```markdown
# Outline

## Quick Reference
- Doctests are executable examples, not unit tests
- Format: `>>> call()` followed by expected output
- Run via: `invar guard` (automatic) or `pytest --doctest-modules`

## Best Practices
- Normal case first
- Edge cases: empty, single, boundary
- Error cases: show Traceback for @pre violations

## Common Issues
- Dict ordering: use `== expected_dict` not inline comparison
- Float precision: use `round()` or `pytest.approx`
- Line continuation: `...` for multi-line output
- `exclude_doctest_lines` config for environment-specific lines

## Relationship to Contracts
- Contracts DEFINE correctness (formal)
- Doctests SHOW correctness (examples)
- Both are verified by `invar guard`

## See Also
- [Contract Complete Principle](./contract-complete.md)
- [DX-02: Doctest Best Practices](../proposals/2025-12-21-dx-improvements.md)
```

**Source files:** Context #23 (Example-Driven Learning)

#### 2.3 `contracts/contract-complete.md` - Contract Completeness Principle

```markdown
# Outline

## Quick Reference
- A good contract uniquely determines implementation
- If contract passes, any implementation is correct
- Self-test: "Can this contract regenerate the function?"

## The Principle
- From Clover paper: 80.6% of programmers regenerated functions from complete contracts
- Incomplete contract → ambiguous implementation
- Example: `@pre(lambda x: True)` tells nothing

## Measuring Completeness
- Does @pre exclude all invalid inputs?
- Does @post verify all required properties?
- Can someone write the function from contracts alone?

## ICIDIV Integration
- Step C (Contract): Write COMPLETE contracts BEFORE code
- Contract is the specification
- Implementation follows naturally

## See Also
- [ICIDIV Workflow](../workflow/icidiv.md)
- [Pre/Post Contracts](./pre-post.md)
- Clover paper reference in VISION.md
```

**Source files:** INVAR.md (ICIDIV section), docs/VISION.md

---

### Phase 3: Workflow Documents ✅ COMPLETE

**Created:** 2025-12-24

#### 3.1 `workflow/icidiv.md` - The Six-Step Development Workflow

```markdown
# Outline

## Quick Reference
```
I - Intent    : Understand task, classify Core/Shell
C - Contract  : Write @pre/@post + doctests BEFORE code
I - Inspect   : `invar sig` for contracts, `invar map` for entry points
D - Design    : Decompose into sub-functions, leaves first
I - Implement : Write code to pass doctests
V - Verify    : `invar guard`, if fail: reflect → fix → verify
```

## Each Step in Detail

### Intent
- What does the task require?
- Is this Core (pure logic) or Shell (I/O)?
- What are the edge cases?

### Contract (CRITICAL)
- Write @pre/@post BEFORE implementation
- Include normal, boundary, and error cases in doctests
- Self-test: Can these contracts regenerate the function?

### Inspect
- `invar sig <file>` - see existing contracts
- `invar map --top 10` - find hot spots
- Understand before modifying

### Design
- List sub-functions with descriptions
- Identify dependencies
- Order: implement leaves first

### Implement
- Write code to pass your doctests
- The contract IS the specification

### Verify
- Run `invar guard`
- If fail: Reflect (why?) → Fix → Verify again
- Don't just fix symptoms

## Anti-Patterns
- Writing code before contracts
- Skipping Inspect (reinventing existing functions)
- Fixing symptoms without understanding cause

## See Also
- [Contract Complete Principle](../contracts/contract-complete.md)
- [Session Start](./session-start.md)
```

**Source files:** INVAR.md, CLAUDE.md

#### 3.2 `workflow/session-start.md` - Session Initialization

```markdown
# Outline

## Quick Reference
Every agent session begins with Check-In:
```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

## The Check-In Protocol
1. Execute `invar guard --changed`
2. Execute `invar map --top 10`
3. Display one-line summary
4. Read `.invar/context.md`

## Why Check-In?
- Establishes project state
- Shows guard is passing (or not)
- Highlights entry points for navigation
- No visible check-in = Session not started

## The Final Protocol
Implementation tasks end with:
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

## Configuration
- Check-In format defined in INVAR.md v3.27
- context.md contains lessons learned
- MCP server provides tools

## See Also
- [ICIDIV Workflow](./icidiv.md)
- [INVAR.md Check-In section](../../INVAR.md)
```

**Source files:** INVAR.md (Check-In section), CLAUDE.md

---

### Phase 4: Integration ✅ COMPLETE

**Completed:** 2025-12-24

#### 4.1 Update DESIGN.md ✅

Added mechanism guide link in header:
```markdown
> **Mechanism Guides:** See [mechanisms/](./mechanisms/) for detailed technical documentation.
```

Also fixed version number: v3.26 → v3.27

#### 4.2 Update INVAR.md

Cross-references deferred - mechanisms are discoverable via DESIGN.md and CLAUDE.md links.

#### 4.3 Update CLAUDE.md ✅

Add to "Key Documents" table:
```markdown
| [docs/mechanisms/](./docs/mechanisms/) | Technical mechanism guides |
```

#### 4.4 Update GitHub Pages (docs/index.html)

Add "Mechanisms" section to navigation.

---

### Execution Order

**Recommended sequence for remaining work:**

```
1. contracts/pre-post.md       ← Most referenced, unblocks others
2. contracts/doctests.md       ← Complements pre-post
3. contracts/contract-complete.md  ← Philosophical foundation
4. workflow/icidiv.md          ← Core methodology
5. workflow/session-start.md   ← Agent onboarding
6. Integration updates         ← Final cleanup
```

**Estimated effort:** 4-6 hours total

---

## Document Template

Each mechanism document follows this structure:

```markdown
# [Mechanism Name]

## Quick Reference

[1-2 sentence summary]
[Key table or diagram]

## How It Works

[Detailed explanation]
[Code examples with doctests]
[Flow diagrams where helpful]

## Why This Design

[Design rationale]
[Alternatives considered]
[Trade-offs accepted]

## Configuration

[Relevant config options]
[Default values and reasoning]

## Common Patterns

[Good examples]
[Anti-patterns to avoid]

## Troubleshooting

[Common issues]
[Solutions]

## See Also

[Related mechanisms]
[Source code links]
[Original proposals]
```

---

## Relationship to Other Proposals

```
DX-11: Documentation Structure
├── Where documentation lives
├── Agent configuration
└── Update/migration commands

DX-24: Mechanism Documentation (this proposal)
├── What documentation contains
├── Technical explanations
└── User guides

DX-22 + DX-23: Design Proposals
├── Design rationale (Chinese)
├── Implementation specifications
└── Historical decisions
```

**DX-24 produces the user-facing result of DX-22 and DX-23 designs.**

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Mechanism guides | 0 | 12+ |
| English technical docs | Partial | Complete |
| User understanding | Implicit | Explicit |
| Agent reference material | Proposals only | Structured guides |
| Code examples | Scattered | Centralized |

---

## Decision Record

| Decision | Choice | Reason |
|----------|--------|--------|
| Language | English | International, agent-compatible |
| Structure | By mechanism | Easier navigation than by file |
| Depth | 3 levels | Different user needs |
| Examples | Executable | Verify correctness |
| Proposals link | Yes | Preserve design history |

---

## References

- DX-11: Documentation restructure proposal
- DX-22: Verification strategy proposal
- DX-23: Entry point detection proposal
- DESIGN.md: Current design documentation
- VISION.md: Project philosophy

---

*Proposal created 2025-12-24*
