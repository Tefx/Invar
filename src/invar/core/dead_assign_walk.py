"""AST walking helpers for dead_assign rule."""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.dead_assign_common import (
    DeadWrite,
    _has_ast_fields,
    _is_excluded_name,
    _state_is_valid,
)


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

    if isinstance(node, ast.Lambda):
        _walk_expr(node.body, pending, dead_writes)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return

    for child in ast.iter_child_nodes(node):
        _walk_expr(child, pending, dead_writes)


@post(lambda result: result is None)
def _walk_expr_read_only(node: ast.AST, pending: dict[str, DeadWrite]) -> None:
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        _record_read(node.id, pending)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        _walk_nested_scope_reads_read_only(node, pending)
        return

    for child in ast.iter_child_nodes(node):
        _walk_expr_read_only(child, pending)


@post(lambda result: result is None)
def _walk_stmt_read_only(node: ast.stmt, pending: dict[str, DeadWrite]) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        _walk_nested_scope_reads_read_only(node, pending)
        return

    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.stmt):
            _walk_stmt_read_only(child, pending)
        else:
            _walk_expr_read_only(child, pending)


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
        _walk_expr(target, pending, dead_writes)
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
    else:
        _walk_expr(node.target, pending, dead_writes)
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
    # Simulate one additional iteration in read-only mode so loop-carried
    # reads clear pending writes from the previous iteration.
    for body_stmt in node.body:
        _walk_stmt_read_only(body_stmt, pending)
    for else_stmt in node.orelse:
        _walk_stmt(else_stmt, pending, dead_writes)


@pre(
    lambda node, pending, dead_writes: (
        _has_ast_fields(node, ("test", "body", "orelse")) and _state_is_valid(pending, dead_writes)
    )
)
@post(lambda result: result is None)
def _walk_while(
    node: ast.While,
    pending: dict[str, DeadWrite],
    dead_writes: list[DeadWrite],
) -> None:
    _walk_expr(node.test, pending, dead_writes)
    for body_stmt in node.body:
        _walk_stmt(body_stmt, pending, dead_writes)
    # Simulate next-iteration condition check in read-only mode.
    _walk_expr_read_only(node.test, pending)
    # Simulate one additional iteration body pass in read-only mode so
    # loop-carried reads clear pending writes from the previous iteration.
    for body_stmt in node.body:
        _walk_stmt_read_only(body_stmt, pending)
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


@post(lambda result: result is None)
def _walk_nested_scope_reads_read_only(node: ast.AST, pending: dict[str, DeadWrite]) -> None:
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        _record_read(node.id, pending)
        return

    if isinstance(node, ast.Lambda):
        _walk_expr_read_only(node.body, pending)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        _walk_nested_scope_header_read_only(node, pending)
        return

    for child in ast.iter_child_nodes(node):
        _walk_nested_scope_reads_read_only(child, pending)


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


@pre(
    lambda node, pending: (
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
        and all(len(k) > 0 and v[1] > 0 for k, v in pending.items())
    )
)
@post(lambda result: result is None)
def _walk_nested_scope_header_read_only(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    pending: dict[str, DeadWrite],
) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for decorator in node.decorator_list:
            _walk_expr_read_only(decorator, pending)
        for default in node.args.defaults:
            _walk_expr_read_only(default, pending)
        for kw_default in node.args.kw_defaults:
            if kw_default is not None:
                _walk_expr_read_only(kw_default, pending)
        for arg_node in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            node.args.vararg,
            node.args.kwarg,
        ]:
            if arg_node is not None and arg_node.annotation is not None:
                _walk_expr_read_only(arg_node.annotation, pending)
        if node.returns is not None:
            _walk_expr_read_only(node.returns, pending)
        for body_stmt in node.body:
            _walk_nested_scope_reads_read_only(body_stmt, pending)
        return

    for base in node.bases:
        _walk_expr_read_only(base, pending)
    for keyword in node.keywords:
        _walk_expr_read_only(keyword.value, pending)
    for decorator in node.decorator_list:
        _walk_expr_read_only(decorator, pending)
    for body_stmt in node.body:
        _walk_nested_scope_reads_read_only(body_stmt, pending)


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

    if isinstance(node, ast.While):
        _walk_while(node, pending, dead_writes)
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
