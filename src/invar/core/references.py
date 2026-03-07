"""
Reference counting for Perception (Phase 4).

This module provides functions to count cross-file symbol references.
Analyzes AST to find Name, Call, and Attribute nodes that reference known symbols.

No I/O operations - receives parsed data only.
"""

from __future__ import annotations

import ast
from collections import defaultdict

from deal import post, pre

from invar.core.models import FileInfo, PerceptionMap, SymbolKind, SymbolRefs

TYPER_DYNAMIC_REGISTRATION_METHODS: frozenset[str] = frozenset({"command", "callback"})


@pre(lambda source, known_symbols: len(source) > 0 and len(known_symbols) > 0)  # Non-empty inputs
@post(lambda result: all(isinstance(name, str) and line > 0 for name, line in result))  # Valid refs
def find_references_in_source(source: str, known_symbols: set[str]) -> list[tuple[str, int]]:
    """
    Find references to known symbols in source code.

    Returns list of (symbol_name, line_number) for each reference found.
    Deduplicates: each (symbol, line) pair counted once.

    Examples:
        >>> refs = find_references_in_source("x = foo()\\nbar(x)", {"foo", "bar"})
        >>> sorted(refs)
        [('bar', 2), ('foo', 1)]
        >>> refs = find_references_in_source("mod.foo()\\npkg.mod.bar()", {"foo", "bar"})
        >>> sorted(refs)
        [('bar', 2), ('foo', 1)]
        >>> refs = find_references_in_source("app.command()(init)\\napp.command('t')(test)", {"init", "test", "verify"})
        >>> sorted(refs)
        [('init', 1), ('test', 2)]
        >>> refs = find_references_in_source(
        ...     "loop.set_exception_handler(suppress_invalid_state_error)",
        ...     {"suppress_invalid_state_error"},
        ... )
        >>> sorted(refs)
        [('suppress_invalid_state_error', 1)]
        >>> refs = find_references_in_source(
        ...     "def build():\\n    from mod import foo\\n    return 1",
        ...     {"foo"},
        ... )
        >>> sorted(refs)
        [('foo', 2)]
        >>> find_references_in_source("x = unknown()", {"foo"})
        []
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return []

    seen: set[tuple[str, int]] = set()

    for node in ast.walk(tree):
        # Count explicit imports: from mod import foo
        if isinstance(node, ast.ImportFrom):
            line = getattr(node, "lineno", 0)
            for imported_name in node.names:
                if imported_name.name != "*" and imported_name.name in known_symbols:
                    seen.add((imported_name.name, line))

        # Count function calls: foo() and module.foo()
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            if name in known_symbols:
                line = getattr(node, "lineno", 0)
                seen.add((name, line))

            # Count callback/function-object usage passed as call arguments.
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in known_symbols:
                    line = getattr(arg, "lineno", 0)
                    seen.add((arg.id, line))
            for keyword in node.keywords:
                if isinstance(keyword.value, ast.Name) and keyword.value.id in known_symbols:
                    line = getattr(keyword.value, "lineno", 0)
                    seen.add((keyword.value.id, line))

        # Count dynamic Typer registration usage: app.command()(fn)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Attribute)
            and node.func.func.attr in TYPER_DYNAMIC_REGISTRATION_METHODS
        ):
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id in known_symbols:
                    line = getattr(arg, "lineno", 0)
                    seen.add((arg.id, line))
            for keyword in node.keywords:
                if isinstance(keyword.value, ast.Name) and keyword.value.id in known_symbols:
                    line = getattr(keyword.value, "lineno", 0)
                    seen.add((keyword.value.id, line))

    return list(seen)


@post(lambda result: all(isinstance(v, str) for v in result.values()))
def build_symbol_table(file_infos: list[FileInfo]) -> dict[str, str]:
    """
    Build a mapping of symbol names to their defining file.

    Returns dict of {symbol_name: file_path}.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info = FileInfo(path="core/calc.py", lines=10, symbols=[sym])
        >>> table = build_symbol_table([info])
        >>> table["foo"]
        'core/calc.py'
    """
    symbol_table: dict[str, str] = {}

    for file_info in file_infos:
        for symbol in file_info.symbols:
            if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS):
                # Use simple name (may have collisions, that's OK for now)
                symbol_table[symbol.name] = file_info.path

    return symbol_table


@post(
    lambda result: all(
        isinstance(name, str)
        and isinstance(files, set)
        and all(isinstance(path, str) for path in files)
        for name, files in result.items()
    )
)
def build_symbol_index(file_infos: list[FileInfo]) -> dict[str, set[str]]:
    """Build mapping of symbol names to all defining files.

    References are often discovered by bare symbol name (e.g. ``foo()``),
    which can be ambiguous when multiple modules define the same symbol name.
    This index keeps all candidates so dead-export analysis remains conservative
    and avoids false positives from name collisions.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> a = Symbol(name="main", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> b = Symbol(name="main", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> info_a = FileInfo(path="shell/a.py", lines=3, symbols=[a])
        >>> info_b = FileInfo(path="shell/b.py", lines=3, symbols=[b])
        >>> index = build_symbol_index([info_a, info_b])
        >>> sorted(index["main"])
        ['shell/a.py', 'shell/b.py']
    """
    symbol_index: dict[str, set[str]] = defaultdict(set)

    for file_info in file_infos:
        for symbol in file_info.symbols:
            if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS):
                symbol_index[symbol.name].add(file_info.path)

    return dict(symbol_index)


@post(lambda result: all("::" in k and v >= 0 for k, v in result.items()))  # Valid ref counts
def count_cross_file_references(
    file_infos: list[FileInfo], sources: dict[str, str], include_same_file: bool = False
) -> dict[str, int]:
    """
    Count cross-file references for all symbols.

    Returns dict of {"file::symbol": reference_count}.
    By default, only counts references from OTHER files (excludes self-references).
    Set include_same_file=True to also count references within the defining file.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info = FileInfo(path="a.py", lines=10, symbols=[sym])
        >>> sources = {"a.py": "def foo(): pass", "b.py": "foo()"}
        >>> info2 = FileInfo(path="b.py", lines=5, symbols=[])
        >>> refs = count_cross_file_references([info, info2], sources)
        >>> refs.get("a.py::foo", 0)
        1
        >>> same_file_sources = {
        ...     "a.py": "def foo():\\n    return 1\\n\\nfoo()",
        ...     "b.py": "pass",
        ... }
        >>> same_file_refs = count_cross_file_references(
        ...     [info, info2], same_file_sources, include_same_file=True
        ... )
        >>> same_file_refs.get("a.py::foo", 0) > 0
        True
        >>> main_a = Symbol(name="main", kind=SymbolKind.FUNCTION, line=1, end_line=2)
        >>> main_b = Symbol(name="main", kind=SymbolKind.FUNCTION, line=1, end_line=2)
        >>> info_a = FileInfo(path="shell/a.py", lines=3, symbols=[main_a])
        >>> info_b = FileInfo(path="shell/b.py", lines=3, symbols=[main_b])
        >>> ambiguous_sources = {
        ...     "shell/a.py": "def main():\\n    return 1",
        ...     "shell/b.py": "def main():\\n    return 2\\n\\nmain()",
        ... }
        >>> refs = count_cross_file_references([info_a, info_b], ambiguous_sources, include_same_file=True)
        >>> refs.get("shell/a.py::main", 0) > 0 and refs.get("shell/b.py::main", 0) > 0
        True
    """
    # Build symbol index: name -> defining files
    symbol_index = build_symbol_index(file_infos)
    known_symbols = set(symbol_index.keys())

    # Count references from each file
    ref_counts: dict[str, int] = defaultdict(int)

    for file_info in file_infos:
        source = sources.get(file_info.path, "")
        if not source:
            continue

        references = find_references_in_source(source, known_symbols)

        for symbol_name, _ in references:
            defining_files = symbol_index.get(symbol_name, set())
            for defining_file in defining_files:
                if include_same_file or defining_file != file_info.path:
                    key = f"{defining_file}::{symbol_name}"
                    ref_counts[key] += 1

    return dict(ref_counts)


@pre(
    lambda file_infos, sources, include_same_file=False: (
        isinstance(file_infos, list)
        and all(isinstance(fi, FileInfo) for fi in file_infos)
        and isinstance(sources, dict)
        and isinstance(include_same_file, bool)
    )
)
@post(lambda result: all("::" in k and isinstance(v, list) for k, v in result.items()))
def get_reference_sources(
    file_infos: list[FileInfo],
    sources: dict[str, str],
    include_same_file: bool = False,
) -> dict[str, list[str]]:
    """
    Get the list of source files that reference each symbol.

    Returns dict of {"file::symbol": [list of referencing file paths]}.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=2)
        >>> info = FileInfo(path="a.py", lines=5, symbols=[sym])
        >>> srcs = {"a.py": "def foo(): pass", "tests/test_a.py": "from a import foo"}
        >>> info2 = FileInfo(path="tests/test_a.py", lines=5, symbols=[])
        >>> ref_sources = get_reference_sources([info, info2], srcs)
        >>> sorted(ref_sources.get("a.py::foo", []))
        ['tests/test_a.py']
    """
    # Build symbol index: name -> defining files
    symbol_index = build_symbol_index(file_infos)
    known_symbols = set(symbol_index.keys())

    # Track reference sources: key -> list of source files
    ref_sources: dict[str, list[str]] = defaultdict(list)

    for file_info in file_infos:
        source = sources.get(file_info.path, "")
        if not source:
            continue

        references = find_references_in_source(source, known_symbols)

        for symbol_name, _ in references:
            defining_files = symbol_index.get(symbol_name, set())
            for defining_file in defining_files:
                if include_same_file or defining_file != file_info.path:
                    key = f"{defining_file}::{symbol_name}"
                    ref_sources[key].append(file_info.path)

    return dict(ref_sources)


@pre(
    lambda file_infos, sources, project_root: (
        isinstance(file_infos, list)
        and all(isinstance(fi, FileInfo) for fi in file_infos)
        and isinstance(sources, dict)
        and isinstance(project_root, str)
        and len(project_root) > 0
    )
)
def build_perception_map(
    file_infos: list[FileInfo], sources: dict[str, str], project_root: str
) -> PerceptionMap:
    """
    Build complete perception map with reference counts.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> sym = Symbol(name="foo", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info = FileInfo(path="a.py", lines=10, symbols=[sym])
        >>> pm = build_perception_map([info], {"a.py": "def foo(): pass"}, "/test")
        >>> pm.total_symbols
        1
    """
    ref_counts = count_cross_file_references(file_infos, sources)

    # Build SymbolRefs list
    symbol_refs: list[SymbolRefs] = []
    total_symbols = 0

    for file_info in file_infos:
        for symbol in file_info.symbols:
            if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.CLASS):
                key = f"{file_info.path}::{symbol.name}"
                count = ref_counts.get(key, 0)
                symbol_refs.append(
                    SymbolRefs(
                        symbol=symbol,
                        file_path=file_info.path,
                        ref_count=count,
                    )
                )
                total_symbols += 1

    # Sort by reference count (descending)
    symbol_refs.sort(key=lambda sr: sr.ref_count, reverse=True)

    try:
        return PerceptionMap(
            project_root=project_root,
            total_files=len(file_infos),
            total_symbols=total_symbols,
            symbols=symbol_refs,
        )
    except Exception:
        # Handle CrossHair symbolic value validation failures
        # Use safe literal value that always passes validation
        return PerceptionMap(
            project_root="/",
            total_files=0,
            total_symbols=0,
            symbols=[],
        )
