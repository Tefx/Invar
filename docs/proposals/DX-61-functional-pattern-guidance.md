# DX-61: Functional Pattern Guidance for Agents

**Status:** Draft
**Created:** 2025-12-28
**Depends on:** DX-25 (Functional Patterns - internal)
**Series:** DX (Developer Experience)

## Executive Summary

Extend Invar from "correctness enforcement" to "quality guidance" by teaching agents proven functional patterns. This transforms Guard from a gatekeeper into a mentor.

**Key Insight:** In vibe coding, the human provides intent; the agent provides implementation. If we only check correctness, we get correct but mediocre code. If we also guide patterns, we get correct AND excellent code.

---

## Problem Statement

### Current State

```
Invar Today:
├── ✅ Catches: Missing contracts, I/O in Core, missing Result
├── ✅ Blocks: Code that violates architecture
└── ❌ Missing: Guidance toward better patterns

Agent writes:
def validate(data: dict) -> Result[Config, str]:
    if "path" not in data:
        return Failure("Missing path")      # First error only
    if "rules" not in data:
        return Failure("Missing rules")     # Never reached
    return Success(Config(...))

Guard says: ✅ PASS (has Result, has contract)

But this is suboptimal! User sees one error at a time.
```

### The Gap

| What Guard Checks | What Guard Could Suggest |
|-------------------|--------------------------|
| Has @pre/@post | Could @pre be more semantic? |
| Returns Result | Could use Validation for multi-error? |
| No I/O in Core | Could use NewType for clarity? |
| Has doctests | Could doctests cover more edges? |

**Guard is binary (pass/fail) when it could be gradient (good/better/best).**

---

## Vision: From Gatekeeper to Mentor

```
Level 1 - Gatekeeper (Current):
"Your code is wrong. Fix it."
→ Agent fixes minimum to pass

Level 2 - Mentor (Proposed):
"Your code works. Here's how to make it better."
→ Agent learns patterns, applies them proactively
```

### Value for Vibe Coding

| Scenario | Without DX-61 | With DX-61 |
|----------|---------------|------------|
| Config validation | Returns first error | Returns all errors |
| Multiple str params | Easy to confuse | NewType prevents mistakes |
| Empty list handling | Runtime crash | Compile-time safety |
| Object construction | Invalid states possible | Smart constructors |

**ROI:** Human says "add validation" once. Agent produces production-quality code, not prototype-quality.

---

## Design Principles

### 1. Suggest, Don't Block

```python
# Guard output levels:
ERROR   # Must fix (current behavior)
WARNING # Should fix (current behavior)
SUGGEST # Could improve (new - never blocks)

# Example:
src/core/config.py
  SUGGEST :15 Multiple string parameters detected
    → Consider NewType for semantic clarity
    → Example: FilePath, ModulePath, SymbolName
```

### 2. Learn from Examples

```python
# .invar/examples/functional.py teaches patterns
# Agent reads examples → Learns patterns → Applies proactively

# Before reading examples:
def find(path: str, name: str) -> Symbol: ...

# After reading examples:
def find(path: ModulePath, name: SymbolName) -> Symbol: ...
```

### 3. Progressive Adoption

```toml
# invar.toml - project can opt-in to stricter checks
[guard.suggestions]
enabled = true              # Show suggestions (default: true)
newtype_threshold = 3       # Suggest NewType when N+ string params
validation_pattern = true   # Detect fail-fast validation
nonempty_pattern = true     # Detect defensive empty checks
```

---

## Proposed Rules

### Rule 1: `suggest_newtype`

**Detects:** Functions with 3+ parameters of the same primitive type

```python
# Triggers suggestion:
def find_symbol(
    module_path: str,    # str #1
    symbol_name: str,    # str #2
    file_pattern: str,   # str #3
) -> Symbol:
    ...

# Suggestion:
SUGGEST: 3 string parameters in 'find_symbol'
  → Consider using NewType for semantic clarity
  → from typing import NewType
  → ModulePath = NewType('ModulePath', str)
  → SymbolName = NewType('SymbolName', str)
```

**Implementation:** AST analysis of function signatures

### Rule 2: `suggest_validation`

**Detects:** Sequential if-return-Failure pattern

```python
# Triggers suggestion:
def validate(data: dict) -> Result[Config, str]:
    if "a" not in data:
        return Failure("missing a")
    if "b" not in data:
        return Failure("missing b")
    if "c" not in data:
        return Failure("missing c")
    return Success(Config(...))

# Suggestion:
SUGGEST: Sequential validation in 'validate' returns first error only
  → Consider Validation pattern to accumulate all errors
  → Users see all problems at once, not one at a time
  → See .invar/examples/functional.py for example
```

