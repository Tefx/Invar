# DX-61: Functional Pattern Guidance for Agents

**Status:** Draft
**Created:** 2025-12-28
**Depends on:** None
**Synergies:** DX-62 (Proactive Reference Reading)
**References:** DX-38 (Contract Quality Rules - tiered approach)
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

## Part 1: Core Patterns (P0)

These 5 rules have the highest detection reliability, impact, and universal applicability.

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

### Rule 4: `suggest_literal_type`

**Detects:** String/int parameters with limited valid values

```python
# Triggers suggestion:
def set_log_level(level: str) -> None:
    if level not in ("debug", "info", "warning", "error"):
        raise ValueError(f"Invalid level: {level}")
    ...

# Suggestion:
SUGGEST: Parameter 'level' has limited valid values
  → Consider Literal type for compile-time safety
  → from typing import Literal
  → LogLevel = Literal["debug", "info", "warning", "error"]
  → def set_log_level(level: LogLevel) -> None:
```

**Implementation:** AST pattern matching on `not in (literal, ...)` or if-elif chains with string equality

### Rule 5: `suggest_exhaustive_match`

**Detects:** Match statements without exhaustive handling

```python
# Triggers suggestion:
class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

def handle(status: Status) -> str:
    match status:
        case Status.PENDING: return "waiting"
        case Status.RUNNING: return "in progress"
        # Missing DONE and FAILED!

# Suggestion:
SUGGEST: Match on Status is not exhaustive
  → Missing cases: DONE, FAILED
  → Add: case _: assert_never(status)
  → from typing import assert_never
```

**Implementation:** Compare Enum member count vs match case count

---

## Part 2: Extended Best Practices (P1/P2)

### Category A: Type Safety Patterns

#### Rule 6: `suggest_smart_constructor`

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

#### Rule 7: `suggest_protocol`

**Detects:** Functions accepting objects and only using specific methods

```python
# Triggers suggestion:
def process(obj: Any) -> str:
    return obj.read() + obj.name

# Suggestion:
SUGGEST: Function uses .read() and .name on 'obj'
  → Consider Protocol for explicit interface
  → class Readable(Protocol):
  →     def read(self) -> str: ...
  →     @property
  →     def name(self) -> str: ...
  → def process(obj: Readable) -> str:
```

#### Rule 8: `suggest_typeguard`

**Detects:** isinstance checks followed by type-specific operations

```python
# Triggers suggestion:
def handle(value: str | int) -> str:
    if isinstance(value, str):
        return value.upper()  # Type narrowing works here
    return str(value)

# Suggestion (for complex cases):
SUGGEST: Complex type narrowing detected
  → Consider TypeGuard for reusable type predicates
  → def is_string_list(val: list) -> TypeGuard[list[str]]:
  →     return all(isinstance(x, str) for x in val)
```

---

### Category B: Error Handling Patterns

#### Rule 9: `suggest_structured_error`

**Detects:** String error messages with embedded data

```python
# Triggers suggestion:
def parse(text: str) -> Result[AST, str]:
    if not text:
        return Failure(f"Parse error at line {line}: unexpected EOF")
    ...

# Suggestion:
SUGGEST: Error message contains structured data (line number)
  → Consider structured error type for programmatic handling
  → @dataclass
  → class ParseError:
  →     message: str
  →     line: int
  →     column: int
  → def parse(text: str) -> Result[AST, ParseError]:
```

#### Rule 10: `suggest_error_context`

**Detects:** Re-raising exceptions without context

```python
# Triggers suggestion:
def load_config(path: str) -> Config:
    try:
        return parse(read_file(path))
    except Exception as e:
        raise e  # Lost context: which file?

# Suggestion:
SUGGEST: Exception re-raised without context
  → Add context for debugging
  → except Exception as e:
  →     raise ConfigError(f"Failed to load {path}") from e
```

---

### Category C: Immutability Patterns

#### Rule 11: `suggest_frozen_dataclass`

**Detects:** Dataclass without frozen=True that isn't mutated

```python
# Triggers suggestion:
@dataclass
class Config:
    path: str
    max_lines: int

# If no mutations detected in codebase:
SUGGEST: Dataclass 'Config' appears immutable
  → Consider frozen=True for safety
  → @dataclass(frozen=True)
  → class Config:
  → Benefits: hashable, thread-safe, prevents accidental mutation
```

#### Rule 12: `suggest_tuple_over_list`

**Detects:** List literals that are never mutated

