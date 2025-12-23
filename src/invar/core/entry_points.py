"""
Entry point detection for framework callbacks.

DX-23: Detects entry points (Flask routes, Typer commands, pytest fixtures, etc.)
that are exempt from Result[T, E] requirement but must remain thin.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from deal import post, pre

if TYPE_CHECKING:
    from invar.core.models import Symbol


# Decorator patterns that indicate framework entry points
# These functions interface with external frameworks and cannot return Result
ENTRY_POINT_DECORATORS: frozenset[str] = frozenset([
    # Web frameworks - Flask
    "app.route",
    "app.get",
    "app.post",
    "app.put",
    "app.delete",
    "app.patch",
    "blueprint.route",
    "bp.route",
    # Web frameworks - FastAPI
    "router.get",
    "router.post",
    "router.put",
    "router.delete",
    "router.patch",
    "api_router.get",
    "api_router.post",
    "api_router.put",
    "api_router.delete",
    # CLI frameworks - Typer
    "app.command",
    "app.callback",
    "typer.command",
    # CLI frameworks - Click
    "click.command",
    "click.group",
    "cli.command",
    # Testing - pytest
    "pytest.fixture",
    "fixture",
    # Event handlers
    "on_event",
    "app.on_event",
    "middleware",
    "app.middleware",
    # Django
    "admin.register",
    "receiver",
])

# Explicit marker comment for edge cases
ENTRY_MARKER_PATTERN = re.compile(r"#\s*@shell:entry\b")


@pre(lambda symbol, source: symbol is not None)
@post(lambda result: isinstance(result, bool))
def is_entry_point(symbol: Symbol, source: str) -> bool:
    """
    Check if a symbol is a framework entry point.

    Entry points are functions decorated with framework-specific decorators
    (Flask routes, Typer commands, etc.) that cannot return Result[T, E]
    because the framework expects specific return types.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="index", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> source = '''
        ... @app.route("/")
        ... def index():
        ...     return "Hello"
        ... '''
        >>> is_entry_point(sym, source)
        True

        >>> sym2 = Symbol(name="load_file", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> source2 = '''
        ... def load_file(path: str) -> Result[str, str]:
        ...     return Success(path.read_text())
        ... '''
        >>> is_entry_point(sym2, source2)
        False

        >>> # Explicit marker
        >>> sym3 = Symbol(name="handler", kind=SymbolKind.FUNCTION, line=3, end_line=8)
        >>> source3 = '''
        ... # @shell:entry - Legacy callback
        ... def handler(data):
        ...     return process(data)
        ... '''
        >>> is_entry_point(sym3, source3)
        True
    """
    # Check decorator patterns
    if _has_entry_decorator(symbol, source):
        return True

    # Check explicit marker
    return _has_entry_marker(symbol, source)


@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
def _has_entry_decorator(symbol: Symbol, source: str) -> bool:
    """
    Check if symbol has a framework entry point decorator.

    Looks at the source code above the function definition.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="home", kind=SymbolKind.FUNCTION, line=3, end_line=6)
        >>> source = '''@app.route("/")
        ... def home():
        ...     pass
        ... '''
        >>> _has_entry_decorator(sym, source)
        True
    """
    # Get source lines
    lines = source.splitlines()
    if not lines:
        return False

    # Look at lines before the function definition (decorators are above)
    # We check up to 5 lines above the function for decorators
    start_line = max(0, symbol.line - 6)
    end_line = symbol.line  # Line numbers are 1-indexed, so line-1 = index

    context_lines = lines[start_line:end_line]
    context = "\n".join(context_lines)

    # Check each known decorator pattern
    for pattern in ENTRY_POINT_DECORATORS:
        # Match @pattern or @something.pattern
        if f"@{pattern}" in context:
            return True
        # Also match partial patterns (e.g., "route" matches "app.route")
        if "." in pattern:
            base = pattern.split(".")[-1]
            if f".{base}(" in context or f".{base}\n" in context:
                return True

    return False


@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
def _has_entry_marker(symbol: Symbol, source: str) -> bool:
    """
    Check if symbol has an explicit entry point marker comment.

    Looks for: # @shell:entry

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="callback", kind=SymbolKind.FUNCTION, line=3, end_line=6)
        >>> source = '''
        ... # @shell:entry - Custom framework callback
        ... def callback():
        ...     pass
        ... '''
        >>> _has_entry_marker(sym, source)
        True

        >>> sym2 = Symbol(name="regular", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> source2 = '''def regular(): pass'''
        >>> _has_entry_marker(sym2, source2)
        False
    """
    lines = source.splitlines()
    if not lines:
        return False

    # Look at lines before the function definition
    start_line = max(0, symbol.line - 4)
    end_line = symbol.line

    context_lines = lines[start_line:end_line]
    context = "\n".join(context_lines)

    return bool(ENTRY_MARKER_PATTERN.search(context))


@pre(lambda symbol: symbol is not None)
@post(lambda result: isinstance(result, int) and result >= 0)
def get_symbol_lines(symbol: Symbol) -> int:
    """
    Get the number of lines in a symbol.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=10)
        >>> get_symbol_lines(sym)
        10
        >>> sym2 = Symbol(name="bar", kind=SymbolKind.FUNCTION, line=5, end_line=5)
        >>> get_symbol_lines(sym2)
        1
    """
    return max(1, symbol.end_line - symbol.line + 1)