**Implementation:** Control flow analysis for consecutive if-Failure patterns

### Rule 3: `suggest_nonempty`

**Detects:** Empty check followed by index access

```python
# Triggers suggestion:
def process(items: list[str]) -> str:
    if not items:
        raise ValueError("empty")
    return items[0]  # Only safe because of check above

# Suggestion:
SUGGEST: Defensive empty check in 'process'
  → Consider NonEmpty[T] type for compile-time safety
  → def process(items: NonEmpty[str]) -> str:
  →     return items.first  # Always safe, no check needed
```

**Implementation:** Pattern matching on AST

### Rule 4: `suggest_smart_constructor`

**Detects:** Dataclass with validation logic in methods

```python
# Triggers suggestion:
@dataclass
class Symbol:
    name: str
    line: int

    def validate(self) -> bool:
        return bool(self.name) and self.line > 0

# Suggestion:
SUGGEST: Dataclass 'Symbol' has external validation
  → Consider smart constructor pattern
  → @classmethod
  → def create(cls, name: str, line: int) -> Result[Symbol, str]:
  →     if not name: return Failure("name required")
  →     return Success(cls(name=name, line=line))
```

**Implementation:** Detect dataclass + validation method pattern

---

## Runtime Library Extensions

### Option A: Extend invar_runtime

```python
# invar_runtime/__init__.py
from .contracts import pre, post, NonEmpty, IsInstance, ...
from .functional import Validation, NonEmptyList  # NEW

# Usage in user projects:
from invar_runtime import Validation, NonEmptyList

def validate(data: dict) -> Validation[Config, str]:
    ...
```

### Option B: Recommend returns library

```python
# Don't reinvent, just recommend
# Guard suggestion points to returns library patterns

SUGGEST: Consider Validation pattern
  → pip install returns
  → from returns.result import Result
  → from returns.pipeline import flow
```

**Recommendation:** Option B - leverage existing ecosystem, don't bloat runtime

---

## Example File

```python
# .invar/examples/functional.py
"""
Functional Patterns for Higher Quality Code

These patterns are SUGGESTIONS, not requirements.
Guard will suggest them when it detects opportunities.
"""

from typing import NewType
from dataclasses import dataclass
from returns.result import Result, Success, Failure

# =============================================================================
# Pattern 1: NewType for Semantic Clarity
# =============================================================================

# BEFORE: Easy to confuse parameters
def find_bad(path: str, name: str, pattern: str) -> Symbol:
    ...

# AFTER: Self-documenting, type-checker catches mistakes
FilePath = NewType('FilePath', str)
ModulePath = NewType('ModulePath', str)
SymbolName = NewType('SymbolName', str)

def find_good(path: ModulePath, name: SymbolName) -> Symbol:
    ...


# =============================================================================
# Pattern 2: Validation for Error Accumulation
# =============================================================================

# BEFORE: User sees one error at a time
def validate_bad(data: dict) -> Result[Config, str]:
    if "path" not in data:
        return Failure("Missing path")
    if "rules" not in data:
        return Failure("Missing rules")  # Never reached if path missing
    return Success(Config(...))

# AFTER: User sees all errors at once
def validate_good(data: dict) -> Result[Config, list[str]]:
    errors: list[str] = []

    if "path" not in data:
        errors.append("Missing path")
    if "rules" not in data:
        errors.append("Missing rules")
    if data.get("max_lines", 0) < 0:
        errors.append("max_lines must be >= 0")

    if errors:
        return Failure(errors)
    return Success(Config(...))


# =============================================================================
# Pattern 3: NonEmpty for Compile-Time Safety
# =============================================================================

@dataclass(frozen=True)
class NonEmpty(Generic[T]):
    """List guaranteed to have at least one element."""
    head: T
    tail: tuple[T, ...]

    @property
    def first(self) -> T:
        return self.head  # Always safe

    @classmethod
    def from_list(cls, items: list[T]) -> Result["NonEmpty[T]", str]:
        if not items:
            return Failure("Cannot create NonEmpty from empty list")
        return Success(cls(head=items[0], tail=tuple(items[1:])))

# BEFORE: Defensive code
def summarize_bad(items: list[str]) -> str:
    if not items:
        raise ValueError("empty")
    return items[0]

# AFTER: Type-safe
def summarize_good(items: NonEmpty[str]) -> str:
    return items.first  # Guaranteed safe


# =============================================================================
# Pattern 4: Smart Constructors
# =============================================================================

# BEFORE: Can create invalid objects
@dataclass
class SymbolBad:
    name: str
    line: int
    # Symbol("", -1) is valid but meaningless

# AFTER: Validation at construction
@dataclass(frozen=True)
class SymbolGood:
    _name: str
    _line: int

    @classmethod
    def create(cls, name: str, line: int) -> Result["SymbolGood", str]:
        if not name:
            return Failure("Symbol name cannot be empty")
        if line < 1:
            return Failure(f"Line must be >= 1, got {line}")
        return Success(cls(_name=name, _line=line))

    @property
    def name(self) -> str:
        return self._name
```

