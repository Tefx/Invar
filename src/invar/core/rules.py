# @invar:allow file_size: LX-10 added doctests, consider extraction later
"""Rule engine for Guard. Rules check FileInfo and produce Violations. No I/O."""

from __future__ import annotations

from collections.abc import Callable

from deal import post, pre

from invar.core.contracts import (
    check_empty_contracts,
    check_param_mismatch,
    check_partial_contract,
    check_redundant_type_contracts,
    check_semantic_tautology,
    check_skip_without_reason,
)
from invar.core.entry_points import (
    extract_escape_hatches,
    get_symbol_lines,
    has_allow_marker,
    is_entry_point,
)
from invar.core.extraction import format_extraction_hint
from invar.core.models import (
    FileInfo,
    RuleConfig,
    Severity,
    SymbolKind,
    Violation,
    get_layer,
    get_limits,
)
from invar.core.must_use import check_must_use
from invar.core.postcondition_scope import check_postcondition_scope
from invar.core.purity import check_impure_calls, check_internal_imports
from invar.core.review_trigger import check_contract_quality_ratio, check_review_suggested
from invar.core.shell_architecture import check_shell_pure_logic, check_shell_too_complex
from invar.core.suggestions import format_suggestion_for_violation
from invar.core.utils import get_excluded_rules

# P17: Pure alternatives for forbidden imports (module → suggestion)
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

# Type alias for rule functions
RuleFunc = Callable[[FileInfo, RuleConfig], list[Violation]]


@post(lambda result: isinstance(result, str))
def _build_size_suggestion(base: str, extraction_hint: str, func_hint: str) -> str:
    """Build suggestion message with extraction hints."""
    if extraction_hint:
        return f"{base}\nExtractable groups:\n{extraction_hint}"
    return f"{base}{func_hint}" if func_hint else base


@post(lambda result: isinstance(result, str))
def _get_func_hint(file_info: FileInfo) -> str:
    """Get top 5 largest functions as hint string."""
    funcs = sorted(
        [(s.name, s.end_line - s.line + 1) for s in file_info.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)],
        key=lambda x: -x[1],
    )[:5]
    return f" Functions: {', '.join(f'{n}({sz}L)' for n, sz in funcs)}" if funcs else ""


@pre(lambda file_info, rule: file_info is not None and len(rule) > 0)
@post(lambda result: isinstance(result, bool))
def _has_file_escape(file_info: FileInfo, rule: str) -> bool:
    """Check if file has escape hatch for given rule.

    Examples:
        >>> info = FileInfo(path="test.py", lines=10, source="# @invar:allow file_size: reason")
        >>> _has_file_escape(info, "file_size")
        True
        >>> _has_file_escape(info, "other_rule")
        False
        >>> # Edge: empty source returns False
        >>> _has_file_escape(FileInfo(path="x.py", lines=1), "any")
        False
    """
    if not file_info.source:
        return False
    escapes = extract_escape_hatches(file_info.source)
    return any(r == rule for r, _, _ in escapes)


