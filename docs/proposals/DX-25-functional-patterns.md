# DX-25: Functional Patterns Enhancement

> **"Steal from Haskell, adapt for Python"**

## Status

- **ID**: DX-25
- **Status**: Draft
- **Inspiration**: Haskell (Either, Validation, Monoid, NonEmpty, Newtype)
- **Related**: DX-23 (Monad runner pattern)

---

## Problem Statement

Invar has adopted some Haskell patterns (Result monad, Core/Shell separation), but several valuable patterns remain unused:

| Pattern | Haskell | Current Invar | Gap |
|---------|---------|---------------|-----|
| Error accumulation | Validation | Single Result | Loses errors |
| Type safety | Newtype | Raw primitives | Type confusion |
| Non-empty guarantee | NonEmpty | Runtime checks | Defensive code |
| Composable config | Monoid | Manual merging | Boilerplate |
| Monad composition | do-notation | Nested binds | Readability |

**Symptoms:**
1. Validation functions return first error, hiding others
2. `str` used for paths, names, patterns interchangeably
3. Empty list checks scattered everywhere
4. Config merging logic duplicated
5. Long Result chains hard to read

---

## Design Principles

### Python-Native Adaptation

```
Don't: Force Haskell syntax into Python
Do:   Adapt Haskell concepts to Python idioms
```

### Gradual Adoption

```
Don't: Rewrite everything at once
Do:   Introduce patterns where they add value
```

### Type Checker Friendly

```
Don't: Runtime-only safety
Do:   Leverage mypy/pyright for static checks
```

---

## Part 1: Validation Pattern (Error Accumulation)

### Problem

```python
# Current: Stops at first error
def validate_config(data: dict) -> Result[Config, str]:
    if "path" not in data:
        return Failure("Missing path")      # User sees only this
    if "rules" not in data:
        return Failure("Missing rules")     # Never reached
    if "max_lines" in data and data["max_lines"] < 0:
        return Failure("Invalid max_lines") # Never reached
    return Success(Config(...))
```

### Solution

```python
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Validation(Generic[T, E]):
    """Accumulates all errors instead of stopping at first."""

    _value: T | None
    _errors: list[E]

    @classmethod
    def valid(cls, value: T) -> "Validation[T, E]":
        return cls(_value=value, _errors=[])

    @classmethod
    def invalid(cls, *errors: E) -> "Validation[T, E]":
        return cls(_value=None, _errors=list(errors))

    @property
    def is_valid(self) -> bool:
        return len(self._errors) == 0

    @property
    def errors(self) -> list[E]:
        return self._errors

    @property
    def value(self) -> T:
        if not self.is_valid:
            raise ValueError("Cannot get value from invalid Validation")
        return self._value  # type: ignore

    def combine(self, other: "Validation[T, E]") -> "Validation[T, E]":
        """Combine two validations, accumulating errors."""
        if self.is_valid and other.is_valid:
            return other  # Both valid, return latest
        return Validation.invalid(*self._errors, *other._errors)

    def map(self, f: Callable[[T], U]) -> "Validation[U, E]":
        if self.is_valid:
            return Validation.valid(f(self._value))  # type: ignore
        return Validation.invalid(*self._errors)

    def to_result(self) -> Result[T, list[E]]:
        """Convert to Result for compatibility."""
        if self.is_valid:
            return Success(self._value)
        return Failure(self._errors)


# Usage
def validate_config(data: dict) -> Validation[Config, str]:
    """Validate config, accumulating ALL errors."""
    errors: list[str] = []

    path = data.get("path")
    if path is None:
        errors.append("Missing required field: path")

    rules = data.get("rules")
    if rules is None:
        errors.append("Missing required field: rules")

    max_lines = data.get("max_lines", 500)
    if max_lines < 0:
        errors.append(f"Invalid max_lines: {max_lines} (must be >= 0)")

    if errors:
        return Validation.invalid(*errors)

    return Validation.valid(Config(path=path, rules=rules, max_lines=max_lines))


# Result: User sees ALL errors at once
result = validate_config({"max_lines": -1})
# Validation.invalid([
#     "Missing required field: path",
#     "Missing required field: rules",
#     "Invalid max_lines: -1 (must be >= 0)"
# ])
```