```python
# Triggers suggestion:
VALID_EXTENSIONS = [".py", ".pyi", ".pyx"]  # Never modified

# Suggestion:
SUGGEST: List 'VALID_EXTENSIONS' is never mutated
  → Consider tuple for immutability
  → VALID_EXTENSIONS = (".py", ".pyi", ".pyx")
  → Benefits: immutable, slightly faster, clearer intent
```

---

### Category D: Function Design Patterns

#### Rule 13: `suggest_total_function`

**Detects:** Functions that raise exceptions for some inputs

```python
# Triggers suggestion:
def divide(a: int, b: int) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Suggestion:
SUGGEST: Function 'divide' raises for some inputs
  → Consider total function with Result
  → def divide(a: int, b: int) -> Result[float, str]:
  →     if b == 0:
  →         return Failure("Cannot divide by zero")
  →     return Success(a / b)
  → Benefits: Caller forced to handle error case
```

#### Rule 14: `suggest_dependency_injection`

**Detects:** Functions creating their own dependencies

```python
# Triggers suggestion:
def process_file(path: str) -> Result[Report, str]:
    content = open(path).read()  # Creates dependency internally
    return analyze(content)

# Suggestion:
SUGGEST: Function creates I/O dependency internally
  → Consider dependency injection for testability
  → def process_file(path: str, reader: Callable[[str], str] = open_and_read) -> Result[Report, str]:
  →     content = reader(path)
  →     return analyze(content)
  → Benefits: Easy to test with mock reader
```

#### Rule 15: `suggest_early_return`

**Detects:** Deeply nested conditionals

```python
# Triggers suggestion:
def process(data: dict) -> Result[Output, str]:
    if "key1" in data:
        if data["key1"] > 0:
            if "key2" in data:
                # Deep nesting
                return Success(compute(data))
    return Failure("invalid")

# Suggestion:
SUGGEST: Deep nesting detected (3+ levels)
  → Consider early returns for readability
  → def process(data: dict) -> Result[Output, str]:
  →     if "key1" not in data:
  →         return Failure("missing key1")
  →     if data["key1"] <= 0:
  →         return Failure("key1 must be positive")
  →     if "key2" not in data:
  →         return Failure("missing key2")
  →     return Success(compute(data))
```

---

### Category E: API Design Patterns

#### Rule 16: `suggest_parse_dont_validate`

**Detects:** Validation that discards information

```python
# Triggers suggestion:
def is_valid_email(s: str) -> bool:
    return "@" in s and "." in s.split("@")[1]

def send_email(to: str) -> None:
    if not is_valid_email(to):
        raise ValueError("Invalid email")
    # to is still just str, not Email

# Suggestion:
SUGGEST: Validation discards type information
  → Consider parsing to preserve validated state
  → @dataclass(frozen=True)
  → class Email:
  →     _value: str
  →     @classmethod
  →     def parse(cls, s: str) -> Result[Email, str]:
  →         if "@" not in s: return Failure("missing @")
  →         return Success(cls(s))
  → def send_email(to: Email) -> None:  # Guaranteed valid
```

#### Rule 17: `suggest_builder_pattern`

**Detects:** Functions with many optional parameters

```python
# Triggers suggestion:
def create_request(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: str | None = None,
    timeout: int = 30,
    retries: int = 3,
    auth: tuple | None = None,
) -> Request:
    ...

# Suggestion:
SUGGEST: Function has 5+ optional parameters
  → Consider builder pattern for clarity
  → request = Request.builder(url) \
  →     .method("POST") \
  →     .header("Content-Type", "application/json") \
  →     .body(data) \
  →     .timeout(60) \
  →     .build()
```

---

### Category F: Defensive Programming

#### Rule 18: `suggest_assert_invariant`

**Detects:** Implicit assumptions in code

```python
# Triggers suggestion:
def binary_search(arr: list[int], target: int) -> int:
    # Assumes arr is sorted, but doesn't verify
    left, right = 0, len(arr) - 1
    ...

# Suggestion:
SUGGEST: Function assumes sorted input without verification
  → Consider assertion for invariant
  → def binary_search(arr: list[int], target: int) -> int:
  →     assert arr == sorted(arr), "binary_search requires sorted input"
  → Or use type: SortedList[int]
```

#### Rule 19: `suggest_explicit_none_handling`

**Detects:** Optional parameters used without None check

