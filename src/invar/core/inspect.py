"""
File inspection for USBV Understand step (Phase 9.2 P14).

Provides context about a file to help agents understand existing patterns
before making changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from deal import post, pre

from invar.core.models import SymbolKind
from invar.core.parser import parse_source


@dataclass
class FileContext:
    """
    Context information about a file for inspection.

    Examples:
        >>> ctx = FileContext(
        ...     path="src/core/calc.py",
        ...     lines=150,
        ...     max_lines=500,
        ...     functions_total=5,
        ...     functions_with_contracts=3,
        ...     contract_examples=["@pre(lambda x: x > 0)", "@post(lambda result: result is not None)"]
        ... )
        >>> ctx.percentage
        30
        >>> ctx.has_patterns
        True
    """

    path: str
    lines: int
    max_lines: int
    functions_total: int
    functions_with_contracts: int
    contract_examples: list[str]

    @property
    @post(lambda result: result >= 0)
    def percentage(self) -> int:
        """Percentage of max lines used.

        >>> ctx = FileContext("x.py", 400, 500, 10, 5, [])
        >>> ctx.percentage
        80
        """
        if self.max_lines <= 0 or self.lines < 0:
            return 0
        return int(self.lines / self.max_lines * 100)

    @property
    @post(lambda result: isinstance(result, bool))
    def has_patterns(self) -> bool:
        """Whether there are contract patterns to show.

        >>> FileContext("x.py", 100, 500, 5, 2, ["@pre"]).has_patterns
        True
        >>> FileContext("x.py", 100, 500, 5, 2, []).has_patterns
        False
        """
        return len(self.contract_examples) > 0


@pre(lambda source, path, max_lines: isinstance(source, str) and len(path) > 0 and max_lines > 0)
def analyze_file_context(source: str, path: str, max_lines: int = 500) -> FileContext:
    """
    Analyze a source file to extract context for inspection.

    Examples:
        >>> source = '''
        ... from deal import pre
        ... @pre(lambda x: x > 0)
        ... def positive(x: int) -> int:
        ...     return x * 2
        ... def no_contract(y):
        ...     return y
        ... '''
        >>> ctx = analyze_file_context(source.strip(), "test.py", 500)
        >>> ctx.functions_total
        2
        >>> ctx.functions_with_contracts
        1
        >>> "@pre(lambda x: x > 0)" in ctx.contract_examples
        True
    """
    lines = source.count("\n") + 1

    # Parse to find functions (handle malformed input gracefully)
    try:
        file_info = parse_source(source, path)
    except (TypeError, ValueError):
        file_info = None

    if file_info is None:
        return FileContext(
            path=path,
            lines=lines,
            max_lines=max_lines,
            functions_total=0,
            functions_with_contracts=0,
            contract_examples=[],
        )

    functions = [s for s in file_info.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)]

    # Find contract patterns in source
    contract_examples = _extract_contract_patterns(source)

    # Count functions with contracts (Symbol.contracts is non-empty)
    functions_with_contracts = sum(1 for f in functions if len(f.contracts) > 0)

    return FileContext(
        path=path,
        lines=lines,
        max_lines=max_lines,
        functions_total=len(functions),
        functions_with_contracts=functions_with_contracts,
        contract_examples=contract_examples[:3],  # Limit to 3 examples
    )


@post(lambda result: isinstance(result, list))
def _extract_contract_patterns(source: str) -> list[str]:
    """
    Extract @pre/@post patterns from source.

    Examples:
        >>> src = "@pre(lambda x: x > 0)\\n@post(lambda r: r is not None)"
        >>> patterns = _extract_contract_patterns(src)
        >>> len(patterns)
        2
        >>> "@pre(lambda x: x > 0)" in patterns
        True
    """
    patterns = []

    # Match @pre(...) and @post(...) decorators
    for match in re.finditer(r"@(pre|post)\([^)]+\)", source):
        pattern = match.group(0)
        # Simplify if too long
        if len(pattern) > 60:
            pattern = pattern[:57] + "..."
        if pattern not in patterns:
            patterns.append(pattern)

    return patterns
