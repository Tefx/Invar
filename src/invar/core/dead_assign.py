"""dead_assign rule implementation. Spec: plan.yaml:wiring-integrity-2.dead-assign-core, rule_meta:dead_assign."""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.entry_points import extract_escape_hatches
from invar.core.models import FileInfo, RuleConfig, Severity, Violation

DeadWrite = tuple[str, int]


@pre(lambda name: len(name.strip()) > 0)
@post(lambda result: result in (True, False))
def _is_excluded_name(name: str) -> bool:
    return name.startswith("_")


@pre(
    lambda node, fields: (
        isinstance(node, ast.AST)
        and len(fields) > 0
        and all(len(field.strip()) > 0 for field in fields)
    )
)
@post(lambda result: result in (True, False))
def _has_ast_fields(node: ast.AST, fields: tuple[str, ...]) -> bool:
    return all(hasattr(node, field) for field in fields)


@pre(
    lambda pending, dead_writes: (
        all(len(name) > 0 and write[1] > 0 for name, write in pending.items())
        and all(len(write[0]) > 0 and write[1] > 0 for write in dead_writes)
    )
)
@post(lambda result: result in (True, False))
def _state_is_valid(pending: dict[str, DeadWrite], dead_writes: list[DeadWrite]) -> bool:
    return all(len(name) > 0 and write[1] > 0 for name, write in pending.items()) and all(
        len(write[0]) > 0 and write[1] > 0 for write in dead_writes
    )


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
    lambda name, line, pending, dead_writes: (
        len(name.strip()) > 0
        and line > 0
        and all(len(k) > 0 and v[1] > 0 for k, v in pending.items())
        and all(len(item[0]) > 0 and item[1] > 0 for item in dead_writes)
    )
)
@post(lambda result: result is None)
def _record_write(
    name: str,
    line: int,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    if _is_excluded_name(name):
        return

    # Keep latest pending write only to avoid branch-overwrite false positives.
    del dead_writes
    pending[name] = (name, line)


@pre(
    lambda name, pending: (
        len(name.strip()) > 0 and all(len(k) > 0 and v[1] > 0 for k, v in pending.items())
    )
)
@post(lambda result: result is None)
def _record_read(name: str, pending: dict[str, DeadWrite]) -> None:
    if _is_excluded_name(name):
        return
    pending.pop(name, None)


@post(lambda result: all(len(w[0]) > 0 and w[1] > 0 for w in result))
def _collect_target_writes(target: ast.expr) -> list[DeadWrite]:
    writes: list[DeadWrite] = []
    if isinstance(target, ast.Name):
        writes.append((target.id, target.lineno))
        return writes
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            writes.extend(_collect_target_writes(elt))
        return writes
    if isinstance(target, ast.Starred):
        writes.extend(_collect_target_writes(target.value))
    return writes


@post(lambda result: result is None)
def _walk_expr(node: ast.AST, pending: dict[str, DeadWrite], dead_writes: list[DeadWrite]) -> None:
    if isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Load):
            _record_read(node.id, pending)
        return

    if isinstance(node, ast.NamedExpr):
        _walk_expr(node.value, pending, dead_writes)
        for name, line in _collect_target_writes(node.target):
            _record_write(name, line, pending, dead_writes)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        return

    for child in ast.iter_child_nodes(node):
        _walk_expr(child, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("targets", "value")) and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_assignment(
    node: ast.Assign,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    _walk_expr(node.value, pending, dead_writes)
    for target in node.targets:
        for name, line in _collect_target_writes(target):
            _record_write(name, line, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("annotation", "target", "value"))
        and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_ann_assignment(
    node: ast.AnnAssign,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    _walk_expr(node.annotation, pending, dead_writes)
    if node.value is None:
        return
    _walk_expr(node.value, pending, dead_writes)
    for name, line in _collect_target_writes(node.target):
        _record_write(name, line, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("target", "value")) and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_aug_assignment(
    node: ast.AugAssign,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    if isinstance(node.target, ast.Name):
        _record_read(node.target.id, pending)
    _walk_expr(node.value, pending, dead_writes)
    for name, line in _collect_target_writes(node.target):
        _record_write(name, line, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(
            node,
            (
                "iter",
                "target",
                "body",
                "orelse",
            ),
        )
        and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_loop(
    node: ast.For | ast.AsyncFor,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    _walk_expr(node.iter, pending, dead_writes)
    for name, line in _collect_target_writes(node.target):
        _record_write(name, line, pending, dead_writes)
    for body_stmt in node.body:
        _walk_stmt(body_stmt, pending, dead_writes)
    for else_stmt in node.orelse:
        _walk_stmt(else_stmt, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("items", "body")) and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_with(
    node: ast.With | ast.AsyncWith,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    for item in node.items:
        _walk_expr(item.context_expr, pending, dead_writes)
        if item.optional_vars is None:
            continue
        for name, line in _collect_target_writes(item.optional_vars):
            _record_write(name, line, pending, dead_writes)
    for body_stmt in node.body:
        _walk_stmt(body_stmt, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(
            node,
            (
                "body",
                "handlers",
                "orelse",
                "finalbody",
            ),
        )
        and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_try(
    node: ast.Try,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    for body_stmt in node.body:
        _walk_stmt(body_stmt, pending, dead_writes)
    for handler in node.handlers:
        if handler.type is not None:
            _walk_expr(handler.type, pending, dead_writes)
        if isinstance(handler.name, str):
            _record_write(handler.name, handler.lineno, pending, dead_writes)
        for handler_stmt in handler.body:
            _walk_stmt(handler_stmt, pending, dead_writes)
    for else_stmt in node.orelse:
        _walk_stmt(else_stmt, pending, dead_writes)
    for final_stmt in node.finalbody:
        _walk_stmt(final_stmt, pending, dead_writes)


@post(lambda result: result is None)
def _walk_nested_scope_reads(
    node: ast.AST,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        _record_read(node.id, pending)
        return

    if isinstance(node, ast.Lambda):
        _walk_expr(node.body, pending, dead_writes)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        _walk_nested_scope_header(node, pending, dead_writes)
        return

    for child in ast.iter_child_nodes(node):
        _walk_nested_scope_reads(child, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("decorator_list", "body"))
        and (
            not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or _has_ast_fields(
                node,
                (
                    "args",
                    "returns",
                ),
            )
        )
        and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_nested_scope_header(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for decorator in node.decorator_list:
            _walk_expr(decorator, pending, dead_writes)
        for default in node.args.defaults:
            _walk_expr(default, pending, dead_writes)
        for kw_default in node.args.kw_defaults:
            if kw_default is not None:
                _walk_expr(kw_default, pending, dead_writes)
        for arg_node in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            node.args.vararg,
            node.args.kwarg,
        ]:
            if arg_node is not None and arg_node.annotation is not None:
                _walk_expr(arg_node.annotation, pending, dead_writes)
        if node.returns is not None:
            _walk_expr(node.returns, pending, dead_writes)
        for body_stmt in node.body:
            _walk_nested_scope_reads(body_stmt, pending, dead_writes)
        return

    for base in node.bases:
        _walk_expr(base, pending, dead_writes)
    for keyword in node.keywords:
        _walk_expr(keyword.value, pending, dead_writes)
    for decorator in node.decorator_list:
        _walk_expr(decorator, pending, dead_writes)
    for body_stmt in node.body:
        _walk_nested_scope_reads(body_stmt, pending, dead_writes)


@post(lambda result: result is None)
def _walk_stmt(node: ast.stmt, pending: dict[str, DeadWrite], dead_writes: list[DeadWrite]) -> None:
    if isinstance(node, ast.Assign):
        _walk_assignment(node, pending, dead_writes)
        return

    if isinstance(node, ast.AnnAssign):
        _walk_ann_assignment(node, pending, dead_writes)
        return

    if isinstance(node, ast.AugAssign):
        _walk_aug_assignment(node, pending, dead_writes)
        return

    if isinstance(node, (ast.For, ast.AsyncFor)):
        _walk_loop(node, pending, dead_writes)
        return

    if isinstance(node, (ast.With, ast.AsyncWith)):
        _walk_with(node, pending, dead_writes)
        return

    if isinstance(node, ast.Try):
        _walk_try(node, pending, dead_writes)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        _walk_nested_scope_header(node, pending, dead_writes)
        return

    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            _walk_stmt(child, pending, dead_writes)
        else:
            _walk_expr(child, pending, dead_writes)


@pre(
    lambda node: (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _has_ast_fields(node, ("body",))
    )
)
@post(lambda result: all(len(write[0].strip()) > 0 and write[1] > 0 for write in result))
def _collect_dead_writes(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[DeadWrite]:
    pending: dict[str, DeadWrite] = {}
    dead_writes: list[DeadWrite] = []
    for statement in node.body:
        _walk_stmt(statement, pending, dead_writes)
    dead_writes.extend(pending.values())
    return dead_writes


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
