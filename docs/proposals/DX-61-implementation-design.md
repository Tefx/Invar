# DX-61: Implementation Design Specification

**Parent:** DX-61-functional-pattern-guidance.md
**Status:** Draft
**Created:** 2025-12-28
**Depends on:** None
**Synergies:** DX-62 (Proactive Reference Reading)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Guard Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Source Files                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │   Static    │   │  Doctest    │   │ CrossHair   │           │
│  │  Analysis   │   │   Runner    │   │  Symbolic   │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│       │                   │                 │                   │
│       ▼                   ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────┐           │
│  │              Result Aggregator                   │           │
│  │  ├── ERROR   (blocks)                           │           │
│  │  ├── WARNING (reports)                          │           │
│  │  └── SUGGEST (guides)  ◀── NEW                  │           │
│  └─────────────────────────────────────────────────┘           │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────┐           │
│  │              Pattern Analyzer  ◀── NEW           │           │
│  │  ├── AST Pattern Matching                       │           │
│  │  ├── Type Flow Analysis                         │           │
│  │  └── Control Flow Analysis                      │           │
│  └─────────────────────────────────────────────────┘           │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────────────────────────────────────┐           │
│  │              Output Formatter                    │           │
│  │  ├── Human (terminal)                           │           │
│  │  └── JSON (agent consumption)  ◀── NEW          │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Structure

```
src/invar/
├── core/
│   └── patterns/                    # NEW: Pattern detection (pure)
│       ├── __init__.py
│       ├── types.py                 # Pattern result types
│       ├── detector.py              # Base detector protocol
│       ├── p0_newtype.py            # Rule 1: NewType suggestion
│       ├── p0_validation.py         # Rule 2: Validation pattern
│       ├── p0_nonempty.py           # Rule 3: NonEmpty suggestion
│       ├── p0_literal.py            # Rule 4: Literal type
│       ├── p0_exhaustive.py         # Rule 5: Exhaustive match
│       └── registry.py              # Pattern registry
│
└── shell/
    └── commands/
        └── guard.py                 # Integrate pattern analysis
```

---

## 3. Core Types

```python
# src/invar/core/patterns/types.py

from dataclasses import dataclass
from enum import Enum
from typing import NewType, Literal

# ============================================================================
# Severity Levels
# ============================================================================

class Severity(Enum):
    """Guard output severity levels."""
    ERROR = "error"      # Must fix, blocks CI
    WARNING = "warning"  # Should fix, reported
    SUGGEST = "suggest"  # Could improve, educational

# ============================================================================
# Pattern Categories
# ============================================================================

PatternCategory = Literal[
    "type_safety",       # NewType, Literal, Protocol
    "error_handling",    # Validation, structured errors
    "immutability",      # frozen dataclass, tuple
    "function_design",   # total functions, early return
    "api_design",        # parse don't validate, builder
    "defensive",         # assertions, None handling
    "performance",       # generators, early exit
    "organization",      # extract function, enum over strings
    "documentation",     # doctests, comments
]

PatternPriority = Literal["P0", "P1", "P2"]

# ============================================================================
# Detection Result
# ============================================================================

@dataclass(frozen=True)
class PatternLocation:
    """Where a pattern was detected."""
    file: str
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

@dataclass(frozen=True)
class PatternSuggestion:
    """A suggestion for pattern improvement."""

    # Identification
    rule_id: str                    # e.g., "suggest_newtype"
    category: PatternCategory
    priority: PatternPriority

    # Location
    location: PatternLocation
    symbol_name: str | None         # e.g., "find_symbol"

    # Content
    title: str                      # One-line summary
    description: str                # Why this matters
    before_code: str | None         # Current code snippet
    after_code: str | None          # Suggested improvement

    # Metadata
    confidence: float               # 0.0-1.0, filter threshold
    reference_file: str | None      # e.g., ".invar/examples/functional.py"
    reference_lines: tuple[int, int] | None  # Line range in reference

    # Suppression
    suppress_key: str               # Unique key for dismissing


@dataclass(frozen=True)
class PatternAnalysisResult:
    """Complete result of pattern analysis."""
    suggestions: tuple[PatternSuggestion, ...]
    files_analyzed: int
    patterns_checked: int
    analysis_time_ms: int
```

---

## 4. Detector Protocol

