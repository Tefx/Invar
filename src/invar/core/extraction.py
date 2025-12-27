"""Extraction analysis for Guard (Phase 11 P25). No I/O operations.

Analyzes function call relationships to suggest extractable groups
when files approach size limits.
"""

from __future__ import annotations

from deal import post, pre

from invar.core.models import FileInfo, Symbol, SymbolKind


@post(lambda result: all(k in result for k in result))  # Bidirectional graph
def _build_call_graph(funcs: dict[str, Symbol]) -> dict[str, set[str]]:
    """Build bidirectional call graph for function grouping.

    >>> from invar.core.models import Symbol, SymbolKind
    >>> s = Symbol(name="a", kind=SymbolKind.FUNCTION, line=1, end_line=5, function_calls=["b"])
    >>> g = _build_call_graph({"a": s})
    >>> "a" in g
    True
    """
    func_names = set(funcs.keys())
    graph: dict[str, set[str]] = {name: set() for name in func_names}

    for name, sym in funcs.items():
        for called in sym.function_calls:
            if called in func_names:
                graph[name].add(called)
                graph[called].add(name)
    return graph


@pre(lambda start, graph, visited: start and start in graph)  # Start must exist in graph
@post(lambda result: len(result) >= 1 or not result)  # At least 1 if found, else empty
def _find_connected_component(start: str, graph: dict[str, set[str]], visited: set[str]) -> list[str]:
    """BFS to find all functions connected to start.

    >>> g = {"a": {"b"}, "b": {"a"}, "c": set()}
    >>> v = set()
    >>> _find_connected_component("a", g, v)
    ['a', 'b']
    """
    component: list[str] = []
    queue = [start]
    while queue:
        current = queue.pop(0)
        if current in visited or current not in graph:
            continue
        visited.add(current)
        component.append(current)
        queue.extend(n for n in graph[current] if n not in visited)
    return component


@post(lambda result: all("functions" in g and "lines" in g for g in result))
def find_extractable_groups(file_info: FileInfo) -> list[dict]:
    """
    Find groups of related functions that could be extracted together.

    Uses function call relationships to identify connected components.
    Returns groups sorted by total lines (largest first).

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> s1 = Symbol(name="main", kind=SymbolKind.FUNCTION, line=1, end_line=20,
        ...     function_calls=["helper"])
        >>> s2 = Symbol(name="helper", kind=SymbolKind.FUNCTION, line=21, end_line=30,
        ...     function_calls=[])
        >>> s3 = Symbol(name="unrelated", kind=SymbolKind.FUNCTION, line=31, end_line=40,
        ...     function_calls=[])
        >>> info = FileInfo(path="test.py", lines=40, symbols=[s1, s2, s3])
        >>> groups = find_extractable_groups(info)
        >>> len(groups)
        2
        >>> sorted(groups[0]["functions"])  # Largest group first
        ['helper', 'main']
        >>> groups[0]["lines"]
        30
    """
    funcs = {
        s.name: s for s in file_info.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
    }
    if not funcs:
        return []

    graph = _build_call_graph(funcs)
    visited: set[str] = set()
    groups: list[dict] = []

    for name in funcs:
        if name in visited:
            continue

        component = _find_connected_component(name, graph, visited)
        total_lines = sum(funcs[n].end_line - funcs[n].line + 1 for n in component)
        deps = _get_group_dependencies(component, funcs, file_info.imports)

        groups.append({
            "functions": sorted(component),
            "lines": total_lines,
            "dependencies": sorted(deps),
        })

    groups.sort(key=lambda g: -g["lines"])
    return groups


@pre(lambda func_names, funcs, file_imports: all(n in funcs for n in func_names if n))
@post(lambda result: isinstance(result, set))
def _get_group_dependencies(
    func_names: list[str],
    funcs: dict[str, Symbol],
    file_imports: list[str],
) -> set[str]:
    """Get external dependencies used by a group of functions.

    >>> from invar.core.models import Symbol, SymbolKind
    >>> s = Symbol(name="f", kind=SymbolKind.FUNCTION, line=1, end_line=5, internal_imports=["os"])
    >>> _get_group_dependencies(["f"], {"f": s}, ["os", "sys"])
    {'os'}
    """
    deps: set[str] = set()

    for name in func_names:
        if not name or name not in funcs:
            continue
        sym = funcs[name]
        # Add internal imports used by this function
        deps.update(sym.internal_imports)

    # Filter to only include actual imports from file
    # (some internal_imports might be from nested scopes)
    return deps.intersection(set(file_imports)) if file_imports else deps


@pre(lambda file_info, max_groups=3: max_groups >= 1)  # At least 1 group
def format_extraction_hint(file_info: FileInfo, max_groups: int = 3) -> str:
    """
    Format extraction suggestions for file_size_warning.

    P25: Shows extractable function groups with dependencies.

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind
        >>> s1 = Symbol(name="parse", kind=SymbolKind.FUNCTION, line=1, end_line=50,
        ...     function_calls=["validate"], internal_imports=["ast"])
        >>> s2 = Symbol(name="validate", kind=SymbolKind.FUNCTION, line=51, end_line=80,
        ...     function_calls=[], internal_imports=["ast"])
        >>> info = FileInfo(path="test.py", lines=100, symbols=[s1, s2], imports=["ast", "re"])
        >>> hint = format_extraction_hint(info)
        >>> "parse, validate" in hint
        True
        >>> "(80L)" in hint
        True
    """
    groups = find_extractable_groups(file_info)

    if not groups:
        return ""

    # Format top N groups
    hints: list[str] = []
    for i, group in enumerate(groups[:max_groups]):
        funcs = ", ".join(group["functions"])
        lines = group["lines"]
        deps = ", ".join(group["dependencies"]) if group["dependencies"] else "none"
        hints.append(f"[{chr(65 + i)}] {funcs} ({lines}L) | Deps: {deps}")

    return "\n".join(hints)
