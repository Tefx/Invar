"""Shared validation helpers for dead_assign walker."""

from __future__ import annotations

import ast

from deal import post, pre

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
