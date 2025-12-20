"""Rule engine for Guard. Rules check FileInfo and produce Violations. No I/O."""

from __future__ import annotations

from typing import Callable

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation
from invar.core.contracts import (
    check_empty_contracts, check_param_mismatch, check_partial_contract,
    check_redundant_type_contracts, check_semantic_tautology,
)
from invar.core.purity import check_impure_calls, check_internal_imports
from invar.core.suggestions import format_suggestion_for_violation
from invar.core.utils import get_excluded_rules
from invar.core.extraction import format_extraction_hint

# P17: Pure alternatives for forbidden imports (module → suggestion)
FORBIDDEN_IMPORT_ALTERNATIVES: dict[str, str] = {
    "os": "Inject paths as strings", "sys": "Pass sys.argv as parameter",
    "pathlib": "Use string operations", "subprocess": "Move to Shell",
    "shutil": "Move to Shell", "io": "Pass content as str/bytes",
    "socket": "Move to Shell", "requests": "Move HTTP to Shell",
    "urllib": "Move to Shell", "datetime": "Inject now as parameter",
    "random": "Inject random values", "open": "Shell reads, Core processes",
}

# Type alias for rule functions
RuleFunc = Callable[[FileInfo, RuleConfig], list[Violation]]


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_file_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if file exceeds maximum line count or warning threshold.

    P18: Shows function groups in size warnings to help agents decide what to extract.
    P25: Shows extractable groups with dependencies for warnings.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> check_file_size(FileInfo(path="ok.py", lines=100), RuleConfig())
        []
        >>> len(check_file_size(FileInfo(path="big.py", lines=600), RuleConfig()))
        1
        >>> # P8: Warning at 80% threshold (400 lines when max is 500)
        >>> vs = check_file_size(FileInfo(path="growing.py", lines=420), RuleConfig())
        >>> len(vs) == 1 and vs[0].rule == "file_size_warning"
        True
    """
    violations: list[Violation] = []
    # P18: Show top 5 largest functions in size warnings
    funcs = sorted([(s.name, s.end_line - s.line + 1) for s in file_info.symbols
                    if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)],
                   key=lambda x: -x[1])[:5]
    func_hint = f" Functions: {', '.join(f'{n}({sz}L)' for n, sz in funcs)}" if funcs else ""

    # P25: Get extractable groups with dependencies
    extraction_hint = format_extraction_hint(file_info)

    if file_info.lines > config.max_file_lines:
        suggestion = "Split into smaller modules."
        if extraction_hint:
            suggestion += f"\nExtractable groups:\n{extraction_hint}"
        elif func_hint:
            suggestion += func_hint
        violations.append(
            Violation(
                rule="file_size",
                severity=Severity.ERROR,
                file=file_info.path,
                line=None,
                message=f"File has {file_info.lines} lines (max: {config.max_file_lines})",
                suggestion=suggestion,
            )
        )
    # Phase 9 P8: Warning at configurable threshold (default 80%)
    elif config.size_warning_threshold > 0:
        threshold_lines = int(config.max_file_lines * config.size_warning_threshold)
        if file_info.lines >= threshold_lines:
            pct = int(file_info.lines / config.max_file_lines * 100)
            suggestion = "Consider splitting before reaching limit."
            if extraction_hint:
                suggestion += f"\nExtractable groups:\n{extraction_hint}"
            elif func_hint:
                suggestion += func_hint
            violations.append(
                Violation(
                    rule="file_size_warning",
                    severity=Severity.WARNING,
                    file=file_info.path,
                    line=None,
                    message=f"File has {file_info.lines} lines ({pct}% of {config.max_file_lines} limit)",
                    suggestion=suggestion,
                )
            )

    return violations


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_function_size(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check if any function exceeds maximum line count.

    When use_code_lines is True, uses code_lines (excluding docstring).
    When exclude_doctest_lines is True, subtracts doctest lines from count.

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
            total_lines = symbol.end_line - symbol.line + 1
            # Calculate effective line count based on config
            if config.use_code_lines and symbol.code_lines is not None:
                func_lines = symbol.code_lines
                line_type = "code lines"
            else:
                func_lines = total_lines
                line_type = "lines"
            # Optionally exclude doctest lines
            if config.exclude_doctest_lines and symbol.doctest_lines > 0:
                func_lines -= symbol.doctest_lines
                line_type = f"{line_type} (excl. doctest)"

            if func_lines > config.max_function_lines:
                # P19: Show breakdown if doctest lines exist
                if symbol.doctest_lines > 0 and not config.exclude_doctest_lines:
                    code_only = total_lines - symbol.doctest_lines
                    breakdown = f" ({code_only} code + {symbol.doctest_lines} doctest)"
                    suggestion = f"Extract helper or set exclude_doctest_lines=true{breakdown}"
                else:
                    suggestion = "Extract helper functions"
                violations.append(
                    Violation(
                        rule="function_size",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"Function '{symbol.name}' has {func_lines} {line_type} (max: {config.max_function_lines})",
                        suggestion=suggestion,
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
        # Check all functions and methods - agent needs contracts everywhere
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            if not symbol.contracts:
                kind_name = "Method" if symbol.kind == SymbolKind.METHOD else "Function"
                suggestion = format_suggestion_for_violation(symbol, "missing_contract")
                violations.append(
                    Violation(
                        rule="missing_contract",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"{kind_name} '{symbol.name}' has no @pre or @post contract",
                        suggestion=suggestion,
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
        # Only public functions/methods require doctests (private can skip)
        # For methods, check if method name (after dot) starts with _
        name_part = symbol.name.split(".")[-1] if "." in symbol.name else symbol.name
        is_public = not name_part.startswith("_")
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) and is_public and symbol.contracts and not symbol.has_doctest:
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


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
def check_shell_result(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """
    Check that Shell functions with return values use Result[T, E].

    Skips: functions returning None (CLI entry points).

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
        # Skip generators (Iterator/Generator) - acceptable exception per protocol
        if "Iterator[" in symbol.signature or "Generator[" in symbol.signature:
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
        >>> len(get_all_rules()) >= 5
        True
    """
    return [check_file_size, check_function_size, check_forbidden_imports, check_contracts,
            check_doctests, check_shell_result, check_internal_imports, check_impure_calls,
            check_empty_contracts, check_semantic_tautology, check_redundant_type_contracts,
            check_param_mismatch, check_partial_contract]


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


@pre(lambda file_info, config: isinstance(file_info, FileInfo))
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
