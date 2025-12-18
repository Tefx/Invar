"""
Pydantic models for Invar.

Core models are pure data structures with validation.
No I/O operations allowed.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SymbolKind(str, Enum):
    """Kind of symbol extracted from Python code."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"


class Severity(str, Enum):
    """Severity level for violations."""

    ERROR = "error"
    WARNING = "warning"


class Contract(BaseModel):
    """A contract (precondition or postcondition) on a function."""

    kind: Literal["pre", "post"]
    expression: str
    line: int


class Symbol(BaseModel):
    """A symbol extracted from Python source code."""

    name: str
    kind: SymbolKind
    line: int
    end_line: int
    signature: str = ""
    docstring: str | None = None
    contracts: list[Contract] = Field(default_factory=list)
    has_doctest: bool = False
    # Phase 3: Guard Enhancement
    internal_imports: list[str] = Field(default_factory=list)
    impure_calls: list[str] = Field(default_factory=list)
    code_lines: int | None = None  # Lines excluding docstring/comments


class FileInfo(BaseModel):
    """Information about a Python file."""

    path: str
    lines: int
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    is_core: bool = False
    is_shell: bool = False


class Violation(BaseModel):
    """A rule violation found by Guard."""

    rule: str
    severity: Severity
    file: str
    line: int | None = None
    message: str
    suggestion: str | None = None


class GuardReport(BaseModel):
    """Complete Guard report for a project."""

    files_checked: int
    violations: list[Violation] = Field(default_factory=list)
    errors: int = 0
    warnings: int = 0

    def add_violation(self, violation: Violation) -> None:
        """
        Add a violation and update counts.

        Examples:
            >>> from invar.core.models import Violation, Severity, GuardReport
            >>> report = GuardReport(files_checked=1)
            >>> v = Violation(rule="test", severity=Severity.ERROR, file="x.py", message="err")
            >>> report.add_violation(v)
            >>> report.errors
            1
        """
        self.violations.append(violation)
        if violation.severity == Severity.ERROR:
            self.errors += 1
        else:
            self.warnings += 1

    @property
    def passed(self) -> bool:
        """
        Check if guard passed (no errors).

        Examples:
            >>> from invar.core.models import GuardReport
            >>> report = GuardReport(files_checked=1)
            >>> report.passed
            True
        """
        return self.errors == 0