```python
# Triggers suggestion:
def greet(name: str | None = None) -> str:
    return f"Hello, {name.upper()}"  # Crashes if name is None

# Suggestion:
SUGGEST: Optional 'name' used without None check
  → Handle None explicitly
  → def greet(name: str | None = None) -> str:
  →     if name is None:
  →         return "Hello, stranger"
  →     return f"Hello, {name.upper()}"
```

---

### Category G: Performance Patterns

#### Rule 20: `suggest_generator`

**Detects:** Functions building large lists that are iterated once

```python
# Triggers suggestion:
def get_all_lines(files: list[Path]) -> list[str]:
    result = []
    for f in files:
        result.extend(f.read_text().splitlines())
    return result  # Could be huge

# Usage:
for line in get_all_lines(files):
    process(line)

# Suggestion:
SUGGEST: Large list built and iterated once
  → Consider generator for memory efficiency
  → def get_all_lines(files: list[Path]) -> Iterator[str]:
  →     for f in files:
  →         yield from f.read_text().splitlines()
```

#### Rule 21: `suggest_early_exit`

**Detects:** Loops that could exit early

```python
# Triggers suggestion:
def has_error(items: list[Item]) -> bool:
    errors = [item for item in items if item.is_error]
    return len(errors) > 0  # Builds full list

# Suggestion:
SUGGEST: Loop builds list but only checks existence
  → Consider early exit with any()
  → def has_error(items: list[Item]) -> bool:
  →     return any(item.is_error for item in items)
  → Benefits: Stops at first match
```

---

### Category H: Code Organization

#### Rule 22: `suggest_extract_function`

**Detects:** Long functions with distinct logical sections

```python
# Triggers suggestion:
def process(data: dict) -> Report:
    # Section 1: Validation (15 lines)
    if "a" not in data: ...
    if "b" not in data: ...
    ...

    # Section 2: Transformation (20 lines)
    result = {}
    for key in data: ...
    ...

    # Section 3: Formatting (15 lines)
    output = ""
    for item in result: ...
    ...

    return Report(output)

# Suggestion:
SUGGEST: Function 'process' has 3 distinct sections (50+ lines)
  → Consider extracting into smaller functions
  → def process(data: dict) -> Report:
  →     validated = validate_data(data)
  →     transformed = transform_data(validated)
  →     return format_report(transformed)
```

#### Rule 23: `suggest_enum_over_strings`

**Detects:** String comparisons with fixed set of values

```python
# Triggers suggestion:
def get_color(status: str) -> str:
    if status == "success":
        return "green"
    elif status == "warning":
        return "yellow"
    elif status == "error":
        return "red"

# Suggestion:
SUGGEST: String comparison with fixed values
  → Consider Enum for type safety
  → class Status(Enum):
  →     SUCCESS = "success"
  →     WARNING = "warning"
  →     ERROR = "error"
  → def get_color(status: Status) -> str:
  →     match status:
  →         case Status.SUCCESS: return "green"
```

---

### Category I: Documentation Patterns

#### Rule 24: `suggest_docstring_examples`

**Detects:** Public functions without doctest examples

```python
# Triggers suggestion:
def calculate_discount(price: float, percent: float) -> float:
    """Apply percentage discount to price."""
    return price * (1 - percent / 100)

# Suggestion:
SUGGEST: Public function without doctest examples
  → Add examples for documentation and testing
  → def calculate_discount(price: float, percent: float) -> float:
  →     """
  →     Apply percentage discount to price.
  →
  →     >>> calculate_discount(100.0, 20)
  →     80.0
  →     >>> calculate_discount(50.0, 10)
  →     45.0
  →     """
```

#### Rule 25: `suggest_type_narrowing_comment`

**Detects:** Type assertions without explanation

```python
# Triggers suggestion:
def process(value: str | int | None) -> str:
    assert value is not None  # Why can we assert this?
    ...

# Suggestion:
SUGGEST: Type assertion without explanation
  → Add comment explaining invariant
  → # value is guaranteed non-None because caller validates
  → assert value is not None
```

---

## Pattern Priority Matrix

