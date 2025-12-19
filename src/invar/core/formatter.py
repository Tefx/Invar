"""
Output formatting for Perception (Phase 4) and Guard (Phase 8).

This module provides functions to format perception and guard output.
Supports both human-readable (Rich) and machine-readable (JSON) formats.

No I/O operations - returns formatted strings/dicts only.
"""

from __future__ import annotations

from deal import post, pre

from invar.core.models import GuardReport, PerceptionMap, Symbol, SymbolRefs, Violation


@pre(lambda perception_map, top_n=0: isinstance(perception_map, PerceptionMap))
def format_map_text(perception_map: PerceptionMap, top_n: int = 0) -> str:
    """
    Format perception map as plain text.

    Args:
        perception_map: The perception map to format
        top_n: If > 0, only show top N symbols by reference count

    Examples:
        >>> from invar.core.models import PerceptionMap
        >>> pm = PerceptionMap(project_root="/test", total_files=1, total_symbols=0)
        >>> "Project:" in format_map_text(pm)
        True
    """
    lines: list[str] = []
    lines.append(f"Project: {perception_map.project_root}")
    lines.append(f"Files: {perception_map.total_files}")
    lines.append(f"Symbols: {perception_map.total_symbols}")
    lines.append("")

    symbols = perception_map.symbols
    if top_n > 0:
        symbols = symbols[:top_n]

    if not symbols:
        lines.append("No symbols found.")
        return "\n".join(lines)

    # Group by reference count level
    hot = [s for s in symbols if s.ref_count > 10]
    warm = [s for s in symbols if 3 <= s.ref_count <= 10]
    cold = [s for s in symbols if s.ref_count < 3]

    for label, group, level in [("Hot (refs > 10)", hot, "hot"),
                                  ("Warm (refs 3-10)", warm, "warm"),
                                  ("Cold (refs < 3)", cold, "cold")]:
        if group:
            lines.append(f"=== {label} ===")
            for sr in group:
                lines.extend(_format_symbol_detail(sr, level=level))
            lines.append("")

    return "\n".join(lines)


@pre(lambda sr, level: isinstance(sr, SymbolRefs) and level in ("hot", "warm", "cold"))
@post(lambda result: all(isinstance(line, str) for line in result))
def _format_symbol_detail(sr: SymbolRefs, level: str) -> list[str]:
    """Format a single symbol with appropriate detail level."""
    lines: list[str] = []
    sym = sr.symbol
    sig = sym.signature or f"({sym.name})"

    if level == "hot":
        # Full detail: signature + docstring + contracts
        lines.append(f"  {sr.file_path}::{sym.name}{sig}  [refs: {sr.ref_count}]")
        if sym.docstring:
            first_line = sym.docstring.split("\n")[0].strip()
            if first_line:
                lines.append(f"    | {first_line}")
        if sym.contracts:
            for c in sym.contracts:
                lines.append(f"    | @{c.kind}: {c.expression}")
    elif level == "warm":
        # Medium: signature + contracts summary
        lines.append(f"  {sr.file_path}::{sym.name}{sig}  [refs: {sr.ref_count}]")
        if sym.contracts:
            kinds = [c.kind for c in sym.contracts]
            lines.append(f"    | contracts: {', '.join(kinds)}")
    else:
        # Minimal: name only
        lines.append(f"  {sr.file_path}::{sym.name}  [refs: {sr.ref_count}]")

    return lines


@pre(lambda perception_map: isinstance(perception_map, PerceptionMap))
def format_map_json(perception_map: PerceptionMap) -> dict:
    """
    Format perception map as JSON-serializable dict.

    Examples:
        >>> from invar.core.models import PerceptionMap
        >>> pm = PerceptionMap(project_root="/test", total_files=1, total_symbols=0)
        >>> d = format_map_json(pm)
        >>> d["project_root"]
        '/test'
    """
    return {
        "project_root": perception_map.project_root,
        "total_files": perception_map.total_files,
        "total_symbols": perception_map.total_symbols,
        "symbols": [_symbol_refs_to_dict(sr) for sr in perception_map.symbols],
    }