```python
# src/invar/core/patterns/detector.py

from abc import ABC, abstractmethod
from typing import Protocol, Iterator
import ast

from invar_runtime import pre, post
from .types import PatternSuggestion, PatternCategory, PatternPriority


class PatternDetector(Protocol):
    """Protocol for pattern detectors."""

    @property
    def rule_id(self) -> str:
        """Unique identifier for this rule."""
        ...

    @property
    def category(self) -> PatternCategory:
        """Category this rule belongs to."""
        ...

    @property
    def priority(self) -> PatternPriority:
        """Implementation priority (P0/P1/P2)."""
        ...

    @property
    def reference_file(self) -> str | None:
        """Path to example file showing this pattern."""
        ...

    @property
    def reference_lines(self) -> tuple[int, int] | None:
        """Line range in reference file."""
        ...

    def detect(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """
        Detect pattern opportunities in AST.

        @pre: tree is valid Python AST
        @post: all returned suggestions have confidence >= 0.5
        """
        ...


class BaseDetector(ABC):
    """Base class for pattern detectors with common utilities."""

    @abstractmethod
    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Implementation of detection logic."""
        ...

    def detect(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Detect with confidence filtering."""
        for suggestion in self._detect_impl(tree, source, file_path):
            if suggestion.confidence >= self._min_confidence:
                yield suggestion

    @property
    def _min_confidence(self) -> float:
        """Minimum confidence to report. Override in subclass."""
        return 0.5

    def _make_location(
        self,
        node: ast.AST,
        file_path: str
    ) -> PatternLocation:
        """Create location from AST node."""
        return PatternLocation(
            file=file_path,
            line=node.lineno,
            column=node.col_offset,
            end_line=getattr(node, 'end_lineno', None),
            end_column=getattr(node, 'end_col_offset', None),
        )

    def _get_source_segment(
        self,
        source: str,
        node: ast.AST
    ) -> str:
        """Extract source code for AST node."""
        lines = source.splitlines()
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', node.lineno)
        return '\n'.join(lines[start_line:end_line])
```

---

## 5. P0 Rule Implementations

### Rule 1: suggest_newtype

```python
# src/invar/core/patterns/p0_newtype.py

import ast
from collections import Counter
from typing import Iterator

from .detector import BaseDetector
from .types import PatternSuggestion, PatternLocation


class NewTypeDetector(BaseDetector):
    """
    Detects functions with 3+ parameters of the same primitive type.

    Rationale: Multiple string/int parameters are easy to confuse.
    NewType provides semantic clarity at zero runtime cost.

    Example trigger:
        def find(path: str, name: str, pattern: str) -> Symbol

    Suggestion:
        FilePath = NewType('FilePath', str)
        SymbolName = NewType('SymbolName', str)
        def find(path: FilePath, name: SymbolName, ...) -> Symbol
    """

    rule_id = "suggest_newtype"
    category = "type_safety"
    priority = "P0"
    reference_file = ".invar/examples/functional.py"
    reference_lines = (15, 30)

    # Configuration
    THRESHOLD = 3  # Minimum same-type params to trigger
    PRIMITIVE_TYPES = {"str", "int", "float", "bool", "bytes"}

    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Find functions with many same-type primitive parameters."""

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Skip private/dunder methods
            if node.name.startswith('_'):
                continue

            # Count parameter types
            type_counts = self._count_param_types(node)

            # Find primitives exceeding threshold
            for type_name, count in type_counts.items():
                if type_name in self.PRIMITIVE_TYPES and count >= self.THRESHOLD:
                    yield self._make_suggestion(
                        node, type_name, count, source, file_path
                    )

    def _count_param_types(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Counter[str]:
        """Count occurrences of each parameter type."""
        counts: Counter[str] = Counter()

        for arg in func.args.args + func.args.posonlyargs + func.args.kwonlyargs:
            if arg.annotation:
                type_name = self._extract_type_name(arg.annotation)
                if type_name:
                    counts[type_name] += 1

        return counts

    def _extract_type_name(self, annotation: ast.expr) -> str | None:
        """Extract simple type name from annotation."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            return annotation.value
        return None

    def _make_suggestion(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        type_name: str,
        count: int,
        source: str,
        file_path: str,
    ) -> PatternSuggestion:
        """Create suggestion for NewType usage."""

        # Extract param names with this type
        param_names = [
            arg.arg for arg in func.args.args
            if arg.annotation and self._extract_type_name(arg.annotation) == type_name
        ]

        # Generate suggested NewType names
        suggested_types = [
            f"{name.title().replace('_', '')}Type"
            for name in param_names[:3]
        ]

        return PatternSuggestion(
            rule_id=self.rule_id,
            category=self.category,
            priority=self.priority,
            location=self._make_location(func, file_path),
            symbol_name=func.name,
            title=f"{count} {type_name} parameters in '{func.name}'",
            description=(
                f"Function has {count} parameters of type '{type_name}'. "
                f"Consider using NewType for semantic clarity and type safety."
            ),
            before_code=self._get_source_segment(source, func).split('\n')[0],
            after_code=self._generate_after_code(type_name, suggested_types),
            confidence=self._calculate_confidence(count),
            reference_file=self.reference_file,
            reference_lines=self.reference_lines,
            suppress_key=f"{file_path}:{func.name}:newtype:{type_name}",
        )

    def _generate_after_code(
        self,
        base_type: str,
        suggested_types: list[str]
    ) -> str:
        """Generate example NewType definitions."""
        lines = ["from typing import NewType", ""]
        for name in suggested_types:
            lines.append(f"{name} = NewType('{name}', {base_type})")
        return '\n'.join(lines)

    def _calculate_confidence(self, count: int) -> float:
        """Higher count = higher confidence."""
        if count >= 5:
            return 0.95
        if count >= 4:
            return 0.85
        if count >= 3:
            return 0.70
        return 0.50
```

