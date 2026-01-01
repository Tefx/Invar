# @invar:allow file_size: LX-10 added layer types and functions, extraction planned
"""
Pydantic models for Invar.

Core models are pure data structures with validation.
No I/O operations allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from deal import post, pre
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
    SUGGEST = "suggest"  # DX-61: Functional pattern suggestions


class CodeLayer(str, Enum):
    """Code layer for differentiated size limits (LX-10)."""

    CORE = "core"
    SHELL = "shell"
    TESTS = "tests"
    DEFAULT = "default"


@dataclass(frozen=True)
class LayerLimits:
    """Size limits for a specific code layer (LX-10).

    Examples:
        >>> limits = LayerLimits(max_file_lines=500, max_function_lines=50)
        >>> limits.max_file_lines
        500
        >>> limits.max_function_lines
        50
    """

    max_file_lines: int
    max_function_lines: int


# LX-10: Hardcoded layer limits (no config needed)
PYTHON_LAYER_LIMITS: dict[CodeLayer, LayerLimits] = {
    CodeLayer.CORE: LayerLimits(500, 50),
    CodeLayer.SHELL: LayerLimits(700, 100),
    CodeLayer.TESTS: LayerLimits(1000, 200),
    CodeLayer.DEFAULT: LayerLimits(600, 80),
}

TYPESCRIPT_LAYER_LIMITS: dict[CodeLayer, LayerLimits] = {
    CodeLayer.CORE: LayerLimits(650, 65),
    CodeLayer.SHELL: LayerLimits(910, 130),
    CodeLayer.TESTS: LayerLimits(1300, 260),
    CodeLayer.DEFAULT: LayerLimits(780, 104),
}


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


# LX-10: Layer detection functions
@pre(lambda file_info: file_info is not None and hasattr(file_info, "path"))
@post(lambda result: result in CodeLayer)
def get_layer(file_info: FileInfo) -> CodeLayer:
    """
    Determine code layer from FileInfo classification.

    Uses existing is_core/is_shell fields. Tests detection via path.

    Examples:
        >>> get_layer(FileInfo(path="src/core/logic.py", lines=10, is_core=True))
        <CodeLayer.CORE: 'core'>
        >>> get_layer(FileInfo(path="src/shell/cli.py", lines=10, is_shell=True))
        <CodeLayer.SHELL: 'shell'>
        >>> get_layer(FileInfo(path="tests/test_foo.py", lines=10))
        <CodeLayer.TESTS: 'tests'>
        >>> get_layer(FileInfo(path="src/utils.py", lines=10))
        <CodeLayer.DEFAULT: 'default'>
        >>> # Edge: "test_" must be at filename start, not anywhere in path
        >>> get_layer(FileInfo(path="src/contest_utils.py", lines=10))
        <CodeLayer.DEFAULT: 'default'>
        >>> get_layer(FileInfo(path="src/foo_test.py", lines=10))
        <CodeLayer.TESTS: 'tests'>
    """
    # Tests: path-based (no is_tests field exists)
    path_lower = file_info.path.replace("\\", "/").lower()
    filename = path_lower.rsplit("/", 1)[-1]  # Extract filename
    # Match: /tests/ dir, /test/ dir, test_*.py files, *_test.py files
    if (
        "/tests/" in path_lower
        or "/test/" in path_lower
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    ):
        return CodeLayer.TESTS

    # Core/Shell: use existing classification
    if file_info.is_core:
        return CodeLayer.CORE
    if file_info.is_shell:
        return CodeLayer.SHELL

    return CodeLayer.DEFAULT


@pre(lambda layer, language="python": isinstance(layer, CodeLayer) and language in ("python", "typescript"))
@post(lambda result: result.max_file_lines > 0 and result.max_function_lines > 0)
def get_limits(layer: CodeLayer, language: str = "python") -> LayerLimits:
    """
    Get size limits for layer and language.

    Examples:
        >>> get_limits(CodeLayer.CORE).max_function_lines
        50
        >>> get_limits(CodeLayer.SHELL).max_function_lines
        100
        >>> get_limits(CodeLayer.CORE, "typescript").max_function_lines
        65
    """
    limits = TYPESCRIPT_LAYER_LIMITS if language == "typescript" else PYTHON_LAYER_LIMITS
    return limits[layer]


class Violation(BaseModel):
    """A rule violation found by Guard."""

    rule: str
    severity: Severity
    file: str
    line: int | None = None
    message: str
    suggestion: str | None = None


class EscapeHatchDetail(BaseModel):
    """
    Detail of a single escape hatch (@invar:allow) marker (DX-66).

    Examples:
        >>> d = EscapeHatchDetail(file="test.py", line=10, rule="shell_result", reason="API")
        >>> d.line
        10
        >>> # line=0 is valid (fallback when line number unknown)
        >>> d0 = EscapeHatchDetail(file="test.py", line=0, rule="test", reason="fallback")
        >>> d0.line
        0
    """

    file: str
    line: int = Field(ge=0)  # 0 = fallback when line number unknown
    rule: str
    reason: str


class EscapeHatchSummary(BaseModel):
    """
    Summary of escape hatches in the codebase (DX-66).

    Provides visibility into @invar:allow usage for tracking technical debt.

    Examples:
        >>> summary = EscapeHatchSummary()
        >>> summary.count
        0
        >>> summary.by_rule
        {}
        >>> detail = EscapeHatchDetail(file="test.py", line=10, rule="shell_result", reason="API boundary")
        >>> summary.add(detail)
        >>> summary.count
        1
        >>> summary.by_rule
        {'shell_result': 1}
    """

    details: list[EscapeHatchDetail] = Field(default_factory=list)

    @property
    @post(lambda result: result >= 0)
    def count(self) -> int:
        """
        Total number of escape hatches.

        Examples:
            >>> EscapeHatchSummary().count
            0
        """
        return len(self.details)

    @property
    @post(lambda result: all(v >= 0 for v in result.values()))
    def by_rule(self) -> dict[str, int]:
        """
        Count of escape hatches grouped by rule.

        Examples:
            >>> EscapeHatchSummary().by_rule
            {}
        """
        counts: dict[str, int] = {}
        for detail in self.details:
            counts[detail.rule] = counts.get(detail.rule, 0) + 1
        return counts

    @pre(lambda self, detail: bool(detail.rule) and bool(detail.file))
    def add(self, detail: EscapeHatchDetail) -> None:
        """
        Add an escape hatch detail to the summary.

        Examples:
            >>> s = EscapeHatchSummary()
            >>> s.add(EscapeHatchDetail(file="t.py", line=1, rule="r", reason="x"))
            >>> s.count
            1
        """
        self.details.append(detail)


class GuardReport(BaseModel):
    """Complete Guard report for a project."""

    files_checked: int
    violations: list[Violation] = Field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    infos: int = 0  # Phase 7: Track INFO-level issues
    suggests: int = 0  # DX-61: Track SUGGEST-level pattern suggestions
    # P24: Contract coverage statistics (Core files only)
    core_functions_total: int = 0
    core_functions_with_contracts: int = 0
    # DX-66: Escape hatch visibility
    escape_hatches: EscapeHatchSummary = Field(default_factory=EscapeHatchSummary)

    @pre(lambda self, violation: violation.rule and violation.severity)  # Valid violation
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
            >>> v2 = Violation(rule="pattern", severity=Severity.SUGGEST, file="x.py", message="sug")
            >>> report.add_violation(v2)
            >>> report.suggests
            1
        """
        self.violations.append(violation)
        if violation.severity == Severity.ERROR:
            self.errors += 1
        elif violation.severity == Severity.WARNING:
            self.warnings += 1
        elif violation.severity == Severity.SUGGEST:
            self.suggests += 1
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
    @post(lambda result: 0 <= result <= 100)
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
    @post(lambda result: all(k in result for k in ("tautology", "empty", "partial", "type_only")))
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
    @post(lambda result: isinstance(result, bool))
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
        >>> # MINOR-6: Value ranges validated
        >>> RuleConfig(max_file_lines=0)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        pydantic_core._pydantic_core.ValidationError: ...
    """

    # MINOR-6: Added ge=1 constraints for numeric fields
    max_file_lines: int = Field(default=500, ge=1)  # Phase 9 P1: Raised from 300
    max_function_lines: int = Field(default=50, ge=1)
    entry_max_lines: int = Field(default=15, ge=1)  # DX-23: Entry point max lines
    shell_max_branches: int = Field(default=3, ge=1)  # DX-22: Shell function max branches
    shell_complexity_debt_limit: int = Field(default=5, ge=0)  # DX-22: 0 = no limit
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
    size_warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    # B4: User-declared purity (override heuristics)
    purity_pure: list[str] = Field(default_factory=list)  # Known pure functions
    purity_impure: list[str] = Field(default_factory=list)  # Known impure functions

    # Timeout configuration (seconds) - MAJOR-3 fix
    timeout_doctest: int = Field(default=60, ge=1, le=600)  # Doctests should be fast
    timeout_hypothesis: int = Field(default=300, ge=1, le=1800)  # Property tests
    timeout_crosshair: int = Field(default=300, ge=1, le=1800)  # Symbolic verification total
    timeout_crosshair_per_condition: int = Field(default=30, ge=1, le=300)  # Per-contract limit

    # DX-61: Pattern detection configuration
    pattern_min_confidence: str = Field(default="medium")  # low, medium, high
    pattern_priorities: list[str] = Field(default_factory=lambda: ["P0"])  # P0, P1
    pattern_exclude: list[str] = Field(default_factory=list)  # Pattern IDs to exclude


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

    # MINOR-7: Added field validators
    project_root: str = Field(min_length=1)
    total_files: int = Field(ge=0)
    total_symbols: int = Field(ge=0)
    symbols: list[SymbolRefs] = Field(default_factory=list)