### Application in Invar

```python
# src/invar/core/rules.py

def check_all_rules(file_info: FileInfo) -> Validation[None, Violation]:
    """Run all rules, accumulate all violations."""
    validations = [
        check_file_size(file_info),
        check_function_size(file_info),
        check_contracts(file_info),
        check_purity(file_info),
    ]

    result = Validation.valid(None)
    for v in validations:
        result = result.combine(v)

    return result
```

---

## Part 2: NewType (Semantic Type Safety)

### Problem

```python
# All strings - easy to confuse
def find_symbol(
    module_path: str,    # Is this a file path or module path?
    symbol_name: str,    # Is this a full name or pattern?
    file_pattern: str,   # Wait, another string?
) -> Symbol:
    ...

# Easy mistake:
find_symbol(symbol_name, file_pattern, module_path)  # Wrong order, no error!
```

### Solution

```python
from typing import NewType

# Define semantic types
FilePath = NewType('FilePath', str)
ModulePath = NewType('ModulePath', str)
SymbolName = NewType('SymbolName', str)
GlobPattern = NewType('GlobPattern', str)

# Function signature is self-documenting
def find_symbol(
    module: ModulePath,
    name: SymbolName,
) -> Symbol:
    ...

# Type checker warns about wrong usage
path = FilePath("/src/core/parser.py")
module = ModulePath("invar.core.parser")
name = SymbolName("parse_source")

find_symbol(module, name)  # ✓ Correct
find_symbol(path, name)    # ✗ Type error: FilePath != ModulePath
find_symbol(name, module)  # ✗ Type error: wrong order
```

### Proposed NewTypes for Invar

```python
# src/invar/core/types.py

from typing import NewType

# Path types
FilePath = NewType('FilePath', str)          # Absolute file path
RelativePath = NewType('RelativePath', str)  # Relative to project root
ModulePath = NewType('ModulePath', str)      # Python module path (dot notation)

# Name types
SymbolName = NewType('SymbolName', str)      # Function/class name
RuleName = NewType('RuleName', str)          # Rule identifier

# Pattern types
GlobPattern = NewType('GlobPattern', str)    # Glob pattern for file matching
RegexPattern = NewType('RegexPattern', str)  # Regular expression

# Content types
SourceCode = NewType('SourceCode', str)      # Python source code
ContractExpr = NewType('ContractExpr', str)  # Lambda expression in contract
```

### Migration Strategy

```python
# Phase 1: Define types (non-breaking)
# Just add type aliases, existing code still works

# Phase 2: Annotate new code
# New functions use NewType in signatures

# Phase 3: Gradual migration
# Update existing functions as touched

# Phase 4: Enable strict mypy
# --strict flag catches remaining issues
```

---

## Part 3: NonEmpty (Guaranteed Non-Empty Collections)

### Problem

```python
# Defensive code everywhere
def process_violations(violations: list[Violation]) -> Report:
    if not violations:
        return Report.empty()  # Special case

    first = violations[0]  # Safe? Only if we checked above
    ...

# Easy to forget the check
def summarize(items: list[str]) -> str:
    return items[0]  # IndexError if empty!
```

### Solution

