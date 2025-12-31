# LX-05: Language-Agnostic Protocol Extraction

**Status:** Draft
**Priority:** Medium
**Category:** Language/Agent eXtensions
**Created:** 2025-12-30
**Based on:** LX-01 (feasibility), LX-04 (multi-agent), INVAR.md v5.0
**Depends on:** LX-04 completion

## Executive Summary

Extract a language-agnostic version of the Invar protocol and skills that can be applied to any programming language. The core insight: **80% of Invar's value is in workflow and agent discipline, not Python-specific tools**.

## Problem Statement

### Current INVAR.md Content Analysis

| Section | Lines | Language-Specific | Universal |
|---------|-------|-------------------|-----------|
| Six Laws | 10 | 10% (@pre/@post mention) | 90% |
| Core/Shell | 40 | 60% (Python imports, syntax) | 40% |
| Contract Rules | 45 | 100% (Python lambda syntax) | 0% |
| Check-In | 15 | 0% | 100% |
| USBV Workflow | 25 | 10% (guard command) | 90% |
| Visible Workflow | 25 | 20% (Python examples) | 80% |
| Task Completion | 10 | 0% | 100% |
| Markers | 35 | 80% (Python decorators) | 20% |
| Commands | 15 | 100% (Python tools) | 0% |
| **Total** | ~220 | **~45%** | **~55%** |

**Conclusion:** Over half of INVAR.md is already language-agnostic conceptually.

### Skill Content Analysis

| Skill | Language-Specific | Universal |
|-------|-------------------|-----------|
| `/develop` | 15% (guard command refs) | 85% |
| `/investigate` | 5% (sig/map refs) | 95% |
| `/propose` | 0% | 100% |
| `/review` | 10% (guard refs) | 90% |

**Conclusion:** Skills are 90%+ language-agnostic.

## Proposed Architecture

### Layer 1: Universal Protocol (`invar-protocol`)

```
invar-protocol/
├── PROTOCOL.md              # Core methodology (language-agnostic)
│   ├── Six Laws             # Universal principles
│   ├── USBV Workflow        # Universal process
│   ├── Check-In/Final       # Session boundaries
│   ├── Visible Workflow     # Progress tracking
│   └── Task Completion      # Done criteria
│
├── ARCHITECTURE.md          # Core/Shell concepts
│   ├── Separation Principle # Pure vs I/O
│   ├── Decision Tree        # Universal (no language examples)
│   └── Size Limits          # Function/file guidelines
│
├── CONTRACTS.md             # Contract concepts (not syntax)
│   ├── Preconditions        # Input constraints concept
│   ├── Postconditions       # Output guarantees concept
│   ├── Invariants           # State consistency concept
│   └── Self-Test Rule       # "Can others implement from spec?"
│
├── skills/                  # Universal skill definitions
│   ├── develop.md           # USBV implementation skill
│   ├── investigate.md       # Research skill
│   ├── propose.md           # Decision facilitation
│   └── review.md            # Adversarial review
│
└── schema/                  # Format specifications
    ├── claude-md.schema.md  # CLAUDE.md structure
    ├── context.schema.md    # context.md structure
    └── skill.schema.md      # Skill file structure
```

### Layer 2: Language Adapters

```
invar-python/               # Current (refactored)
├── CONTRACTS-PYTHON.md     # @pre/@post lambda syntax
├── TOOLS-PYTHON.md         # guard, sig, map specifics
├── templates/
│   └── examples/           # Python code examples
└── runtime/                # invar_runtime package

invar-typescript/           # Future
├── CONTRACTS-TS.md         # Zod/io-ts patterns
├── TOOLS-TS.md             # ESLint, fast-check
└── templates/
    └── examples/           # TypeScript examples

invar-rust/                 # Future
├── CONTRACTS-RUST.md       # contracts crate, proptest
├── TOOLS-RUST.md           # clippy, cargo test
└── templates/
    └── examples/           # Rust examples
```

## Universal Protocol Content

### PROTOCOL.md (Draft)

```markdown
# The Invar Protocol (Universal)

> **"Trade structure for safety."**

## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Pure logic / I/O physically separate |
| 2. Contract Complete | Preconditions + Postconditions + Examples uniquely determine implementation |
| 3. Context Economy | Overview → Signatures → Code (only read what's needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct; verify all paths |

## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Activities |
|-------|---------|------------|
| UNDERSTAND | Know what and why | Intent, Inspect existing code, Constraints |
| SPECIFY | Define boundaries | Preconditions, Postconditions, Examples |
| BUILD | Write code | Implement leaves, Compose |
| VALIDATE | Confirm correctness | Run verification, Review if needed |

**Key:** Inspect before Contract. Contracts before Code.

## Session Protocol

### Check-In (Required)

Your first message MUST display:
```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

