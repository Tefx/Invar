"""
Entry point detection for framework callbacks.

DX-23: Detects entry points (Flask routes, Typer commands, pytest fixtures, etc.)
that are exempt from Result[T, E] requirement but must remain thin.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast
import re
import tokenize
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

# DX-22: Unified escape hatch pattern: # @invar:allow <rule>: <reason>
INVAR_ALLOW_PATTERN = re.compile(r"#\s*@invar:allow\s+(\w+)\s*:\s*(.+)")


@post(lambda result: result >= 0)  # Escape hatch count is non-negative
def count_escape_hatches(source: str) -> int:
    """
    Count @invar:allow markers in source code (DX-31).

    Uses tokenize to only match real comments, not strings/docstrings (DX-33 Option C).
    Used by check_review_suggested to trigger review when escape count >= 3.

    Examples:
        >>> count_escape_hatches("")
        0
        >>> count_escape_hatches("# @invar:allow rule: reason")
        1
        >>> source = '''
        ... # @invar:allow rule1: reason1
        ... def foo(): pass
        ... # @invar:allow rule2: reason2
        ... def bar(): pass
        ... '''
        >>> count_escape_hatches(source)
        2
        >>> count_escape_hatches("regular comment # no marker")
        0
        >>> # DX-33 Option C: Strings containing the pattern should NOT match
        >>> count_escape_hatches('s = "# @invar:allow rule: reason"')
        0
    """
    return len(extract_escape_hatches(source))


@post(lambda result: all(len(t) == 3 for t in result))  # Returns (rule, reason, line) tuples
def extract_escape_hatches(source: str) -> list[tuple[str, str, int]]:
    """
    Extract @invar:allow markers with their reasons and line numbers (DX-33, DX-66).

    Uses tokenize to only match real comments, not strings/docstrings.
    Returns list of (rule, reason, line) tuples for cross-file analysis.

    Examples:
        >>> extract_escape_hatches("")
        []
        >>> extract_escape_hatches("# @invar:allow shell_result: API boundary")
        [('shell_result', 'API boundary', 1)]
        >>> source = '''
        ... # @invar:allow rule1: same reason
        ... # @invar:allow rule2: different reason
        ... '''
        >>> extract_escape_hatches(source)
        [('rule1', 'same reason', 2), ('rule2', 'different reason', 3)]
        >>> # DX-33 Option C: Strings containing the pattern should NOT match
        >>> extract_escape_hatches('suggestion = "# @invar:allow rule: reason"')
        []
    """
    results: list[tuple[str, str, int]] = []
    try:
        # Use iterator-based readline to avoid io.StringIO (forbidden in Core)
        lines = iter(source.splitlines(keepends=True))
        tokens = tokenize.generate_tokens(lambda: next(lines, ""))
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                match = INVAR_ALLOW_PATTERN.search(tok.string)
                if match:
                    # DX-66: tok.start[0] is the 1-based line number
                    results.append((match.group(1), match.group(2), tok.start[0]))
    except Exception:
        # Fall back to regex if tokenization fails - can't get line numbers
        # Return line 0 to indicate unknown position
        return [(r, reason, 0) for r, reason in INVAR_ALLOW_PATTERN.findall(source)]
    return results


@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
def is_entry_point(symbol: Symbol, source: str) -> bool:
    """
    Check if a symbol is a framework entry point.

    Entry points are functions decorated with framework-specific decorators
    (Flask routes, Typer commands, etc.) that cannot return Result[T, E]
    because the framework expects specific return types.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="index", kind=SymbolKind.FUNCTION, line=3, end_line=5)
        >>> source = '''
        ... @app.route("/")
        ... def index():
        ...     return "Hello"
        ... '''
        >>> is_entry_point(sym, source)
        True

        >>> sym2 = Symbol(name="load_file", kind=SymbolKind.FUNCTION, line=2, end_line=4)
        >>> source2 = '''
        ... def load_file(path: str) -> Result[str, str]:
        ...     return Success(path.read_text())
        ... '''
        >>> is_entry_point(sym2, source2)
        False

        >>> # Explicit marker
        >>> sym3 = Symbol(name="handler", kind=SymbolKind.FUNCTION, line=3, end_line=5)
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



@post(lambda result: isinstance(result, str))
def _decorator_to_string(decorator: ast.AST) -> str:
    """
    Convert AST decorator node to string representation for matching.

    Examples:
        >>> import ast
        >>> tree = ast.parse("@app.route('/')\\ndef f(): pass")
        >>> func = tree.body[0]
        >>> _decorator_to_string(func.decorator_list[0])
        'app.route'
    """
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        parts = []
        node = decorator
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))
    elif isinstance(decorator, ast.Call):
        return _decorator_to_string(decorator.func)
    return ""

@pre(lambda symbol, source: symbol is not None and isinstance(source, str))
@post(lambda result: isinstance(result, bool))
def _has_entry_decorator(symbol: Symbol, source: str) -> bool:
    """
    Check if symbol has a framework entry point decorator.

    Uses AST to check decorator nodes, avoiding false matches in strings.
    DX-33 Option C: Migrated from string matching to AST-based detection.

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="home", kind=SymbolKind.FUNCTION, line=2, end_line=4)
        >>> source = '''@app.route("/")
        ... def home():
        ...     pass
        ... '''
        >>> _has_entry_decorator(sym, source)
        True
        >>> # DX-33: Decorators in strings should NOT match
        >>> sym2 = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=2, end_line=4)
        >>> source2 = '''x = "@app.route('/')"
        ... def foo():
        ...     pass
        ... '''
        >>> _has_entry_decorator(sym2, source2)
        False
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    # Find the function definition at the symbol's line
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno == symbol.line and node.name == symbol.name:
                # Check decorators
                for decorator in node.decorator_list:
                    decorator_str = _decorator_to_string(decorator)
                    if decorator_str:
                        for pattern in ENTRY_POINT_DECORATORS:
                            if pattern in decorator_str or decorator_str.endswith(
                                "." + pattern.split(".")[-1]
                            ):
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


@pre(lambda symbol, source, rule: symbol is not None and isinstance(rule, str))
@post(lambda result: isinstance(result, bool))
def has_allow_marker(symbol: Symbol, source: str, rule: str) -> bool:
    """
    Check if symbol has an @invar:allow marker for a specific rule.

    DX-22: Unified escape hatch mechanism. Format:
        # @invar:allow <rule>: <reason>

    Examples:
        >>> from invar.core.models import Symbol, SymbolKind
        >>> sym = Symbol(name="handler", kind=SymbolKind.FUNCTION, line=3, end_line=20)
        >>> source = '''
        ... # @invar:allow entry_point_too_thick: Complex CLI parsing
        ... def handler():
        ...     pass
        ... '''
        >>> has_allow_marker(sym, source, "entry_point_too_thick")
        True
        >>> has_allow_marker(sym, source, "shell_result")
        False

        >>> sym2 = Symbol(name="api", kind=SymbolKind.FUNCTION, line=3, end_line=10)
        >>> source2 = '''
        ... # @invar:allow shell_result: Returns raw JSON for legacy API
        ... def api():
        ...     pass
        ... '''
        >>> has_allow_marker(sym2, source2, "shell_result")
        True
    """
    lines = source.splitlines()
    if not lines:
        return False

    # Look at lines before the function definition (up to 4 lines)
    start_line = max(0, symbol.line - 5)
    end_line = symbol.line

    context_lines = lines[start_line:end_line]

    for line in context_lines:
        match = INVAR_ALLOW_PATTERN.search(line)
        if match and match.group(1) == rule:
            return True

    return False