```python
from typing import Generic, TypeVar, Iterator
from dataclasses import dataclass

T = TypeVar('T')

@dataclass(frozen=True)
class NonEmpty(Generic[T]):
    """A list guaranteed to have at least one element."""

    head: T
    tail: tuple[T, ...]

    @classmethod
    def of(cls, first: T, *rest: T) -> "NonEmpty[T]":
        """Create NonEmpty from arguments."""
        return cls(head=first, tail=rest)

    @classmethod
    def from_list(cls, items: list[T]) -> Result["NonEmpty[T]", str]:
        """Create from list, failing if empty."""
        if not items:
            return Failure("Cannot create NonEmpty from empty list")
        return Success(cls(head=items[0], tail=tuple(items[1:])))

    def __iter__(self) -> Iterator[T]:
        yield self.head
        yield from self.tail

    def __len__(self) -> int:
        return 1 + len(self.tail)

    def to_list(self) -> list[T]:
        return [self.head, *self.tail]

    def map(self, f: Callable[[T], U]) -> "NonEmpty[U]":
        return NonEmpty(head=f(self.head), tail=tuple(f(x) for x in self.tail))

    @property
    def first(self) -> T:
        """Always safe - guaranteed to exist."""
        return self.head

    @property
    def last(self) -> T:
        """Always safe - guaranteed to exist."""
        return self.tail[-1] if self.tail else self.head


# Usage
def process_violations(violations: NonEmpty[Violation]) -> Report:
    # No need to check - type guarantees non-empty
    first = violations.first  # Always safe
    ...

# Caller must handle empty case
match NonEmpty.from_list(violations):
    case Success(non_empty):
        return process_violations(non_empty)
    case Failure(_):
        return Report.empty()
```

### Application in Invar

```python
# Functions that require non-empty input
def format_violations(violations: NonEmpty[Violation]) -> str:
    """Format violations for display. Requires at least one."""
    ...

def merge_configs(configs: NonEmpty[RuleConfig]) -> RuleConfig:
    """Merge multiple configs. Requires at least one."""
    base = configs.first
    for config in configs.tail:
        base = base.merge(config)
    return base

# Return type communicates guarantee
def get_violations(file: FileInfo) -> NonEmpty[Violation] | None:
    """Returns violations if any, None if clean."""
    violations = run_all_checks(file)
    return NonEmpty.from_list(violations).value_or(None)
```

---

## Part 4: Monoid (Composable Values)

### Problem

```python
# Config merging is ad-hoc
def merge_configs(default: Config, project: Config, cli: Config) -> Config:
    return Config(
        max_lines=cli.max_lines or project.max_lines or default.max_lines,
        excluded=default.excluded + project.excluded + cli.excluded,
        strict=cli.strict if cli.strict is not None else project.strict or default.strict,
        # ... 10 more fields with different merge logic
    )
```

### Solution

```python
from typing import Protocol, TypeVar
from dataclasses import dataclass, field
from abc import abstractmethod

T = TypeVar('T', covariant=True)

class Monoid(Protocol[T]):
    """A type with an identity element and associative combine operation."""

    @classmethod
    @abstractmethod
    def empty(cls) -> T:
        """Identity element: empty.combine(x) == x.combine(empty) == x"""
        ...

    @abstractmethod
    def combine(self, other: T) -> T:
        """Associative: (a.combine(b)).combine(c) == a.combine(b.combine(c))"""
        ...


@dataclass
class RuleConfig:
    """Rule configuration with monoidal combine."""

    max_file_lines: int | None = None
    max_function_lines: int | None = None
    excluded_paths: frozenset[str] = field(default_factory=frozenset)
    excluded_rules: frozenset[str] = field(default_factory=frozenset)
    strict: bool | None = None

    @classmethod
    def empty(cls) -> "RuleConfig":
        """Empty config - identity element."""
        return cls()

    def combine(self, other: "RuleConfig") -> "RuleConfig":
        """
        Combine configs: later values override earlier.
        Sets are unioned, not overridden.

        >>> default = RuleConfig(max_file_lines=500)
        >>> project = RuleConfig(max_file_lines=300, strict=True)
        >>> default.combine(project).max_file_lines
        300
        """
        return RuleConfig(
            max_file_lines=other.max_file_lines or self.max_file_lines,
            max_function_lines=other.max_function_lines or self.max_function_lines,
            excluded_paths=self.excluded_paths | other.excluded_paths,
            excluded_rules=self.excluded_rules | other.excluded_rules,
            strict=other.strict if other.strict is not None else self.strict,
        )


def concat_all(items: list[T]) -> T:
    """Combine all items using monoidal combine."""
    if not items:
        raise ValueError("Need at least one item")
    result = items[0]
    for item in items[1:]:
        result = result.combine(item)
    return result


# Usage: Clean, declarative config merging
final_config = concat_all([
    RuleConfig.empty(),      # Start with identity
    load_default_config(),   # Package defaults
    load_project_config(),   # pyproject.toml
    load_cli_config(),       # Command line args
])
```

