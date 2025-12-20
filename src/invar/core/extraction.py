"""Extraction analysis for Guard (Phase 11 P25). No I/O operations.

Analyzes function call relationships to suggest extractable groups
when files approach size limits.
"""

from __future__ import annotations

from deal import pre

from invar.core.models import FileInfo, Symbol, SymbolKind


@pre(lambda file_info: isinstance(file_info, FileInfo))
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
    # Get only functions/methods
    funcs = {s.name: s for s in file_info.symbols
             if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)}

    if not funcs:
        return []

    # Build call graph (only internal calls)
    func_names = set(funcs.keys())
    graph: dict[str, set[str]] = {name: set() for name in func_names}

    for name, sym in funcs.items():
        for called in sym.function_calls:
            if called in func_names:
                graph[name].add(called)
                graph[called].add(name)  # Bidirectional for grouping

    # Find connected components
    visited: set[str] = set()
    groups: list[dict] = []

    for name in func_names:
        if name in visited:
            continue

        # BFS to find all connected functions
        component: list[str] = []
        queue = [name]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            queue.extend(n for n in graph[current] if n not in visited)

        # Calculate group stats
        total_lines = sum(funcs[n].end_line - funcs[n].line + 1 for n in component)
        deps = _get_group_dependencies(component, funcs, file_info.imports)

        groups.append({
            "functions": sorted(component),
            "lines": total_lines,
            "dependencies": sorted(deps),
        })

    # Sort by lines (largest first)
    groups.sort(key=lambda g: -g["lines"])
    return groups


def _get_group_dependencies(
    func_names: list[str],
    funcs: dict[str, Symbol],
    file_imports: list[str],
) -> set[str]:
    """Get external dependencies used by a group of functions."""
    deps: set[str] = set()

    for name in func_names:
        sym = funcs[name]
        # Add internal imports used by this function
        deps.update(sym.internal_imports)

    # Filter to only include actual imports from file
    # (some internal_imports might be from nested scopes)
    return deps.intersection(set(file_imports)) if file_imports else deps


@pre(lambda file_info, max_groups=3: isinstance(file_info, FileInfo))
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
        hints.append(f"[{chr(65+i)}] {funcs} ({lines}L) | Deps: {deps}")

    return "\n".join(hints)