### Final (Required)

Your last message for implementation tasks MUST display:
```
✓ Final: verification PASS | <summary>
```

## Visible Workflow

For complex tasks (3+ functions), show checkpoints:
```
□ [UNDERSTAND] Task, context, constraints
□ [SPECIFY] Contracts and design decomposition
□ [VALIDATE] Verification results, integration status
```

## Task Completion

A task is complete only when ALL conditions met:
- Check-In displayed
- Intent explicitly stated
- Contracts written before implementation
- Final displayed with passing verification
- User requirement satisfied

## Contract Concepts

### Precondition
Constraints on inputs that must be true before function executes.
```
PRECONDITION: input_value > 0 AND input_value < 100
```

### Postcondition
Guarantees about outputs that must be true after function executes.
```
POSTCONDITION: result >= 0
```

### Self-Test Rule
> "Can someone else write the exact same function from just the contracts + examples?"

If yes → Contracts are complete.
If no → Add more constraints or examples.
```

### ARCHITECTURE.md (Draft)

```markdown
# Core/Shell Architecture (Universal)

## Separation Principle

| Zone | Purpose | Characteristics |
|------|---------|-----------------|
| **Core** | Pure logic | No I/O, deterministic, testable |
| **Shell** | I/O operations | File/network/time access, error handling |

## Decision Tree

```
Does this function...
│
├─ Read or write files? ──────────────→ Shell
├─ Make network requests? ────────────→ Shell
├─ Access current time? ──────────────→ Shell OR inject as parameter
├─ Generate random values? ───────────→ Shell OR inject as parameter
├─ Print output? ─────────────────────→ Shell (return data instead)
├─ Access environment? ───────────────→ Shell
│
└─ None of the above? ────────────────→ Core
```

## Injection Pattern

Instead of accessing impure values directly, inject them as parameters:

```
# Core: receives 'current_time' as parameter (pure)
function is_expired(expiry, current_time):
    return current_time > expiry

# Shell: calls with actual time
expired = is_expired(token.expiry, get_current_time())
```

## Size Guidelines

| Component | Recommended Limit | Rationale |
|-----------|-------------------|-----------|
| Function body | ~50 lines | Comprehensible unit |
| File | ~500 lines | Manageable module |
| Entry point | ~15 lines | Thin delegation layer |
```

### skills/develop.md (Universal Draft)

```markdown
# /develop Skill (Universal)

> **Mindset:** CONTRACTS before code — no exceptions.

## Scope Boundaries

**This skill IS for:** Implementing features, Fixing bugs, Modifying existing code
**This skill is NOT for:** Exploring unclear requirements → /investigate first

## Entry Actions

1. Read context file for project state
2. Understand the task requirements

## USBV Phases

### UNDERSTAND (Phase 1)
- What exactly needs to be done?
- Review existing code structure
- Identify constraints and dependencies

### SPECIFY (Phase 2)
- Write preconditions and postconditions BEFORE implementation
- Add examples for expected behavior
- Design function decomposition if complex

### BUILD (Phase 3)
- Follow the contracts from SPECIFY
- Implement leaf functions first
- Compose into larger functions

### VALIDATE (Phase 4)
- Run verification tool
- Fix any failures
- Show Final summary

## New Function Gate (MANDATORY)

| Check | If NO → Action |
|-------|----------------|
| Contract shown in SPECIFY phase? | STOP. Return to SPECIFY. |
| Example written? | STOP. Write example first. |

## Exit Criteria

- Verification passes
- Final displayed
- User requirement satisfied
```

## Language Adapter Specification

### Contract Syntax Mapping

| Concept | Python | TypeScript | Rust | Go |
|---------|--------|------------|------|-----|
| **Precondition** | `@pre(lambda x: x > 0)` | `@Pre(x => x > 0)` or Zod | `#[pre(x > 0)]` | `// @pre: x > 0` |
| **Postcondition** | `@post(lambda r: r >= 0)` | `@Post(r => r >= 0)` | `#[post(ret >= 0)]` | `// @post: ret >= 0` |
| **Example** | Doctest `>>>` | JSDoc `@example` | `/// # Examples` | `// Example:` |
| **Pure/IO split** | `core/` vs `shell/` | Same or `pure/` | Same | Same |
| **Error type** | `Result[T, E]` | `Result<T, E>` | `Result<T, E>` | `(T, error)` |

### Verification Tool Mapping