### Laws (Verified by Doctests)

```python
@dataclass
class RuleConfig:
    ...

    # Doctest: Identity law
    """
    >>> cfg = RuleConfig(max_file_lines=100)
    >>> cfg.combine(RuleConfig.empty()) == cfg
    True
    >>> RuleConfig.empty().combine(cfg) == cfg
    True
    """

    # Doctest: Associativity law
    """
    >>> a = RuleConfig(max_file_lines=100)
    >>> b = RuleConfig(max_function_lines=50)
    >>> c = RuleConfig(strict=True)
    >>> (a.combine(b)).combine(c) == a.combine(b.combine(c))
    True
    """
```

---

## Part 5: Do-Notation (Readable Result Chains)

### Problem

```python
# Nested binds are hard to read
def process_file(path: Path) -> Result[Report, str]:
    return (
        read_file(path)
        .bind(lambda content:
            parse_source(content)
            .bind(lambda ast:
                extract_symbols(ast)
                .bind(lambda symbols:
                    check_rules(symbols)
                    .map(lambda violations:
                        Report(path, violations)
                    )
                )
            )
        )
    )
```

### Solution (returns library)

```python
from returns.result import Result, Success, Failure
from returns.pointfree import bind
from returns.pipeline import flow

# Option 1: Pipeline style
def process_file(path: Path) -> Result[Report, str]:
    return flow(
        read_file(path),
        bind(parse_source),
        bind(extract_symbols),
        bind(check_rules),
        bind(lambda v: Success(Report(path, v))),
    )

# Option 2: Imperative style with early return
def process_file(path: Path) -> Result[Report, str]:
    content_result = read_file(path)
    if isinstance(content_result, Failure):
        return content_result
    content = content_result.unwrap()

    ast_result = parse_source(content)
    if isinstance(ast_result, Failure):
        return ast_result
    ast = ast_result.unwrap()

    # ... continue pattern
    return Success(Report(path, violations))
```

### Proposed Convention for Invar

```python
# Shell functions use pipeline style for clarity
from returns.pipeline import flow
from returns.pointfree import bind, map_

def load_and_check(path: Path) -> Result[list[Violation], str]:
    """Load file and run all checks."""
    return flow(
        read_file(path),
        bind(parse_source),
        bind(extract_file_info),
        map_(run_all_checks),
    )

# Core functions remain pure, no Result needed
@pre(lambda source: isinstance(source, str))
@post(lambda result: isinstance(result, FileInfo))
def extract_file_info(ast: AST) -> FileInfo:
    """Pure extraction, no failure possible."""
    ...
```

---

## Part 6: Smart Constructors

### Problem

```python
@dataclass
class Symbol:
    name: str
    line: int
    kind: SymbolKind

# Can create invalid symbols
bad = Symbol(name="", line=-1, kind=SymbolKind.FUNCTION)
```

### Solution

```python
@dataclass(frozen=True)
class Symbol:
    """Immutable symbol with guaranteed validity."""

    _name: str
    _line: int
    _kind: SymbolKind

    def __post_init__(self):
        # Validate on construction
        if not self._name:
            raise ValueError("Symbol name cannot be empty")
        if self._line < 1:
            raise ValueError(f"Line must be >= 1, got {self._line}")

    @classmethod
    def create(
        cls,
        name: str,
        line: int,
        kind: SymbolKind,
    ) -> Result["Symbol", str]:
        """Smart constructor: validates before creating."""
        if not name:
            return Failure("Symbol name cannot be empty")
        if line < 1:
            return Failure(f"Line must be >= 1, got {line}")
        return Success(cls(_name=name, _line=line, _kind=kind))

    @property
    def name(self) -> str:
        return self._name

    @property
    def line(self) -> int:
        return self._line

    @property
    def kind(self) -> SymbolKind:
        return self._kind


# Usage
match Symbol.create("foo", 10, SymbolKind.FUNCTION):
    case Success(symbol):
        process(symbol)  # Guaranteed valid
    case Failure(error):
        log_error(error)
```