### Rule 2: suggest_validation

```python
# src/invar/core/patterns/p0_validation.py

import ast
from typing import Iterator

from .detector import BaseDetector
from .types import PatternSuggestion


class ValidationPatternDetector(BaseDetector):
    """
    Detects sequential if-return-Failure pattern (fail-fast validation).

    Rationale: Users prefer seeing all errors at once, not one at a time.
    Validation pattern accumulates errors before returning.

    Example trigger:
        if "a" not in data:
            return Failure("missing a")
        if "b" not in data:
            return Failure("missing b")  # Never reached if "a" missing

    Suggestion:
        errors = []
        if "a" not in data:
            errors.append("missing a")
        if "b" not in data:
            errors.append("missing b")
        if errors:
            return Failure(errors)
    """

    rule_id = "suggest_validation"
    category = "error_handling"
    priority = "P0"
    reference_file = ".invar/examples/functional.py"
    reference_lines = (45, 70)

    # Configuration
    MIN_CONSECUTIVE_CHECKS = 2  # Minimum sequential if-Failure to trigger

    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Find sequential if-Failure patterns."""

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Skip functions not returning Result
            if not self._returns_result(node):
                continue

            # Find consecutive if-Failure sequences
            sequences = self._find_failure_sequences(node.body)

            for start_idx, length in sequences:
                if length >= self.MIN_CONSECUTIVE_CHECKS:
                    yield self._make_suggestion(
                        node, start_idx, length, source, file_path
                    )

    def _returns_result(self, func: ast.FunctionDef) -> bool:
        """Check if function has Result return type annotation."""
        if func.returns is None:
            return False

        return_str = ast.unparse(func.returns)
        return "Result" in return_str

    def _find_failure_sequences(
        self,
        body: list[ast.stmt]
    ) -> list[tuple[int, int]]:
        """Find consecutive if statements that return Failure."""
        sequences = []
        current_start = None
        current_length = 0

        for i, stmt in enumerate(body):
            if self._is_failure_check(stmt):
                if current_start is None:
                    current_start = i
                    current_length = 1
                else:
                    current_length += 1
            else:
                if current_start is not None and current_length >= 2:
                    sequences.append((current_start, current_length))
                current_start = None
                current_length = 0

        # Don't forget last sequence
        if current_start is not None and current_length >= 2:
            sequences.append((current_start, current_length))

        return sequences

    def _is_failure_check(self, stmt: ast.stmt) -> bool:
        """Check if statement is: if <cond>: return Failure(...)"""
        if not isinstance(stmt, ast.If):
            return False

        # Check body has single return
        if len(stmt.body) != 1:
            return False

        ret = stmt.body[0]
        if not isinstance(ret, ast.Return):
            return False

        # Check return value is Failure(...)
        if ret.value is None:
            return False

        if isinstance(ret.value, ast.Call):
            if isinstance(ret.value.func, ast.Name):
                return ret.value.func.id == "Failure"

        return False

    def _make_suggestion(
        self,
        func: ast.FunctionDef,
        start_idx: int,
        length: int,
        source: str,
        file_path: str,
    ) -> PatternSuggestion:
        """Create suggestion for Validation pattern."""

        return PatternSuggestion(
            rule_id=self.rule_id,
            category=self.category,
            priority=self.priority,
            location=self._make_location(func.body[start_idx], file_path),
            symbol_name=func.name,
            title=f"Sequential validation in '{func.name}' returns first error only",
            description=(
                f"Found {length} consecutive validation checks that return immediately on failure. "
                f"Users will only see the first error. Consider accumulating all errors "
                f"using the Validation pattern for better UX."
            ),
            before_code=None,  # Too complex to extract cleanly
            after_code=self._generate_after_code(),
            confidence=self._calculate_confidence(length),
            reference_file=self.reference_file,
            reference_lines=self.reference_lines,
            suppress_key=f"{file_path}:{func.name}:validation",
        )

    def _generate_after_code(self) -> str:
        """Generate example Validation pattern."""
        return '''errors: list[str] = []
if condition1:
    errors.append("error 1")
if condition2:
    errors.append("error 2")
if errors:
    return Failure(errors)
return Success(result)'''

    def _calculate_confidence(self, length: int) -> float:
        """More checks = higher confidence it's a pattern."""
        if length >= 5:
            return 0.95
        if length >= 4:
            return 0.85
        if length >= 3:
            return 0.75
        return 0.60
```

