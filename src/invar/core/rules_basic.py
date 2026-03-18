"""Core rule checks shared by rules engine."""

from __future__ import annotations

from deal import post

from invar.core.entry_points import has_allow_marker
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.suggestions import format_suggestion_for_violation

# P17: Pure alternatives for forbidden imports (module -> suggestion)
FORBIDDEN_IMPORT_ALTERNATIVES: dict[str, str] = {
    "os": "Inject paths as strings",
    "sys": "Pass sys.argv as parameter",
    "pathlib": "Use string operations",
    "subprocess": "Move to Shell",
    "shutil": "Move to Shell",
    "io": "Pass content as str/bytes",
    "socket": "Move to Shell",
    "requests": "Move HTTP to Shell",
    "urllib": "Move to Shell",
    "datetime": "Inject now as parameter",
    "random": "Inject random values",
    "open": "Shell reads, Core processes",
}


@post(lambda result: all(v.rule == "forbidden_import" for v in result))
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
            alt = FORBIDDEN_IMPORT_ALTERNATIVES.get(imp, "")
            suggestion = f"Move I/O code using '{imp}' to Shell"
            if alt:
                suggestion += f". Alternative: {alt}"
            violations.append(
                Violation(
                    rule="forbidden_import",
                    severity=Severity.ERROR,
                    file=file_info.path,
                    line=None,
                    message=f"Imports '{imp}' (forbidden in Core)",
                    suggestion=suggestion,
                )
            )

    return violations


@post(lambda result: all(v.rule == "missing_contract" for v in result))
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

    source = file_info.source or ""
    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and not symbol.contracts:
            if has_allow_marker(symbol, source, "missing_contract"):
                continue
            kind_name = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
            suggestion = format_suggestion_for_violation(symbol, "missing_contract")
            violations.append(
                Violation(
                    rule="missing_contract",
                    severity=Severity.ERROR,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"{kind_name} '{symbol.name}' has no @pre or @post contract",
                    suggestion=suggestion,
                )
            )

    return violations


@post(lambda result: all(v.rule == "missing_doctest" for v in result))
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
        name_part = symbol.name.split(".")[-1] if "." in symbol.name else symbol.name
        is_public = not name_part.startswith("_")
        if (
            symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
            and is_public
            and symbol.contracts
            and not symbol.has_doctest
        ):
            kind_name = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
            violations.append(
                Violation(
                    rule="missing_doctest",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=symbol.line,
                    message=f"{kind_name} '{symbol.name}' has contracts but no doctest examples",
                    suggestion="Add >>> examples in docstring",
                )
            )

    return violations
