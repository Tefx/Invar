"""
Dead export detection for Shell functions.

Identifies Shell functions that are never referenced elsewhere in the codebase.
Useful for identifying potentially unused API endpoints or dead code.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

from deal import post, pre

from invar.core.entry_points import has_allow_marker, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation


@pre(
    lambda file_infos, ref_counts, config: (
        all(isinstance(fi, FileInfo) for fi in file_infos)
        and all(
            isinstance(name, str) and isinstance(count, int) and count >= 0
            for name, count in ref_counts.items()
        )
        and isinstance(config, RuleConfig)
    )
)
@post(lambda result: all(v.rule == "dead_export" for v in result))
def check_dead_exports(
    file_infos: list[FileInfo], ref_counts: dict[str, int], config: RuleConfig
) -> list[Violation]:
    """
    Check for dead exports in Shell functions.

    Identifies Shell functions that are never referenced elsewhere.
    Only checks public functions (not starting with _).

    Exclusions:
    - Private functions (name.startswith("_"))
    - Dunder methods (name.startswith("__") and name.endswith("__"))
    - Entry points (framework callbacks detected by decorators)
    - Functions with @invar:allow dead_export: <reason> marker

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> # Case 1: No dead exports (referenced function)
        >>> sym1 = Symbol(name="used_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info1 = FileInfo(path="shell/api.py", lines=15, symbols=[sym1], is_shell=True)
        >>> ref_counts1 = {"shell/api.py::used_func": 3}
        >>> len(check_dead_exports([info1], ref_counts1, RuleConfig()))
        0

        >>> # Case 2: Dead export (unreferenced public function)
        >>> sym2 = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info2 = FileInfo(path="shell/api.py", lines=15, symbols=[sym2], is_shell=True)
        >>> ref_counts2 = {"shell/api.py::unused_func": 0}
        >>> violations2 = check_dead_exports([info2], ref_counts2, RuleConfig())
        >>> len(violations2)
        1
        >>> violations2[0].rule
        'dead_export'
        >>> violations2[0].severity
        <Severity.WARNING: 'warning'>

        >>> # Case 3: Private function (starts with _) - excluded
        >>> sym3 = Symbol(name="_helper", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info3 = FileInfo(path="shell/api.py", lines=15, symbols=[sym3], is_shell=True)
        >>> ref_counts3 = {}
        >>> len(check_dead_exports([info3], ref_counts3, RuleConfig()))
        0

        >>> # Case 4: Dunder method - excluded
        >>> sym4 = Symbol(name="__init__", kind=SymbolKind.METHOD, line=5, end_line=10)
        >>> info4 = FileInfo(path="shell/api.py", lines=15, symbols=[sym4], is_shell=True)
        >>> ref_counts4 = {}
        >>> len(check_dead_exports([info4], ref_counts4, RuleConfig()))
        0

        >>> # Case 4b: FUNCTION-kind dunder (e.g., module-level __init__) - excluded
        >>> sym4b = Symbol(name="__init__", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info4b = FileInfo(path="shell/api.py", lines=15, symbols=[sym4b], is_shell=True)
        >>> ref_counts4b = {}
        >>> len(check_dead_exports([info4b], ref_counts4b, RuleConfig()))
        0

        >>> # Case 5: Entry point (decorator) - excluded
        >>> sym5 = Symbol(name="index", kind=SymbolKind.FUNCTION, line=3, end_line=5)
        >>> source5 = '''
        ... @app.route("/")
        ... def index():
        ...     pass
        ... '''
        >>> info5 = FileInfo(path="shell/web.py", lines=10, symbols=[sym5], is_shell=True, source=source5)
        >>> len(check_dead_exports([info5], {}, RuleConfig()))
        0

        >>> # Case 6: @invar:allow marker - excluded
        >>> sym6 = Symbol(name="legacy_api", kind=SymbolKind.FUNCTION, line=3, end_line=10)
        >>> source6 = '''
        ... # @invar:allow dead_export: Legacy API used by external systems
        ... def legacy_api():
        ...     pass
        ... '''
        >>> info6 = FileInfo(path="shell/api.py", lines=15, symbols=[sym6], is_shell=True, source=source6)
        >>> len(check_dead_exports([info6], {"shell/api.py::legacy_api": 0}, RuleConfig()))
        0

        >>> # Case 7: Core file - excluded (only checks Shell)
        >>> sym7 = Symbol(name="public_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info7 = FileInfo(path="core/logic.py", lines=15, symbols=[sym7], is_core=True, is_shell=False)
        >>> ref_counts7 = {}
        >>> len(check_dead_exports([info7], ref_counts7, RuleConfig()))
        0

        >>> # Case 8: Multiple file_infos with mixed results
        >>> sym8a = Symbol(name="used", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info8a = FileInfo(path="shell/a.py", lines=10, symbols=[sym8a], is_shell=True)
        >>> sym8b = Symbol(name="dead", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info8b = FileInfo(path="shell/b.py", lines=10, symbols=[sym8b], is_shell=True)
        >>> ref_counts8 = {"shell/a.py::used": 2, "shell/b.py::dead": 0}
        >>> violations8 = check_dead_exports([info8a, info8b], ref_counts8, RuleConfig())
        >>> len(violations8)
        1
        >>> violations8[0].file
        'shell/b.py'
    """
    violations: list[Violation] = []

    for file_info in file_infos:
        # Only check Shell files
        if not file_info.is_shell:
            continue

        source = file_info.source or ""

        for symbol in file_info.symbols:
            # Only check functions
            if symbol.kind != SymbolKind.FUNCTION:
                continue

            # Skip dunder methods (e.g., __init__, __str__) - must check before private
            if symbol.name.startswith("__") and symbol.name.endswith("__"):
                continue

            # Skip private functions (start with _)
            if symbol.name.startswith("_"):
                continue

            # Skip entry points (framework callbacks)
            if is_entry_point(symbol, source):
                continue

            # Skip if has @invar:allow dead_export marker
            if has_allow_marker(symbol, source, "dead_export"):
                continue

            # Build reference key
            key = f"{file_info.path}::{symbol.name}"

            # Check if referenced (ref_count == 0 means dead export)
            ref_count = ref_counts.get(key, 0)
            if ref_count == 0:
                violations.append(
                    Violation(
                        rule="dead_export",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"Shell function '{symbol.name}' is never referenced",
                        suggestion="Remove unused function, or add: # @invar:allow dead_export: <reason>",
                    )
                )

    return violations