---

## Implementation Plan

### Phase 1: Foundation Types (0.5 day)

```
□ Create src/invar/core/functional.py
  ├── Validation[T, E] class
  ├── NonEmpty[T] class
  └── Monoid protocol

□ Create src/invar/core/types.py
  ├── FilePath, ModulePath, etc. NewTypes
  └── Type aliases for clarity
```

### Phase 2: Validation Migration (0.5 day)

```
□ Update config validation
  └── Return all errors, not just first

□ Update rule checking
  └── Accumulate violations properly
```

### Phase 3: NewType Adoption (0.5 day)

```
□ Add NewTypes to core models
□ Update function signatures
□ Enable stricter mypy checks
```

### Phase 4: Monoid Config (0.5 day)

```
□ Implement Monoid for RuleConfig
□ Refactor config loading to use combine
□ Add doctest verification of laws
```

### Phase 5: Documentation (0.5 day)

```
□ Add to DX-24 mechanism docs
□ Create examples in .invar/examples/
□ Update INVAR.md with patterns
```

**Total: ~2.5 days**

---

## File Changes

```
src/invar/core/
├── functional.py    # NEW: Validation, NonEmpty, Monoid
├── types.py         # NEW: NewType definitions
├── models.py        # UPDATE: Use NewTypes, smart constructors
├── rules.py         # UPDATE: Use Validation for error accumulation
└── config.py        # UPDATE: Use Monoid for config merging

src/invar/shell/
├── config.py        # UPDATE: Use Monoid pattern
└── fs.py            # UPDATE: Use NewTypes for paths
```

---

## Compatibility

### With Existing Code

- NewTypes are aliases, backward compatible
- Validation converts to Result via `.to_result()`
- NonEmpty converts to list via `.to_list()`
- Gradual adoption, no big bang migration

### With Type Checkers

- All patterns work with mypy --strict
- IDE autocomplete improved
- Error messages clearer

### With returns Library

- Validation complements, doesn't replace Result
- Pipeline patterns align with returns style
- Can use returns' `@do` decorator

---

## Decision Record

| Decision | Choice | Reason |
|----------|--------|--------|
| Validation vs Result | Both | Different use cases |
| NewType vs class wrapper | NewType | Zero runtime cost |
| NonEmpty implementation | Frozen dataclass | Immutability |
| Monoid enforcement | Protocol + doctest | Verify laws |
| Pipeline style | returns library | Already dependency |

---

## Examples

### Before and After: Config Validation

```python
# BEFORE: Single error
def validate(data: dict) -> Result[Config, str]:
    if "path" not in data:
        return Failure("Missing path")
    ...

# AFTER: All errors
def validate(data: dict) -> Validation[Config, str]:
    errors = []
    if "path" not in data:
        errors.append("Missing path")
    if "rules" not in data:
        errors.append("Missing rules")
    if errors:
        return Validation.invalid(*errors)
    return Validation.valid(Config(...))
```

### Before and After: Function Signature

```python
# BEFORE: Confusing strings
def find(path: str, name: str, pattern: str) -> Symbol:
    ...

# AFTER: Self-documenting
def find(path: ModulePath, name: SymbolName) -> Symbol:
    ...
```

### Before and After: Empty Check

```python
# BEFORE: Defensive
def process(items: list[T]) -> T:
    if not items:
        raise ValueError("Empty")
    return items[0]

# AFTER: Type-safe
def process(items: NonEmpty[T]) -> T:
    return items.first  # Always safe
```

---

## References

- Haskell `Data.Validation` - Error accumulation
- Haskell `Data.List.NonEmpty` - Non-empty lists
- Haskell `Data.Monoid` - Composable values
- Python `typing.NewType` - Semantic types
- returns library - Functional patterns for Python

---

*Proposal created 2025-12-24*