### Rule 3: suggest_nonempty

```python
# src/invar/core/patterns/p0_nonempty.py

import ast
from typing import Iterator

from .detector import BaseDetector
from .types import PatternSuggestion


class NonEmptyDetector(BaseDetector):
    """
    Detects defensive empty checks followed by index access.

    Rationale: If you check for empty and then access [0],
    the type system could guarantee non-emptiness instead.

    Example trigger:
        if not items:
            raise ValueError("empty")
        return items[0]

    Suggestion:
        def process(items: NonEmpty[str]) -> str:
            return items.first  # Always safe
    """

    rule_id = "suggest_nonempty"
    category = "type_safety"
    priority = "P0"
    reference_file = ".invar/examples/functional.py"
    reference_lines = (80, 100)

    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Find empty checks followed by index access."""

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Look for pattern: if not x: raise/return; x[0]
            findings = self._find_empty_check_pattern(node.body)

            for var_name, check_line, access_line in findings:
                yield self._make_suggestion(
                    node, var_name, check_line, access_line, file_path
                )

    def _find_empty_check_pattern(
        self,
        body: list[ast.stmt]
    ) -> list[tuple[str, int, int]]:
        """Find variables that are empty-checked then indexed."""
        findings = []
        empty_checked_vars: dict[str, int] = {}  # var_name -> line

        for stmt in body:
            # Check for: if not x: raise/return
            if isinstance(stmt, ast.If):
                var_name = self._extract_empty_check_var(stmt)
                if var_name:
                    empty_checked_vars[var_name] = stmt.lineno

            # Check for: x[0] or x[n] access
            for node in ast.walk(stmt):
                if isinstance(node, ast.Subscript):
                    var_name = self._extract_subscript_var(node)
                    if var_name and var_name in empty_checked_vars:
                        findings.append((
                            var_name,
                            empty_checked_vars[var_name],
                            node.lineno
                        ))

        return findings

    def _extract_empty_check_var(self, if_stmt: ast.If) -> str | None:
        """Extract variable from 'if not x:' pattern."""
        # Pattern: if not x:
        if isinstance(if_stmt.test, ast.UnaryOp):
            if isinstance(if_stmt.test.op, ast.Not):
                if isinstance(if_stmt.test.operand, ast.Name):
                    # Check body is raise or return
                    if if_stmt.body and isinstance(if_stmt.body[0], (ast.Raise, ast.Return)):
                        return if_stmt.test.operand.id

        # Pattern: if len(x) == 0:
        if isinstance(if_stmt.test, ast.Compare):
            if isinstance(if_stmt.test.left, ast.Call):
                if isinstance(if_stmt.test.left.func, ast.Name):
                    if if_stmt.test.left.func.id == "len":
                        if if_stmt.test.left.args:
                            arg = if_stmt.test.left.args[0]
                            if isinstance(arg, ast.Name):
                                return arg.id

        return None

    def _extract_subscript_var(self, subscript: ast.Subscript) -> str | None:
        """Extract variable from x[...] access."""
        if isinstance(subscript.value, ast.Name):
            # Check if index is 0 or a simple integer
            if isinstance(subscript.slice, ast.Constant):
                if isinstance(subscript.slice.value, int):
                    return subscript.value.id
        return None

    def _make_suggestion(
        self,
        func: ast.FunctionDef,
        var_name: str,
        check_line: int,
        access_line: int,
        file_path: str,
    ) -> PatternSuggestion:
        """Create suggestion for NonEmpty usage."""

        return PatternSuggestion(
            rule_id=self.rule_id,
            category=self.category,
            priority=self.priority,
            location=PatternLocation(file=file_path, line=check_line, column=0),
            symbol_name=func.name,
            title=f"Defensive empty check for '{var_name}' in '{func.name}'",
            description=(
                f"Variable '{var_name}' is checked for emptiness at line {check_line} "
                f"and then indexed at line {access_line}. Consider using NonEmpty[T] type "
                f"for compile-time safety instead of runtime checks."
            ),
            before_code=f"if not {var_name}:\n    raise ValueError('empty')\nreturn {var_name}[0]",
            after_code=f"def {func.name}({var_name}: NonEmpty[T]) -> T:\n    return {var_name}.first  # Always safe",
            confidence=0.80,
            reference_file=self.reference_file,
            reference_lines=self.reference_lines,
            suppress_key=f"{file_path}:{func.name}:nonempty:{var_name}",
        )
```