| Rule | Pattern | Detectability | Impact | False Positive Risk | Priority |
|------|---------|--------------|--------|---------------------|----------|
| 1 | NewType | High | High | Low | **P0** |
| 2 | Validation | High | High | Low | **P0** |
| 3 | NonEmpty | High | Medium | Low | **P0** |
| 4 | Literal Type | High | High | Low | **P0** |
| 5 | Exhaustive Match | High | High | Low | **P0** |
| 6 | Smart Constructor | Medium | High | Medium | P1 |
| 9 | Structured Error | Medium | High | Medium | P1 |
| 11 | Frozen Dataclass | High | Medium | Low | P1 |
| 13 | Total Function | Medium | High | Medium | P1 |
| 15 | Early Return | High | Medium | Low | P2 |
| 20 | Generator | Medium | Medium | Medium | P2 |
| 22 | Extract Function | Medium | High | High | P2 |
| 24 | Docstring Examples | High | Medium | Low | P2 |

**Implementation Order:** P0 (5 rules) → P1 (4 rules) → P2 (remaining)

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

Part 1 - Core Patterns (P0):
  1. NewType         - Semantic clarity for primitive types
  2. Validation      - Error accumulation instead of fail-fast
  3. NonEmpty        - Compile-time safety for non-empty collections
  4. Literal         - Type-safe finite value sets
  5. ExhaustiveMatch - Catch missing cases at compile time
"""

from typing import NewType, Literal, assert_never
from enum import Enum
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
# Pattern 4: Literal for Finite Value Sets
# =============================================================================

# BEFORE: Runtime error for invalid values
def set_level_bad(level: str) -> None:
    if level not in ("debug", "info", "warning", "error"):
        raise ValueError(f"Invalid level: {level}")
    ...

# AFTER: Compile-time error for invalid values
LogLevel = Literal["debug", "info", "warning", "error"]

def set_level_good(level: LogLevel) -> None:
    ...  # Type checker catches invalid values


# =============================================================================
# Pattern 5: Exhaustive Match
# =============================================================================

class Status(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

# BEFORE: Missing cases silently ignored
def handle_bad(status: Status) -> str:
    match status:
        case Status.PENDING: return "waiting"
        case Status.RUNNING: return "in progress"
        # DONE and FAILED silently fall through!
    return "unknown"

# AFTER: Compiler catches missing cases
def handle_good(status: Status) -> str:
    match status:
        case Status.PENDING: return "waiting"
        case Status.RUNNING: return "in progress"
        case Status.DONE: return "completed"
        case Status.FAILED: return "error"
        case _: assert_never(status)  # Catches future enum additions


# =============================================================================
# Pattern 6: Smart Constructors (P1)
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

### Phase 1: Examples (1 day)
```
□ Create .invar/examples/functional.py
  ├── Type safety patterns (NewType, Literal, Protocol)
  ├── Error handling patterns (Validation, exhaustive match)
  ├── Immutability patterns (frozen dataclass, tuple)
  └── Function design patterns (total functions, early return)
□ Document each pattern with before/after
□ Agent learns from examples immediately
```

### Phase 2: Core Suggestions - P0 (2 days)
```
□ Add SUGGEST severity level to Guard
□ Implement Rule 1: suggest_newtype
□ Implement Rule 2: suggest_validation
□ Implement Rule 3: suggest_nonempty
□ Implement Rule 4: suggest_literal_type
□ Implement Rule 5: suggest_exhaustive_match
□ Output format: non-blocking, educational
□ JSON output for agent consumption
```

### Phase 3: Extended Suggestions - P1 (2 days)
```
□ Implement Rule 6: suggest_smart_constructor
□ Implement Rule 9: suggest_structured_error
□ Implement Rule 11: suggest_frozen_dataclass
□ Implement Rule 13: suggest_total_function
```

### Phase 4: Config & Polish (1 day)
```
□ Add [guard.suggestions] to config
  ├── enabled = true/false
  ├── max_per_file = 3
  ├── categories = ["type_safety", "error_handling", ...]
  └── thresholds for each rule
□ Allow per-project opt-in/out
□ Dismissable suggestions (don't repeat)
```

### Phase 5: Documentation (1 day)
```
□ Update INVAR.md with Tier 2 guidance
□ Add suggestion categories to context.md
□ Create "Pattern Adoption Guide"
□ Measure baseline for success metrics
```

**Total: ~7 days (phased rollout)**

### Rollout Strategy

```
Week 1: Phase 1 (Examples only)
  → Agents learn from examples, no code changes needed

Week 2: Phase 2 (P0 suggestions)
  → 5 core patterns, maximum impact

Week 3: Phase 3 (P1 suggestions)
  → Extended patterns, refine based on feedback

Week 4: Phase 4-5 (Config & Docs)
  → Polish, configuration, documentation
```

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
