"""
Rule engine for Guard.

Rules check FileInfo and produce Violations.
No I/O operations - receives parsed data only.
"""

from __future__ import annotations

from typing import Callable

from deal import post, pre

from invar.core.models import (
    FileInfo,
    RuleConfig,
    Severity,
    SymbolKind,
    Violation,
)
from invar.core.purity import check_impure_calls, check_internal_imports

# Type alias for rule functions
RuleFunc = Callable[[FileInfo, RuleConfig], list[Violation]]


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_file_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if file exceeds maximum line count.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> check_file_size(FileInfo(path="ok.py", lines=100), RuleConfig())
        []
        >>> len(check_file_size(FileInfo(path="big.py", lines=400), RuleConfig()))
        1
    """
    violations: list[Violation] = []

    if file_info.lines > config.max_file_lines:
        violations.append(
            Violation(
                rule="file_size",
                severity=Severity.ERROR,
                file=file_info.path,
                line=None,
                message=f"File has {file_info.lines} lines (max: {config.max_file_lines})",
                suggestion="Split into smaller modules",
            )
        )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_function_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if any function exceeds maximum line count.

    When use_code_lines is True, uses code_lines (excluding docstring).

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=10)
        >>> info = FileInfo(path="test.py", lines=20, symbols=[sym])
        >>> cfg = RuleConfig(max_function_lines=50)
        >>> check_function_size(info, cfg)
        []
    """
    violations: list[Violation] = []

    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            # Use code_lines if available and enabled, otherwise total lines
            if config.use_code_lines and symbol.code_lines is not None:
                func_lines = symbol.code_lines
                line_type = "code lines"
            else:
                func_lines = symbol.end_line - symbol.line + 1
                line_type = "lines"

            if func_lines > config.max_function_lines:
                violations.append(
                    Violation(
                        rule="function_size",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=(
                            f"Function '{symbol.name}' has {func_lines} {line_type} "
                            f"(max: {config.max_function_lines})"
                        ),
                        suggestion="Extract helper functions",
                    )
                )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_forbidden_imports(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check for forbidden imports in Core files.

    Only applies to files marked as Core.

    Examples:
        >>> from invar.core.models import FileInfo
        >>> info = FileInfo(path="core/calc.py", lines=10, imports=["math"], is_core=True)
        >>> cfg = RuleConfig()
        >>> check_forbidden_imports(info, cfg)
        []
        >>> info = FileInfo(path="core/bad.py", lines=10, imports=["os"], is_core=True)
        >>> violations = check_forbidden_imports(info, cfg)
        >>> len(violations)
        1
    """
    violations: list[Violation] = []

    if not file_info.is_core:
        return violations

    for imp in file_info.imports:
        if imp in config.forbidden_imports:
            violations.append(
                Violation(
                    rule="forbidden_import",
                    severity=Severity.ERROR,
                    file=file_info.path,
                    line=None,
                    message=f"Imports '{imp}' (forbidden in Core)",
                    suggestion=f"Move I/O code using '{imp}' to Shell",
                )
            )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_contracts(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that public Core functions have contracts.

    Only applies to files marked as Core when require_contracts is True.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract
        >>> contract = Contract(kind="pre", expression="x > 0", line=1)
        >>> sym = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5, contracts=[contract])
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> cfg = RuleConfig(require_contracts=True)
        >>> check_contracts(info, cfg)
        []
    """
    violations: list[Violation] = []

    if not file_info.is_core or not config.require_contracts:
        return violations

    for symbol in file_info.symbols:
        # Only check public functions (not _private)
        if symbol.kind == SymbolKind.FUNCTION and not symbol.name.startswith("_"):
            if not symbol.contracts:
                violations.append(
                    Violation(
                        rule="missing_contract",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"Function '{symbol.name}' has no @pre or @post contract",
                        suggestion="Add @pre for input validation or @post for output guarantee",
                    )
                )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_doctests(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that contracted functions have doctest examples.

    Only applies to files marked as Core when require_doctests is True.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, Contract
        >>> contract = Contract(kind="pre", expression="x > 0", line=1)
        >>> sym = Symbol(
        ...     name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     contracts=[contract], has_doctest=True
        ... )
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym], is_core=True)
        >>> cfg = RuleConfig(require_doctests=True)
        >>> check_doctests(info, cfg)
        []
    """
    violations: list[Violation] = []

    if not file_info.is_core or not config.require_doctests:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind == SymbolKind.FUNCTION and symbol.contracts and not symbol.has_doctest:
            violations.append(
                Violation(
                    rule="missing_doctest",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Function '{symbol.name}' has contracts but no doctest examples",
                    suggestion="Add >>> examples in docstring",
                )
            )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_shell_result(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions with return values use Result[T, E].

    Skips: private functions, functions returning None (CLI entry points).

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="load", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(path: str) -> Result[str, str]")
        >>> info = FileInfo(path="shell/fs.py", lines=10, symbols=[sym], is_shell=True)
        >>> check_shell_result(info, RuleConfig())
        []
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION or symbol.name.startswith("_"):
            continue
        # Skip functions with no return type or returning None
        if "-> None" in symbol.signature or "->" not in symbol.signature:
            continue
        if "Result[" not in symbol.signature:
            violations.append(
                Violation(
                    rule="shell_result",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' should return Result[T, E]",
                    suggestion="Use Result[T, E] from returns library",
                )
            )
    return violations


@post(lambda result: len(result) > 0)
def get_all_rules() -> list[RuleFunc]:
    """
    Return all available rule functions.

    Examples:
        >>> rules = get_all_rules()
        >>> len(rules) >= 5
        True
    """
    return [
        check_file_size,
        check_function_size,
        check_forbidden_imports,
        check_contracts,
        check_doctests,
        check_shell_result,
        check_internal_imports,
        check_impure_calls,
    ]


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_all_rules(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Run all rules against a file and collect violations.

    Examples:
        >>> from invar.core.models import FileInfo
        >>> info = FileInfo(path="test.py", lines=50)
        >>> cfg = RuleConfig()
        >>> violations = check_all_rules(info, cfg)
        >>> isinstance(violations, list)
        True
    """
    violations: list[Violation] = []

    for rule in get_all_rules():
        violations.extend(rule(file_info, config))

    return violations