### Rule 4: suggest_literal_type

```python
# src/invar/core/patterns/p0_literal.py

import ast
from typing import Iterator

from .detector import BaseDetector
from .types import PatternSuggestion


class LiteralTypeDetector(BaseDetector):
    """
    Detects parameters validated against finite value sets.

    Rationale: If a parameter can only be one of N values,
    Literal[...] catches invalid values at type-check time.

    Example trigger:
        def set_level(level: str) -> None:
            if level not in ("debug", "info", "warning"):
                raise ValueError(...)

    Suggestion:
        LogLevel = Literal["debug", "info", "warning"]
        def set_level(level: LogLevel) -> None:
    """

    rule_id = "suggest_literal_type"
    category = "type_safety"
    priority = "P0"
    reference_file = ".invar/examples/functional.py"
    reference_lines = (105, 125)

    MAX_LITERAL_VALUES = 10  # Don't suggest for very large sets

    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Find parameters validated against literal sets."""

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Find: if x not in (literal, ...) patterns
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.If):
                    result = self._extract_literal_check(stmt, node)
                    if result:
                        param_name, values = result
                        yield self._make_suggestion(
                            node, param_name, values, file_path
                        )

    def _extract_literal_check(
        self,
        if_stmt: ast.If,
        func: ast.FunctionDef
    ) -> tuple[str, tuple[str, ...]] | None:
        """Extract param name and literal values from validation check."""

        # Pattern: if x not in (...):
        if not isinstance(if_stmt.test, ast.Compare):
            return None

        compare = if_stmt.test
        if len(compare.ops) != 1:
            return None

        if not isinstance(compare.ops[0], ast.NotIn):
            return None

        # Left side should be a parameter name
        if not isinstance(compare.left, ast.Name):
            return None

        param_name = compare.left.id

        # Check it's actually a function parameter
        param_names = [arg.arg for arg in func.args.args]
        if param_name not in param_names:
            return None

        # Right side should be tuple/list of literals
        if len(compare.comparators) != 1:
            return None

        container = compare.comparators[0]
        values = self._extract_literal_values(container)

        if values and len(values) <= self.MAX_LITERAL_VALUES:
            return (param_name, values)

        return None

    def _extract_literal_values(
        self,
        node: ast.expr
    ) -> tuple[str, ...] | None:
        """Extract string/int literals from tuple/list."""
        if isinstance(node, (ast.Tuple, ast.List)):
            values = []
            for elt in node.elts:
                if isinstance(elt, ast.Constant):
                    if isinstance(elt.value, (str, int)):
                        values.append(repr(elt.value))
                    else:
                        return None  # Non-string/int literal
                else:
                    return None  # Non-constant element
            return tuple(values)
        return None

    def _make_suggestion(
        self,
        func: ast.FunctionDef,
        param_name: str,
        values: tuple[str, ...],
        file_path: str,
    ) -> PatternSuggestion:
        """Create suggestion for Literal type."""

        literal_type = f"Literal[{', '.join(values)}]"
        type_alias = f"{param_name.title().replace('_', '')}Type"

        return PatternSuggestion(
            rule_id=self.rule_id,
            category=self.category,
            priority=self.priority,
            location=self._make_location(func, file_path),
            symbol_name=func.name,
            title=f"Parameter '{param_name}' has {len(values)} valid values",
            description=(
                f"Parameter '{param_name}' is validated against a fixed set of values. "
                f"Using Literal type catches invalid values at type-check time."
            ),
            before_code=f"def {func.name}({param_name}: str) -> ...:",
            after_code=f"{type_alias} = {literal_type}\ndef {func.name}({param_name}: {type_alias}) -> ...:",
            confidence=0.90,
            reference_file=self.reference_file,
            reference_lines=self.reference_lines,
            suppress_key=f"{file_path}:{func.name}:literal:{param_name}",
        )
```

### Rule 5: suggest_exhaustive_match