@post(lambda result: all(v.rule in ("file_size", "file_size_warning") for v in result))
def check_file_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if file exceeds maximum line count or warning threshold.

    LX-10: Uses layer-based limits (Core/Shell/Tests/Default).
    P18: Shows function groups in size warnings to help agents decide what to extract.
    P25: Shows extractable groups with dependencies for warnings.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> check_file_size(FileInfo(path="ok.py", lines=100), RuleConfig())
        []
        >>> # Default layer: 600 lines max, error at 650
        >>> len(check_file_size(FileInfo(path="big.py", lines=650), RuleConfig()))
        1
        >>> # Shell layer: 700 lines max, no error at 650
        >>> vs = check_file_size(FileInfo(path="shell/cli.py", lines=550, is_shell=True), RuleConfig())
        >>> any(v.rule == "file_size" for v in vs)
        False
        >>> # Core layer: 500 lines max (strict)
        >>> len(check_file_size(FileInfo(path="core/calc.py", lines=550, is_core=True), RuleConfig()))
        1
    """
    # Check for escape hatch
    if _has_file_escape(file_info, "file_size"):
        return []

    violations: list[Violation] = []
    func_hint = _get_func_hint(file_info)
    extraction_hint = format_extraction_hint(file_info)

    # LX-10: Get layer-based limits
    layer = get_layer(file_info)
    limits = get_limits(layer)
    max_lines = limits.max_file_lines

    if file_info.lines > max_lines:
        violations.append(Violation(
            rule="file_size", severity=Severity.ERROR, file=file_info.path, line=None,
            message=f"File has {file_info.lines} lines (max: {max_lines} for {layer.value})",
            suggestion=_build_size_suggestion("Split into smaller modules.", extraction_hint, func_hint),
        ))
    elif config.size_warning_threshold > 0:
        threshold = int(max_lines * config.size_warning_threshold)
        if file_info.lines >= threshold:
            pct = int(file_info.lines / max_lines * 100)
            violations.append(Violation(
                rule="file_size_warning", severity=Severity.WARNING, file=file_info.path, line=None,
                message=f"File has {file_info.lines} lines ({pct}% of {max_lines} limit)",
                suggestion=_build_size_suggestion("Consider splitting before reaching limit.", extraction_hint, func_hint),
            ))
    return violations


@post(lambda result: all(v.rule == "function_size" for v in result))
def check_function_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if any function exceeds maximum line count.

    LX-10: Uses layer-based limits (Core/Shell/Tests/Default).
    DX-22: Always uses code_lines (excluding docstring) and excludes doctest lines.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=10)
        >>> info = FileInfo(path="test.py", lines=20, symbols=[sym])
        >>> check_function_size(info, RuleConfig())
        []
        >>> # Shell layer: 100 lines max (more lenient)
        >>> sym2 = Symbol(name="cli", kind=SymbolKind.FUNCTION, line=1, end_line=80)
        >>> info2 = FileInfo(path="shell/cli.py", lines=100, symbols=[sym2], is_shell=True)
        >>> check_function_size(info2, RuleConfig())
        []
        >>> # Core layer: 50 lines max (strict)
        >>> sym3 = Symbol(name="calc", kind=SymbolKind.FUNCTION, line=1, end_line=60)
        >>> info3 = FileInfo(path="core/calc.py", lines=100, symbols=[sym3], is_core=True)
        >>> len(check_function_size(info3, RuleConfig()))
        1
    """
    violations: list[Violation] = []

    # LX-10: Get layer-based limits
    layer = get_layer(file_info)
    limits = get_limits(layer)
    max_func_lines = limits.max_function_lines

    for symbol in file_info.symbols:
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            # LX-10: Check for escape hatch on individual functions
            if has_allow_marker(symbol, file_info.source, "function_size"):
                continue
            total_lines = symbol.end_line - symbol.line + 1
            # DX-22: Always use code_lines when available (excluding docstring)
            if symbol.code_lines is not None:
                func_lines = symbol.code_lines
                line_type = "code lines"
            else:
                func_lines = total_lines
                line_type = "lines"
            # DX-22: Always exclude doctest lines from size calculation
            if symbol.doctest_lines > 0:
                func_lines -= symbol.doctest_lines
                line_type = f"{line_type} (excl. doctest)"

            if func_lines > max_func_lines:
                violations.append(
                    Violation(
                        rule="function_size",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"Function '{symbol.name}' has {func_lines} {line_type} (max: {max_func_lines} for {layer.value})",
                        suggestion="Extract helper functions",
                    )
                )

    return violations


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
            # P17: Include pure alternative in suggestion
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
        # Check all functions and methods - agent needs contracts everywhere
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and not symbol.contracts:
            # DX-22: Skip if @invar:allow marker present
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
        # Only public functions/methods require doctests (private can skip)
        # For methods, check if method name (after dot) starts with _
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


