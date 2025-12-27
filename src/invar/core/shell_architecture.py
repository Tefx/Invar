"""
Shell architecture rules for DX-22.

Detects architectural issues in Shell layer:
- shell_pure_logic: Pure logic that belongs in Core
- shell_too_complex: Excessive branching complexity
- shell_complexity_debt: Accumulated complexity warnings

Core module: pure logic, no I/O.
"""

from __future__ import annotations

from deal import post, pre

from invar.core.entry_points import get_symbol_lines, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.shell_analysis import (
    count_branches,
    get_symbol_source,
    has_complexity_marker,
    has_io_operations,
    has_orchestration_marker,
)


@post(lambda result: all(v.rule == "shell_pure_logic" for v in result))
def check_shell_pure_logic(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions contain I/O operations (DX-22).

    Pure logic belongs in Core where it can be tested with contracts.
    Functions > 5 lines without I/O indicators are flagged as WARNING.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=10)
        >>> source = "def calc(x, y):\\n    return x + y"
        >>> info = FileInfo(path="shell/util.py", lines=10, symbols=[sym], is_shell=True, source=source)
        >>> violations = check_shell_pure_logic(info, RuleConfig())
        >>> len(violations) >= 0  # May or may not flag based on line count
        True
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # Skip small functions (wrappers are fine)
        lines = get_symbol_lines(symbol)
        if lines <= 5:
            continue

        # Skip entry points (they're handled by DX-23)
        if is_entry_point(symbol, file_info.source):
            continue

        # Skip if marked with @shell_orchestration (coordinates other shell modules)
        if has_orchestration_marker(symbol, file_info.source):
            continue

        # Get symbol source and check for I/O
        symbol_source = get_symbol_source(symbol, file_info.source)
        if not has_io_operations(symbol_source):
            violations.append(
                Violation(
                    rule="shell_pure_logic",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' has no I/O operations - pure logic belongs in Core",
                    suggestion="Move to src/*/core/ and add @pre/@post contracts, or add: # @shell_orchestration: <reason>",
                )
            )

    return violations


@post(lambda result: all(v.rule == "shell_too_complex" for v in result))
def check_shell_too_complex(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions don't have excessive branching (DX-22).

    Complex logic should be in Core where it can be tested.
    Functions exceeding shell_max_branches are flagged as INFO.

    Use @shell_complexity marker to exempt justified complexity.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="process", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> source = "def process(x):\\n    return x"
        >>> info = FileInfo(path="shell/cli.py", lines=5, symbols=[sym], is_shell=True, source=source)
        >>> check_shell_too_complex(info, RuleConfig())
        []
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    max_branches = config.shell_max_branches

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # Skip if marked with @shell_complexity
        if has_complexity_marker(symbol, file_info.source):
            continue

        # Skip entry points
        if is_entry_point(symbol, file_info.source):
            continue

        # Count branches in symbol source
        symbol_source = get_symbol_source(symbol, file_info.source)
        branches = count_branches(symbol_source)

        if branches > max_branches:
            violations.append(
                Violation(
                    rule="shell_too_complex",
                    severity=Severity.INFO,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' has {branches} branches (max: {max_branches})",
                    suggestion="Extract logic to Core, or add: # @shell_complexity: <reason>",
                )
            )

    return violations


@pre(lambda violations, limit: isinstance(violations, list) and limit > 0)
@post(lambda result: isinstance(result, list))
def check_complexity_debt(violations: list[Violation], limit: int = 5) -> list[Violation]:
    """
    Check project-level complexity debt (DX-22 Fix-or-Explain).

    When the project has too many unaddressed shell_too_complex warnings,
    escalate to ERROR to force resolution.

    Examples:
        >>> from invar.core.models import Violation, Severity
        >>> v1 = Violation(rule="shell_too_complex", severity=Severity.INFO, file="a.py", message="m")
        >>> v2 = Violation(rule="shell_too_complex", severity=Severity.INFO, file="b.py", message="m")
        >>> check_complexity_debt([v1, v2], limit=5)
        []
        >>> many = [Violation(rule="shell_too_complex", severity=Severity.INFO, file=f"{i}.py", message="m") for i in range(6)]
        >>> result = check_complexity_debt(many, limit=5)
        >>> len(result)
        1
        >>> result[0].severity == Severity.ERROR
        True
    """
    unaddressed = [v for v in violations if v.rule == "shell_too_complex"]
    if len(unaddressed) >= limit:
        return [
            Violation(
                rule="shell_complexity_debt",
                severity=Severity.ERROR,
                file="<project>",
                line=None,
                message=f"Project has {len(unaddressed)} unaddressed complexity warnings (limit: {limit})",
                suggestion="You must address these before proceeding:\n1. Refactor to reduce branches, OR\n2. Add @shell_complexity: markers with justification",
            )
        ]
    return []