```python
# src/invar/core/patterns/p0_exhaustive.py

import ast
from typing import Iterator

from .detector import BaseDetector
from .types import PatternSuggestion


class ExhaustiveMatchDetector(BaseDetector):
    """
    Detects match statements on Enums without exhaustive handling.

    Rationale: Missing enum cases fail silently.
    assert_never catches missing cases at type-check time.

    Example trigger:
        class Status(Enum):
            A, B, C, D = ...
        match status:
            case Status.A: ...
            case Status.B: ...
            # Missing C and D!

    Suggestion:
        match status:
            case Status.A: ...
            case Status.B: ...
            case Status.C: ...
            case Status.D: ...
            case _: assert_never(status)
    """

    rule_id = "suggest_exhaustive_match"
    category = "type_safety"
    priority = "P0"
    reference_file = ".invar/examples/functional.py"
    reference_lines = (130, 155)

    def _detect_impl(
        self,
        tree: ast.AST,
        source: str,
        file_path: str
    ) -> Iterator[PatternSuggestion]:
        """Find non-exhaustive match statements on Enums."""

        # First, collect all Enum definitions in the file
        enums = self._collect_enums(tree)

        # Then find match statements
        for node in ast.walk(tree):
            if isinstance(node, ast.Match):
                result = self._check_match_exhaustiveness(node, enums)
                if result:
                    enum_name, covered, missing, has_wildcard = result
                    if missing and not has_wildcard:
                        yield self._make_suggestion(
                            node, enum_name, covered, missing, file_path
                        )

    def _collect_enums(self, tree: ast.AST) -> dict[str, set[str]]:
        """Collect Enum definitions and their members."""
        enums: dict[str, set[str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if inherits from Enum
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Enum":
                        members = set()
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        members.add(target.id)
                                    elif isinstance(target, ast.Tuple):
                                        for elt in target.elts:
                                            if isinstance(elt, ast.Name):
                                                members.add(elt.id)
                        enums[node.name] = members

        return enums

    def _check_match_exhaustiveness(
        self,
        match: ast.Match,
        enums: dict[str, set[str]]
    ) -> tuple[str, set[str], set[str], bool] | None:
        """Check if match is exhaustive for an Enum."""

        # Try to determine enum type from match subject
        # Look for EnumName.member pattern in cases

        covered: set[str] = set()
        enum_name: str | None = None
        has_wildcard = False

        for case in match.cases:
            if isinstance(case.pattern, ast.MatchAs):
                if case.pattern.pattern is None:
                    has_wildcard = True
            elif isinstance(case.pattern, ast.MatchValue):
                if isinstance(case.pattern.value, ast.Attribute):
                    if isinstance(case.pattern.value.value, ast.Name):
                        case_enum = case.pattern.value.value.id
                        case_member = case.pattern.value.attr

                        if enum_name is None:
                            enum_name = case_enum
                        elif enum_name != case_enum:
                            return None  # Mixed enums, skip

                        covered.add(case_member)

        if enum_name and enum_name in enums:
            all_members = enums[enum_name]
            missing = all_members - covered
            return (enum_name, covered, missing, has_wildcard)

        return None

    def _make_suggestion(
        self,
        match: ast.Match,
        enum_name: str,
        covered: set[str],
        missing: set[str],
        file_path: str,
    ) -> PatternSuggestion:
        """Create suggestion for exhaustive match."""

        missing_list = ", ".join(sorted(missing))

        return PatternSuggestion(
            rule_id=self.rule_id,
            category=self.category,
            priority=self.priority,
            location=self._make_location(match, file_path),
            symbol_name=None,
            title=f"Match on {enum_name} is not exhaustive",
            description=(
                f"Match statement covers {len(covered)} of {len(covered) + len(missing)} "
                f"{enum_name} members. Missing: {missing_list}. "
                f"Add 'case _: assert_never(subject)' to catch future additions."
            ),
            before_code=None,
            after_code=f"case _: assert_never(status)  # from typing import assert_never",
            confidence=0.95,
            reference_file=self.reference_file,
            reference_lines=self.reference_lines,
            suppress_key=f"{file_path}:{match.lineno}:exhaustive:{enum_name}",
        )
```

---

## 6. Pattern Registry

```python
# src/invar/core/patterns/registry.py

from typing import Iterator
from dataclasses import dataclass

from .detector import PatternDetector
from .types import PatternPriority, PatternCategory
from .p0_newtype import NewTypeDetector
from .p0_validation import ValidationPatternDetector
from .p0_nonempty import NonEmptyDetector
from .p0_literal import LiteralTypeDetector
from .p0_exhaustive import ExhaustiveMatchDetector


@dataclass(frozen=True)
class PatternConfig:
    """Configuration for pattern detection."""
    enabled: bool = True
    max_suggestions_per_file: int = 5
    min_confidence: float = 0.5
    enabled_categories: frozenset[PatternCategory] | None = None
    enabled_priorities: frozenset[PatternPriority] | None = None


class PatternRegistry:
    """Registry of all pattern detectors."""

    def __init__(self, config: PatternConfig | None = None):
        self.config = config or PatternConfig()
        self._detectors: list[PatternDetector] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in detectors."""
        # P0 - Core patterns (always registered)
        self._detectors.extend([
            NewTypeDetector(),
            ValidationPatternDetector(),
            NonEmptyDetector(),
            LiteralTypeDetector(),
            ExhaustiveMatchDetector(),
        ])

        # P1 - Extended patterns (TODO: implement)
        # self._detectors.extend([
        #     SmartConstructorDetector(),
        #     StructuredErrorDetector(),
        #     FrozenDataclassDetector(),
        #     TotalFunctionDetector(),
        # ])

    def get_enabled_detectors(self) -> Iterator[PatternDetector]:
        """Get detectors matching current config."""
        if not self.config.enabled:
            return

        for detector in self._detectors:
            # Filter by priority
            if self.config.enabled_priorities:
                if detector.priority not in self.config.enabled_priorities:
                    continue

            # Filter by category
            if self.config.enabled_categories:
                if detector.category not in self.config.enabled_categories:
                    continue

            yield detector

    def register(self, detector: PatternDetector) -> None:
        """Register a custom detector."""
        self._detectors.append(detector)
```

