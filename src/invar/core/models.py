"""
Pydantic models for Invar.

Core models are pure data structures with validation.
No I/O operations allowed.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from deal import pre
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
    INFO = "info"  # Phase 7: For informational issues like redundant type contracts


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
    # Phase 6: Verification Completeness
    doctest_lines: int = 0  # Number of lines that are doctest examples
    # Phase 11 P25: For extraction analysis
    function_calls: list[str] = Field(default_factory=list)  # Functions called within this function


class FileInfo(BaseModel):
    """Information about a Python file."""

    path: str
    lines: int
    symbols: list[Symbol] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    is_core: bool = False
    is_shell: bool = False
    source: str = ""  # Original source code for advanced analysis


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
    infos: int = 0  # Phase 7: Track INFO-level issues
    # P24: Contract coverage statistics (Core files only)
    core_functions_total: int = 0
    core_functions_with_contracts: int = 0

    @pre(lambda self, violation: isinstance(violation, Violation))
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
        elif violation.severity == Severity.WARNING:
            self.warnings += 1
        else:
            self.infos += 1

    @pre(lambda self, total, with_contracts: total >= 0 and with_contracts >= 0)
    def update_coverage(self, total: int, with_contracts: int) -> None:
        """
        Update contract coverage statistics (P24).

        Examples:
            >>> from invar.core.models import GuardReport
            >>> report = GuardReport(files_checked=1)
            >>> report.update_coverage(10, 8)
            >>> report.core_functions_total
            10
            >>> report.core_functions_with_contracts
            8
        """
        self.core_functions_total += total
        self.core_functions_with_contracts += with_contracts

    @property
    @pre(lambda self: isinstance(self, GuardReport))
    def contract_coverage_pct(self) -> int:
        """
        Get contract coverage percentage (P24).

        Examples:
            >>> from invar.core.models import GuardReport
            >>> report = GuardReport(files_checked=1)
            >>> report.update_coverage(10, 8)
            >>> report.contract_coverage_pct
            80
        """
        if self.core_functions_total == 0:
            return 100
        return int(self.core_functions_with_contracts / self.core_functions_total * 100)

    @property
    @pre(lambda self: isinstance(self, GuardReport))
    def contract_issue_counts(self) -> dict[str, int]:
        """
        Count contract quality issues by type (P24).

        Examples:
            >>> from invar.core.models import GuardReport, Violation, Severity
            >>> report = GuardReport(files_checked=1)
            >>> v1 = Violation(rule="empty_contract", severity=Severity.WARNING, file="x.py", message="m")
            >>> v2 = Violation(rule="semantic_tautology", severity=Severity.WARNING, file="x.py", message="m")
            >>> report.add_violation(v1)
            >>> report.add_violation(v2)
            >>> report.contract_issue_counts
            {'tautology': 1, 'empty': 1, 'partial': 0, 'type_only': 0}
        """
        counts = {"tautology": 0, "empty": 0, "partial": 0, "type_only": 0}
        for v in self.violations:
            if v.rule == "semantic_tautology":
                counts["tautology"] += 1
            elif v.rule == "empty_contract":
                counts["empty"] += 1
            elif v.rule == "partial_contract":
                counts["partial"] += 1
            elif v.rule == "redundant_type_contract":
                counts["type_only"] += 1
        return counts

    @property
    @pre(lambda self: isinstance(self, GuardReport))
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


class RuleExclusion(BaseModel):
    """
    A rule exclusion pattern for specific files.

    Examples:
        >>> excl = RuleExclusion(pattern="**/generated/**", rules=["*"])
        >>> excl.pattern
        '**/generated/**'
        >>> excl.rules
        ['*']
    """

    pattern: str  # Glob pattern (fnmatch style with ** support)
    rules: list[str]  # Rule names to exclude, or ["*"] for all


class RuleConfig(BaseModel):
    """
    Configuration for rule checking.

    Examples:
        >>> config = RuleConfig()
        >>> config.max_file_lines  # Phase 9 P1: Raised from 300
        500
        >>> config.strict_pure  # Phase 9 P12: Default ON for agents
        True
    """

    max_file_lines: int = 500  # Phase 9 P1: Raised from 300 for less friction
    max_function_lines: int = 50
    entry_max_lines: int = 15  # DX-23: Entry point max lines
    shell_max_branches: int = 3  # DX-22: Shell function max branches
    shell_complexity_debt_limit: int = 5  # DX-22: Max unaddressed complexity warnings
    forbidden_imports: tuple[str, ...] = (
        "os",
        "sys",
        "socket",
        "requests",
        "urllib",
        "subprocess",
        "shutil",
        "io",
        "pathlib",
    )
    require_contracts: bool = True
    require_doctests: bool = True
    strict_pure: bool = True  # Phase 9 P12: Default ON for agent-native
    # DX-22: Removed use_code_lines and exclude_doctest_lines
    # (merged into default behavior - always exclude doctest lines from size calc)
    # Phase 9 P1: Rule exclusions for specific file patterns
    rule_exclusions: list[RuleExclusion] = Field(default_factory=list)
    # Phase 9 P2: Per-rule severity overrides (off, info, warning, error)
    # DX-22: Simplified defaults - most rules have correct severity now
    severity_overrides: dict[str, str] = Field(default_factory=dict)
    # Phase 9 P8: File size warning threshold (0 to disable, 0.8 = warn at 80%)
    size_warning_threshold: float = 0.8
    # B4: User-declared purity (override heuristics)
    purity_pure: list[str] = Field(default_factory=list)  # Known pure functions
    purity_impure: list[str] = Field(default_factory=list)  # Known impure functions


# Phase 4: Perception models


class SymbolRefs(BaseModel):
    """
    A symbol with its cross-file reference count.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind, SymbolRefs
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> sr = SymbolRefs(symbol=sym, file_path="core/calc.py", ref_count=10)
        >>> sr.ref_count
        10
    """

    symbol: Symbol
    file_path: str
    ref_count: int = 0


class PerceptionMap(BaseModel):
    """
    Complete perception map for a project.

    Examples:
        >>> pm = PerceptionMap(project_root="/test", total_files=5, total_symbols=20)
        >>> pm.total_files
        5
    """

    project_root: str
    total_files: int
    total_symbols: int
    symbols: list[SymbolRefs] = Field(default_factory=list)