---

## Should We Expand the Laws?

### Current Invar Laws

```
Law 1: Core is Pure (no I/O imports)
Law 2: Core has Contracts (@pre/@post required)
Law 3: Shell Returns Result (error handling explicit)
Law 4: Agent Follows USBV (workflow discipline)
```

### Proposed New Law?

```
Law 5: Prefer Semantic Types (NewType over primitives)?
Law 6: Accumulate Errors (Validation over fail-fast)?
```

### Analysis

| Consideration | Make it a Law | Keep as Suggestion |
|---------------|---------------|-------------------|
| Agent compliance | Higher (forced) | Lower (optional) |
| Adoption friction | Higher | Lower |
| Existing codebase compat | Breaking | Non-breaking |
| False positives | Risk | Safe |
| Code quality floor | Higher | Same |

### Recommendation: Two-Tier System

```
Tier 1 - Laws (ERROR if violated):
├── Core purity
├── Contract presence
├── Shell Result pattern
└── USBV workflow

Tier 2 - Guidance (SUGGEST if opportunity):
├── NewType for clarity
├── Validation for UX
├── NonEmpty for safety
└── Smart constructors
```

**Rationale:**
- Laws are architectural (wrong = broken code)
- Guidance is stylistic (suboptimal = working but improvable)
- Agent learns from suggestions, doesn't fight errors

---

## Implementation Plan

### Phase 1: Examples (0.5 day)
```
□ Create .invar/examples/functional.py
□ Document patterns with before/after
□ Agent learns from examples immediately
```

### Phase 2: Suggestions (1 day)
```
□ Add SUGGEST severity level to Guard
□ Implement suggest_newtype rule
□ Implement suggest_validation rule
□ Output format: non-blocking, educational
```

### Phase 3: Config (0.5 day)
```
□ Add [guard.suggestions] to config
□ Allow per-project opt-in/out
□ Threshold configuration
```

### Phase 4: Documentation (0.5 day)
```
□ Update INVAR.md with Tier 2 guidance
□ Add to .invar/context.md lessons
□ Blog post on pattern adoption
```

**Total: ~2.5 days**

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Agent uses NewType | ~5% | ~40% |
| Multi-error validation | ~10% | ~60% |
| NonEmpty usage | ~2% | ~20% |
| Smart constructors | ~15% | ~50% |

**Measurement:** Sample agent-generated code before/after DX-61

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Too many suggestions overwhelm | Limit to 3 per file, most impactful |
| False positives annoy | High confidence threshold, easy dismiss |
| Agents ignore suggestions | Track adoption, adjust presentation |
| Conflicts with project style | Config to disable specific suggestions |

---

## Relationship to Vibe Coding

```
Traditional Coding:
Human writes code → Human reviews → Human improves

Vibe Coding (Current):
Human describes → Agent writes → Guard blocks errors → Human reviews

Vibe Coding (With DX-61):
Human describes → Agent writes → Guard suggests improvements →
Agent adopts → Human reviews higher quality code
```

**Key Insight:** In vibe coding, the agent is the primary code author. Teaching the agent patterns has multiplicative effect - every project benefits.

---

## Open Questions

1. **Should suggestions be in JSON output for agent parsing?**
   - Probably yes, agents can act on structured suggestions

2. **Should we track suggestion adoption rate?**
   - Could help refine which suggestions are valuable

3. **How to handle conflicting patterns?**
   - e.g., Validation vs Result for simple cases

4. **Should examples be auto-read at session start?**
   - Currently only context.md is emphasized

---

## References

- DX-25: Functional Patterns Enhancement (internal implementation)
- DX-38: Contract Quality Rules (similar tiered approach)
- Haskell ecosystem: Validation, NonEmpty, Monoid patterns
- returns library: Python functional patterns

---

*Proposal created 2025-12-28*