---

## 7. Guard Integration

```python
# Addition to src/invar/shell/commands/guard.py

import ast
from pathlib import Path

from invar.core.patterns import PatternRegistry, PatternConfig, PatternAnalysisResult
from invar.core.patterns.types import PatternSuggestion


def analyze_patterns(
    files: list[Path],
    config: PatternConfig | None = None,
) -> PatternAnalysisResult:
    """Analyze files for pattern improvement opportunities."""

    registry = PatternRegistry(config)
    all_suggestions: list[PatternSuggestion] = []

    for file_path in files:
        try:
            source = file_path.read_text()
            tree = ast.parse(source)

            file_suggestions: list[PatternSuggestion] = []

            for detector in registry.get_enabled_detectors():
                for suggestion in detector.detect(tree, source, str(file_path)):
                    file_suggestions.append(suggestion)

            # Sort by confidence, take top N per file
            file_suggestions.sort(key=lambda s: -s.confidence)
            max_per_file = config.max_suggestions_per_file if config else 5
            all_suggestions.extend(file_suggestions[:max_per_file])

        except SyntaxError:
            continue  # Skip files with syntax errors

    return PatternAnalysisResult(
        suggestions=tuple(all_suggestions),
        files_analyzed=len(files),
        patterns_checked=len(list(registry.get_enabled_detectors())),
        analysis_time_ms=0,  # TODO: measure
    )


def format_suggestions_human(suggestions: tuple[PatternSuggestion, ...]) -> str:
    """Format suggestions for terminal output."""
    if not suggestions:
        return ""

    lines = ["\n--- Suggestions (non-blocking) ---\n"]

    for s in suggestions:
        lines.append(f"SUGGEST [{s.priority}] {s.location.file}:{s.location.line}")
        lines.append(f"  {s.title}")
        lines.append(f"  → {s.description}")
        if s.reference_file:
            ref = s.reference_file
            if s.reference_lines:
                ref += f":{s.reference_lines[0]}-{s.reference_lines[1]}"
            lines.append(f"  → See: {ref}")
        lines.append("")

    return "\n".join(lines)


def format_suggestions_json(suggestions: tuple[PatternSuggestion, ...]) -> dict:
    """Format suggestions for agent consumption."""
    return {
        "suggestions": [
            {
                "rule_id": s.rule_id,
                "category": s.category,
                "priority": s.priority,
                "file": s.location.file,
                "line": s.location.line,
                "symbol": s.symbol_name,
                "title": s.title,
                "description": s.description,
                "before_code": s.before_code,
                "after_code": s.after_code,
                "confidence": s.confidence,
                "reference": {
                    "file": s.reference_file,
                    "lines": s.reference_lines,
                } if s.reference_file else None,
                "suppress_key": s.suppress_key,
            }
            for s in suggestions
        ],
        "count": len(suggestions),
    }
```

---

## 8. Configuration Schema

```toml
# invar.toml additions

[guard.suggestions]
# Master switch for all suggestions
enabled = true

# Maximum suggestions per file (prevents noise)
max_per_file = 5

# Minimum confidence to report (0.0-1.0)
min_confidence = 0.5

# Enable specific priorities only
# priorities = ["P0", "P1"]  # Default: all

# Enable specific categories only
# categories = ["type_safety", "error_handling"]  # Default: all

# Per-rule configuration
[guard.suggestions.rules]
suggest_newtype = { enabled = true, threshold = 3 }
suggest_validation = { enabled = true, min_checks = 2 }
suggest_nonempty = { enabled = true }
suggest_literal_type = { enabled = true, max_values = 10 }
suggest_exhaustive_match = { enabled = true }

# Suppressed suggestions (auto-populated when dismissed)
[guard.suggestions.suppressed]
# "file:symbol:rule:detail" = "2025-12-28"
```

---

## 9. Output Examples

### Terminal Output

