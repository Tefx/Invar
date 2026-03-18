"""dead_assign rule implementation. Spec: plan.yaml:wiring-integrity-2.dead-assign-core, rule_meta:dead_assign."""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.dead_assign_walk import _collect_dead_writes
from invar.core.entry_points import extract_escape_hatches
from invar.core.models import FileInfo, RuleConfig, Severity, Violation


@post(lambda result: all(line > 0 for line in result))
def _dead_assign_allow_lines(source: str) -> set[int]:
    """Collect line numbers with dead_assign allow marker.

    Examples:
        >>> _dead_assign_allow_lines("x = 1  # @invar:allow dead_assign: temp")
        {1}
        >>> _dead_assign_allow_lines("x = 1")
        set()
    """
    return {
        line
        for rule, _reason, line in extract_escape_hatches(source)
        if rule == "dead_assign" and line > 0
    }


@pre(
    lambda file_infos, config: (
        all(isinstance(fi, FileInfo) for fi in file_infos) and isinstance(config, RuleConfig)
    )
)
@post(lambda result: all(v.rule == "dead_assign" for v in result))
def check_dead_assigns(file_infos: list[FileInfo], config: RuleConfig) -> list[Violation]:
    """Detect assigned-but-never-read local names in function scope.

    Supported assignment forms:
    - simple assignment and re-assignment
    - augmented assignment (read+write)
    - unpacking targets
    - loop targets
    - with-as targets
    - except-as targets

    Exclusions:
    - names prefixed with ``_``
    - assignment lines carrying ``# @invar:allow dead_assign: <reason>``

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> nl = chr(10)
        >>> source1 = "def f():" + nl + "    x = 1" + nl + "    return 0" + nl
        >>> v1 = check_dead_assigns([FileInfo(path='a.py', lines=3, source=source1)], RuleConfig())
        >>> len(v1)
        1
        >>> "x" in v1[0].message
        True

        >>> source2 = "def f():" + nl + "    x = 1" + nl + "    x += 2" + nl + "    return x" + nl
        >>> check_dead_assigns([FileInfo(path='b.py', lines=4, source=source2)], RuleConfig())
        []

        >>> source3 = "def f():" + nl + "    a, b = (1, 2)" + nl + "    return a" + nl
        >>> v3 = check_dead_assigns([FileInfo(path='c.py', lines=3, source=source3)], RuleConfig())
        >>> len(v3)
        1
        >>> "b" in v3[0].message
        True

        >>> source4 = "def f(items):" + nl + "    for item in items:" + nl + "        return 1" + nl
        >>> v4 = check_dead_assigns([FileInfo(path='d.py', lines=3, source=source4)], RuleConfig())
        >>> len(v4)
        1
        >>> "item" in v4[0].message
        True

        >>> source_nested = "def f():" + nl + "    x = 1" + nl + "    def g():" + nl + "        return x" + nl + "    return g()" + nl
        >>> check_dead_assigns([FileInfo(path='d2.py', lines=5, source=source_nested)], RuleConfig())
        []

    """
    del config

    violations: list[Violation] = []

    for file_info in file_infos:
        source = file_info.source or ""
        if not source:
            continue

        try:
            tree = ast.parse(source)
        except (SyntaxError, TypeError, ValueError):
            continue

        allow_lines = _dead_assign_allow_lines(source)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            for dead_write in _collect_dead_writes(node):
                if dead_write[1] in allow_lines:
                    continue
                violations.append(
                    Violation(
                        rule="dead_assign",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=dead_write[1],
                        message=(
                            f"Function '{node.name}' local '{dead_write[0]}' is assigned but never read"
                        ),
                        suggestion=(
                            "Remove assignment, use the value, or add: "
                            "# @invar:allow dead_assign: <reason>"
                        ),
                    )
                )

    return violations