| Layer | Python | TypeScript | Rust | Go |
|-------|--------|------------|------|-----|
| **Static** | Ruff, mypy | ESLint, tsc | Clippy | go vet |
| **Examples** | pytest doctest | Jest/Vitest | cargo test --doc | go test |
| **Property** | Hypothesis | fast-check | proptest | gopter |
| **Symbolic** | CrossHair | N/A | KLEE/MIRI | N/A |

### Adapter Interface

```
LanguageAdapter:
  - detect(path) → bool           # Is this a {language} project?
  - verify(path, options) → Result  # Run verification
  - signatures(file) → Signature[]  # Extract contracts
  - symbols(path) → SymbolMap       # Build reference map
  - patterns() → PatternDefs        # Core/Shell patterns
```

## Implementation Plan

### Phase 1: Extract Universal Protocol (1 week)

| Task | Output |
|------|--------|
| 1.1 Create PROTOCOL.md | Universal Six Laws, USBV, Session Protocol |
| 1.2 Create ARCHITECTURE.md | Universal Core/Shell, Decision Tree |
| 1.3 Create CONTRACTS.md | Concept definitions (not syntax) |
| 1.4 Universalize skills | Remove Python-specific references |

### Phase 2: Create Python Adapter Docs (0.5 week)

| Task | Output |
|------|--------|
| 2.1 Create CONTRACTS-PYTHON.md | @pre/@post lambda syntax, deal specifics |
| 2.2 Create TOOLS-PYTHON.md | guard, sig, map command details |
| 2.3 Update INVAR.md | Reference universal + Python docs |

### Phase 3: Validate with TypeScript Sketch (1 week)

| Task | Output |
|------|--------|
| 3.1 Create CONTRACTS-TS.md | Zod/io-ts patterns, JSDoc conventions |
| 3.2 Create TOOLS-TS.md | ESLint + fast-check integration sketch |
| 3.3 Create TS examples | Core/Shell TypeScript examples |
| 3.4 Validate universality | Can protocol apply without Python refs? |

**Total: 2.5 weeks**

## File Structure After Implementation

```
INVAR.md                    # Combines: Universal Protocol + Python Adapter
                            # (Single file for backward compatibility)

docs/protocol/              # NEW: Universal protocol (extracted)
├── PROTOCOL-UNIVERSAL.md   # Six Laws, USBV, Session (no code examples)
├── ARCHITECTURE-UNIVERSAL.md # Core/Shell concepts (no code examples)
├── CONTRACTS-UNIVERSAL.md  # Contract concepts (no syntax)
└── skills/
    ├── develop-universal.md
    ├── investigate-universal.md
    ├── propose-universal.md
    └── review-universal.md

docs/adapters/              # NEW: Language-specific
├── python/
│   ├── CONTRACTS.md        # @pre/@post syntax, deal
│   ├── TOOLS.md            # guard, sig, map
│   └── EXAMPLES.md         # Python code examples
└── typescript/             # Future
    ├── CONTRACTS.md        # Zod, JSDoc
    ├── TOOLS.md            # ESLint, fast-check
    └── EXAMPLES.md         # TS code examples
```

## Benefits

1. **Broader Applicability** — Protocol useful beyond Python
2. **Clearer Separation** — What's universal vs what's tooling
3. **Easier Onboarding** — Learn concepts first, then syntax
4. **Community Adapters** — Others can create language support
5. **Agent Portability** — Same workflow for any language

## Risks

| Risk | Mitigation |
|------|------------|
| Over-abstraction | Keep concrete Python path as primary |
| Maintenance burden | Universal docs are stable, adapters change |
| Confusion | INVAR.md stays as combined "quick start" |

## Success Criteria

- [ ] Universal protocol docs readable without Python knowledge
- [ ] Python adapter docs add only Python-specific details
- [ ] TypeScript sketch validates universality
- [ ] Existing Python users see no breaking changes
- [ ] At least 1 non-Python project can use universal protocol

## Open Questions

1. **Single file vs split?** Keep INVAR.md as combined, or split into multiple?
2. **Skills:** Should skills reference verification tools generically?
3. **Agent instructions:** Should CLAUDE.md have universal + adapter sections?

## Appendix: Universal Contract Examples (Pseudocode)

```
// PSEUDOCODE - Not tied to any language

FUNCTION calculate_discount(price, rate):
    PRECONDITION: price > 0 AND 0 <= rate <= 1
    POSTCONDITION: result >= 0

    EXAMPLE: calculate_discount(100, 0.2) → 80.0
    EXAMPLE: calculate_discount(100, 0) → 100.0  // Edge: no discount

    RETURNS: price * (1 - rate)

// Self-test: Can you implement this from just the spec above?
// If yes → Contract is complete.
```

---

*LX-05 builds on LX-01 feasibility analysis and LX-04 multi-agent infrastructure.*