```
$ invar guard

src/core/parser.py
  ✅ PASS: 3 functions verified

src/core/config.py
  ✅ PASS: 5 functions verified

--- Suggestions (non-blocking) ---

SUGGEST [P0] src/core/config.py:45
  3 string parameters in 'find_symbol'
  → Consider using NewType for semantic clarity and type safety.
  → See: .invar/examples/functional.py:15-30

SUGGEST [P0] src/core/config.py:78
  Sequential validation in 'validate_config' returns first error only
  → Found 4 consecutive validation checks that return immediately.
  → See: .invar/examples/functional.py:45-70

Summary: 2 files, 8 functions, 0 errors, 0 warnings, 2 suggestions
```

### JSON Output (for agents)

```json
{
  "status": "pass",
  "errors": 0,
  "warnings": 0,
  "suggestions": {
    "count": 2,
    "suggestions": [
      {
        "rule_id": "suggest_newtype",
        "category": "type_safety",
        "priority": "P0",
        "file": "src/core/config.py",
        "line": 45,
        "symbol": "find_symbol",
        "title": "3 string parameters in 'find_symbol'",
        "description": "Consider using NewType for semantic clarity.",
        "after_code": "from typing import NewType\n\nFilePathType = NewType(...)",
        "confidence": 0.85,
        "reference": {
          "file": ".invar/examples/functional.py",
          "lines": [15, 30]
        },
        "suppress_key": "src/core/config.py:find_symbol:newtype:str"
      }
    ]
  }
}
```

---

## 10. Testing Strategy

```python
# tests/core/patterns/test_p0_newtype.py

import pytest
from invar.core.patterns.p0_newtype import NewTypeDetector


class TestNewTypeDetector:
    """Tests for NewType suggestion detection."""

    def test_detects_three_string_params(self):
        """Should suggest NewType for 3+ string parameters."""
        source = '''
def find(path: str, name: str, pattern: str) -> Symbol:
    pass
'''
        detector = NewTypeDetector()
        suggestions = list(detector.detect(
            ast.parse(source), source, "test.py"
        ))

        assert len(suggestions) == 1
        assert suggestions[0].rule_id == "suggest_newtype"
        assert "3 string parameters" in suggestions[0].title

    def test_ignores_two_string_params(self):
        """Should not suggest for only 2 string parameters."""
        source = '''
def find(path: str, name: str) -> Symbol:
    pass
'''
        detector = NewTypeDetector()
        suggestions = list(detector.detect(
            ast.parse(source), source, "test.py"
        ))

        assert len(suggestions) == 0

    def test_ignores_private_functions(self):
        """Should not suggest for private functions."""
        source = '''
def _internal(a: str, b: str, c: str) -> None:
    pass
'''
        detector = NewTypeDetector()
        suggestions = list(detector.detect(
            ast.parse(source), source, "test.py"
        ))

        assert len(suggestions) == 0

    def test_confidence_scales_with_count(self):
        """Higher param count should give higher confidence."""
        source_3 = 'def f(a: str, b: str, c: str): pass'
        source_5 = 'def f(a: str, b: str, c: str, d: str, e: str): pass'

        detector = NewTypeDetector()

        s3 = list(detector.detect(ast.parse(source_3), source_3, "t.py"))
        s5 = list(detector.detect(ast.parse(source_5), source_5, "t.py"))

        assert s5[0].confidence > s3[0].confidence
```

---

## 11. DX-62 Integration

DX-62 (Proactive Reference Reading) integrates with DX-61:

```
Guard outputs suggestion
        │
        ▼
┌─────────────────────────────────┐
│ SUGGEST: Consider NewType       │
│ → See: .invar/examples/func.py  │◀── Reference to example file
│   Lines 15-30                   │
└─────────────────────────────────┘
        │
        ▼
Agent reads referenced file section
        │
        ▼
Agent learns pattern, applies to code
        │
        ▼
Next Guard run: fewer suggestions
```

This creates a **feedback loop**:
1. Agent writes code without pattern knowledge
2. Guard suggests pattern with file reference
3. Agent reads example, learns pattern
4. Agent applies pattern in future code
5. Guard stops suggesting (pattern adopted)

---

## 12. Rollout Phases

| Phase | Scope | Duration | Risk |
|-------|-------|----------|------|
| 1 | Examples file only | 1 day | None |
| 2 | P0 detectors (5 rules) | 2-3 days | Low |
| 3 | Guard integration | 1 day | Low |
| 4 | JSON output | 1 day | None |
| 5 | Config system | 1 day | Low |
| 6 | P1 detectors (4 rules) | 2 days | Medium |

**Total: ~8-9 days**

---

## 13. Success Criteria

| Metric | Measurement | Target |
|--------|-------------|--------|
| Detection accuracy | Manual review of suggestions | >90% relevant |
| False positive rate | Suppressed suggestions | <10% |
| Agent adoption | Code review samples | >50% apply suggestions |
| Performance impact | Guard execution time | <10% increase |