@pre(lambda sr: isinstance(sr, SymbolRefs))
@post(lambda result: "name" in result and "ref_count" in result)
def _symbol_refs_to_dict(sr: SymbolRefs) -> dict:
    """Convert SymbolRefs to dict."""
    sym = sr.symbol
    return {
        "file": sr.file_path,
        "name": sym.name,
        "kind": sym.kind.value,
        "line": sym.line,
        "signature": sym.signature,
        "ref_count": sr.ref_count,
        "docstring": sym.docstring,
        "contracts": [{"kind": c.kind, "expression": c.expression} for c in sym.contracts],
    }


@pre(lambda symbol, file_path: isinstance(symbol, Symbol))
def format_signature(symbol: Symbol, file_path: str) -> str:
    """
    Format a single symbol signature.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5,
        ...     signature="(x: int) -> int")
        >>> format_signature(sym, "test.py")
        'test.py::foo(x: int) -> int'
    """
    sig = symbol.signature or ""
    return f"{file_path}::{symbol.name}{sig}"


@pre(lambda symbols, file_path: isinstance(symbols, list))
def format_signatures_text(symbols: list[Symbol], file_path: str) -> str:
    """
    Format multiple signatures as text.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> format_signatures_text([sym], "test.py")
        'test.py::foo'
    """
    lines = [format_signature(sym, file_path) for sym in symbols]
    return "\n".join(lines)


@pre(lambda symbols, file_path: isinstance(symbols, list))
def format_signatures_json(symbols: list[Symbol], file_path: str) -> dict:
    """
    Format signatures as JSON-serializable dict.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> d = format_signatures_json([sym], "test.py")
        >>> d["file"]
        'test.py'
    """
    return {
        "file": file_path,
        "symbols": [
            {
                "name": sym.name,
                "kind": sym.kind.value,
                "line": sym.line,
                "signature": sym.signature,
                "docstring": sym.docstring,
                "contracts": [{"kind": c.kind, "expression": c.expression} for c in sym.contracts],
            }
            for sym in symbols
        ],
    }


# Phase 8.2: Agent-mode formatting


@pre(lambda report: isinstance(report, GuardReport))
def format_guard_agent(report: GuardReport) -> dict:
    """
    Format Guard report for Agent consumption (Phase 8.2).

    Provides structured output with actionable fix instructions.

    Examples:
        >>> from invar.core.models import GuardReport, Violation, Severity
        >>> report = GuardReport(files_checked=1)
        >>> v = Violation(rule="missing_contract", severity=Severity.WARNING,
        ...     file="test.py", line=10, message="Function 'foo' has no contract",
        ...     suggestion="Add: @pre(lambda x: x >= 0)")
        >>> report.add_violation(v)
        >>> d = format_guard_agent(report)
        >>> d["status"]
        'passed'
        >>> len(d["fixes"])
        1
    """
    return {
        "status": "passed" if report.passed else "failed",
        "summary": {
            "files_checked": report.files_checked,
            "errors": report.errors,
            "warnings": report.warnings,
            "infos": report.infos,
        },
        "fixes": [_violation_to_fix(v) for v in report.violations],
    }


@pre(lambda v: isinstance(v, Violation))
def _violation_to_fix(v: Violation) -> dict:
    """Convert a Violation to an Agent-friendly fix instruction."""
    fix_info = _parse_suggestion(v.suggestion, v.rule) if v.suggestion else None
    return {
        "file": v.file,
        "line": v.line,
        "rule": v.rule,
        "severity": v.severity.value,
        "message": v.message,
        "fix": fix_info,
    }


@pre(lambda suggestion, rule: suggestion is None or isinstance(suggestion, str))
def _parse_suggestion(suggestion: str | None, rule: str) -> dict | None:
    """Parse suggestion string into structured fix instruction."""
    if not suggestion:
        return None

    # Parse "Add: @pre(...)" style suggestions
    if suggestion.startswith("Add: "):
        return {"action": "add_decorator", "code": suggestion[5:]}

    # Parse "Replace with: @pre(...)" style suggestions
    if suggestion.startswith("Replace with: "):
        return {"action": "replace_decorator", "code": suggestion[14:]}

    # Parse "Replace with business logic: @pre(...)" style
    if suggestion.startswith("Replace with business logic: "):
        return {"action": "replace_decorator", "code": suggestion[29:]}

    # Default: return as instruction text
    return {"action": "manual", "instruction": suggestion}