@post(lambda result: all(v.rule == "shell_result" for v in result))
def check_shell_result(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions with return values use Result[T, E].

    Skips:
    - Functions returning None (CLI entry points)
    - Generators (Iterator/Generator/AsyncIterator/AsyncGenerator)
    - Entry points (DX-23: framework callbacks like Flask routes, Typer commands)

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
        if symbol.kind != SymbolKind.FUNCTION:
            continue
        # Skip functions with no return type or returning None
        if "-> None" in symbol.signature or "->" not in symbol.signature:
            continue
        # Skip generators (Iterator/Generator/AsyncIterator/AsyncGenerator) - acceptable per protocol
        # MINOR-11: Added async variants
        if any(
            pattern in symbol.signature
            for pattern in ("Iterator[", "Generator[", "AsyncIterator[", "AsyncGenerator[")
        ):
            continue
        # DX-23: Skip entry points; DX-22: Skip if @invar:allow marker
        if is_entry_point(symbol, file_info.source) or has_allow_marker(symbol, file_info.source, "shell_result"):
            continue
        if "Result[" not in symbol.signature:
            violations.append(
                Violation(
                    rule="shell_result",
                    severity=Severity.ERROR,  # DX-22: Architecture rule
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Shell function '{symbol.name}' should return Result[T, E]",
                    suggestion="Use Result[T, E], or add: # @invar:allow shell_result: <reason>",
                )
            )
    return violations


@post(lambda result: all(v.rule == "entry_point_too_thick" for v in result))
def check_entry_point_thin(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that entry points are thin (DX-23).

    Entry points should delegate to Shell functions and not contain
    business logic. They serve as "monad runners" at framework boundaries.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> sym = Symbol(name="index", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> source = '@app.route("/")\\ndef index(): pass'
        >>> info = FileInfo(path="shell/web.py", lines=10, symbols=[sym], is_shell=True, source=source)
        >>> check_entry_point_thin(info, RuleConfig())
        []
    """
    violations: list[Violation] = []
    if not file_info.is_shell:
        return violations

    max_lines = config.entry_max_lines

    for symbol in file_info.symbols:
        if symbol.kind != SymbolKind.FUNCTION:
            continue

        # Only check entry points; DX-22: Skip if @invar:allow marker
        if not is_entry_point(symbol, file_info.source) or has_allow_marker(symbol, file_info.source, "entry_point_too_thick"):
            continue
        lines = get_symbol_lines(symbol)
        if lines > max_lines:
            violations.append(
                Violation(
                    rule="entry_point_too_thick",
                    severity=Severity.ERROR,  # DX-22: Architecture rule
                    file=file_info.path,
                    line=symbol.line,
                    message=f"Entry point '{symbol.name}' has {lines} lines (max: {max_lines})",
                    suggestion="Move logic to Shell function, or add: # @invar:allow entry_point_too_thick: <reason>",
                )
            )

    return violations


@post(lambda result: len(result) > 0)
def get_all_rules() -> list[RuleFunc]:
    """
    Return all available rule functions.

    Examples:
        >>> len(get_all_rules()) >= 5
        True
    """
    return [
        check_file_size,
        check_function_size,
        check_forbidden_imports,
        check_contracts,
        check_doctests,
        check_shell_result,
        check_entry_point_thin,  # DX-23
        check_shell_pure_logic,  # DX-22
        check_shell_too_complex,  # DX-22
        check_internal_imports,
        check_impure_calls,
        check_empty_contracts,
        check_semantic_tautology,
        check_redundant_type_contracts,
        check_param_mismatch,
        check_partial_contract,
        check_postcondition_scope,
        check_must_use,
        check_skip_without_reason,  # DX-28
        check_contract_quality_ratio,  # DX-30
        check_review_suggested,  # DX-31
    ]


@post(lambda result: result is None or isinstance(result, Violation))
def _apply_severity_override(v: Violation, overrides: dict[str, str]) -> Violation | None:
    """
    Apply severity override to a violation.

    Returns None if rule is set to "off", otherwise returns violation
    with potentially updated severity.

    Examples:
        >>> from invar.core.models import Violation, Severity
        >>> v = Violation(rule="test", severity=Severity.INFO, file="x.py", message="msg")
        >>> _apply_severity_override(v, {"test": "off"}) is None
        True
        >>> v2 = _apply_severity_override(v, {"test": "error"})
        >>> v2.severity
        <Severity.ERROR: 'error'>
        >>> _apply_severity_override(v, {}).severity  # No override
        <Severity.INFO: 'info'>
    """
    override = overrides.get(v.rule)
    if override is None:
        return v
    if override == "off":
        return None
    # Map string to Severity enum
    severity_map = {"info": Severity.INFO, "warning": Severity.WARNING, "error": Severity.ERROR}
    new_severity = severity_map.get(override)
    if new_severity is None:
        return v  # Invalid override, keep original
    # Create new violation with updated severity
    return Violation(
        rule=v.rule,
        severity=new_severity,
        file=v.file,
        line=v.line,
        message=v.message,
        suggestion=v.suggestion,
    )


@post(lambda result: all(v.rule and v.file for v in result) if result else True)
def check_all_rules(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Run all rules against a file and collect violations.

    Respects rule_exclusions and severity_overrides config.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig, RuleExclusion
        >>> violations = check_all_rules(FileInfo(path="test.py", lines=50), RuleConfig())
        >>> isinstance(violations, list)
        True
        >>> # Test exclusion: file_size excluded for generated files
        >>> excl = RuleExclusion(pattern="**/generated/**", rules=["file_size"])
        >>> cfg = RuleConfig(rule_exclusions=[excl])
        >>> big_file = FileInfo(path="src/generated/data.py", lines=600)
        >>> vs = check_all_rules(big_file, cfg)
        >>> any(v.rule == "file_size" for v in vs)
        False
    """
    # Phase 9 P1: Get excluded rules for this file
    excluded = get_excluded_rules(file_info.path, config)
    exclude_all = "*" in excluded

    violations = []
    for rule in get_all_rules():
        for v in rule(file_info, config):
            # Skip if rule is excluded (either specifically or via "*")
            if exclude_all or v.rule in excluded:
                continue
            # Phase 9 P2: Apply severity overrides
            v = _apply_severity_override(v, config.severity_overrides)
            if v is not None:
                violations.append(v)
    return violations
