"""Detect placeholder function bodies.

Flags function-like definitions whose body is a placeholder only:
- ``pass``
- ``raise NotImplementedError``
- ``...``
- bare docstring only

Exemptions:
- abstract methods (``@abstractmethod`` / ``@abc.abstractmethod``)
- anything defined inside protocol classes
- framework entry points (Click/Typer/Flask/FastAPI/etc.)
- explicit ``# @invar:allow stub_body: <reason>`` markers

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.entry_points import has_allow_marker, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, Symbol, SymbolKind, Violation


@pre(
    lambda file_infos, config: (
        all(isinstance(file_info, FileInfo) for file_info in file_infos)
        and isinstance(config, RuleConfig)
    )
)
@post(lambda result: all(v.rule == "stub_body" for v in result))
def check_stub_bodies(file_infos: list[FileInfo], config: RuleConfig) -> list[Violation]:
    """Check files for placeholder-only function bodies.

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> source1 = "def f():\\n    pass"
        >>> len(check_stub_bodies([FileInfo(path="src/mod.py", lines=2, source=source1)], RuleConfig()))
        1

        >>> source2 = "def f():\\n    raise NotImplementedError('todo')"
        >>> len(check_stub_bodies([FileInfo(path="src/mod.py", lines=2, source=source2)], RuleConfig()))
        1

        >>> source3 = "def f():\\n    ..."
        >>> len(check_stub_bodies([FileInfo(path="src/mod.py", lines=2, source=source3)], RuleConfig()))
        1

        >>> source4 = 'def f():\\n    \"\"\"placeholder\"\"\"'
        >>> len(check_stub_bodies([FileInfo(path="src/mod.py", lines=2, source=source4)], RuleConfig()))
        1

        >>> source5 = '''
        ... from abc import abstractmethod
        ... class Base:
        ...     @abstractmethod
        ...     def run(self):
        ...         pass
        ... '''
        >>> len(check_stub_bodies([FileInfo(path="src/base.py", lines=6, source=source5)], RuleConfig()))
        0

        >>> source6 = '''
        ... from typing import Protocol
        ... class Runner(Protocol):
        ...     def run(self) -> int:
        ...         ...
        ... '''
        >>> len(check_stub_bodies([FileInfo(path="src/proto.py", lines=5, source=source6)], RuleConfig()))
        0

        >>> source7 = '''
        ... import click
        ... @click.group()
        ... def main():
        ...     pass
        ... '''
        >>> len(check_stub_bodies([FileInfo(path="src/cli.py", lines=4, source=source7)], RuleConfig()))
        0

        >>> source8 = '''
        ... # @invar:allow stub_body: compatibility shim
        ... def shim():
        ...     ...
        ... '''
        >>> len(check_stub_bodies([FileInfo(path="src/shim.py", lines=3, source=source8)], RuleConfig()))
        0
    """
    _ = config
    violations: list[Violation] = []

    for file_info in file_infos:
        source = file_info.source or ""
        if not source:
            continue

        try:
            tree = ast.parse(source)
        except (SyntaxError, TypeError, ValueError):
            continue

        protocol_names = _collect_protocol_class_names(tree)
        violations.extend(
            _collect_stub_violations(
                path=file_info.path,
                source=source,
                statements=tree.body,
                protocol_names=protocol_names,
                name_prefix=(),
                in_protocol=False,
                in_class=False,
            )
        )

    return violations


@pre(lambda tree: isinstance(tree, ast.Module))
@post(lambda result: isinstance(result, set) and all(isinstance(name, str) for name in result))
def _collect_protocol_class_names(tree: ast.Module) -> set[str]:
    """Collect protocol class names (direct + inherited).

    Examples:
        >>> tree = ast.parse('''
        ... from typing import Protocol
        ... class Base(Protocol):
        ...     ...
        ... class Child(Base):
        ...     ...
        ... ''')
        >>> sorted(_collect_protocol_class_names(tree))
        ['Base', 'Child']
    """
    body = getattr(tree, "body", None)
    if not isinstance(body, list):
        return set()

    protocol_names: set[str] = {
        node.name
        for node in body
        if isinstance(node, ast.ClassDef) and _is_protocol_base_class(node)
    }

    while True:
        additions = {
            node.name
            for node in body
            if isinstance(node, ast.ClassDef)
            and node.name not in protocol_names
            and any(isinstance(base, ast.Name) and base.id in protocol_names for base in node.bases)
        }
        if not additions:
            break
        protocol_names.update(additions)

    return protocol_names


@pre(
    lambda class_def: (
        isinstance(class_def, ast.ClassDef) and isinstance(getattr(class_def, "bases", None), list)
    )
)
@post(lambda result: isinstance(result, bool))
def _is_protocol_base_class(class_def: ast.ClassDef) -> bool:
    """Return True if class directly inherits from Protocol."""
    bases = getattr(class_def, "bases", None)
    if not isinstance(bases, list):
        return False

    for base in bases:
        if isinstance(base, ast.Name) and base.id == "Protocol":
            return True
        if isinstance(base, ast.Attribute) and base.attr == "Protocol":
            return True
        if isinstance(base, ast.Subscript):
            value = base.value
            if isinstance(value, ast.Name) and value.id == "Protocol":
                return True
            if isinstance(value, ast.Attribute) and value.attr == "Protocol":
                return True
    return False


@pre(
    lambda path, source, statements, protocol_names, name_prefix, in_protocol, in_class: (
        isinstance(path, str)
        and isinstance(source, str)
        and all(isinstance(stmt, ast.stmt) for stmt in statements)
        and isinstance(protocol_names, set)
        and all(isinstance(name, str) for name in protocol_names)
        and isinstance(name_prefix, tuple)
        and all(isinstance(part, str) for part in name_prefix)
        and isinstance(in_protocol, bool)
        and isinstance(in_class, bool)
    )
)
@post(lambda result: all(v.rule == "stub_body" for v in result))
def _collect_stub_violations(
    path: str,
    source: str,
    statements: list[ast.stmt],
    protocol_names: set[str],
    name_prefix: tuple[str, ...],
    in_protocol: bool,
    in_class: bool,
) -> list[Violation]:
    """Walk statements recursively and collect stub_body violations.

    Examples:
        >>> tree = ast.parse("def outer():\\n    def inner():\\n        ...\\n    return 1")
        >>> violations = _collect_stub_violations(
        ...     path="src/mod.py",
        ...     source="def outer():\\n    def inner():\\n        ...\\n    return 1",
        ...     statements=tree.body,
        ...     protocol_names=set(),
        ...     name_prefix=(),
        ...     in_protocol=False,
        ...     in_class=False,
        ... )
        >>> [v.message for v in violations]
        ["Function 'outer.inner' contains a placeholder body"]
    """
    violations: list[Violation] = []

    for statement in statements:
        if isinstance(statement, ast.ClassDef):
            class_name = getattr(statement, "name", None)
            class_body = getattr(statement, "body", None)
            if not isinstance(class_name, str) or not isinstance(class_body, list):
                continue

            nested_in_protocol = in_protocol or class_name in protocol_names
            violations.extend(
                _collect_stub_violations(
                    path,
                    source,
                    class_body,
                    protocol_names,
                    (*name_prefix, class_name),
                    nested_in_protocol,
                    True,
                )
            )
            continue

        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
            func_name = getattr(statement, "name", None)
            func_body = getattr(statement, "body", None)
            if not isinstance(func_name, str) or not isinstance(func_body, list):
                continue

            symbol_name = ".".join((*name_prefix, func_name))
            exempt_abstract_method = in_class and _is_abstract_method(statement)
            symbol_kind = SymbolKind.METHOD if in_class else SymbolKind.FUNCTION
            symbol = Symbol(
                name=func_name,
                kind=symbol_kind,
                line=statement.lineno,
                end_line=getattr(statement, "end_lineno", statement.lineno),
            )
            exempt_entry_point = is_entry_point(symbol, source)
            has_stub_allow = has_allow_marker(symbol, source, "stub_body")

            if (
                (not in_protocol)
                and (not exempt_abstract_method)
                and (not exempt_entry_point)
                and (not has_stub_allow)
                and _is_stub_body(statement)
            ):
                violations.append(
                    Violation(
                        rule="stub_body",
                        severity=Severity.INFO,
                        file=path,
                        line=statement.lineno,
                        message=f"Function '{symbol_name}' contains a placeholder body",
                        suggestion="Implement the function body or convert it to abstract/protocol declaration",
                    )
                )

            violations.extend(
                _collect_stub_violations(
                    path,
                    source,
                    func_body,
                    protocol_names,
                    (*name_prefix, func_name),
                    in_protocol,
                    False,
                )
            )

    return violations


@pre(
    lambda node: (
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and isinstance(getattr(node, "decorator_list", None), list)
    )
)
@post(lambda result: isinstance(result, bool))
def _is_abstract_method(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True when function has an abstractmethod decorator.

    Examples:
        >>> fn = ast.parse("from abc import abstractmethod\\n@abstractmethod\\ndef run():\\n    pass").body[1]
        >>> isinstance(fn, ast.FunctionDef)
        True
        >>> _is_abstract_method(fn)
        True

        >>> fn2 = ast.parse("def run():\\n    pass").body[0]
        >>> isinstance(fn2, ast.FunctionDef)
        True
        >>> _is_abstract_method(fn2)
        False
    """
    decorators = getattr(node, "decorator_list", None)
    if not isinstance(decorators, list):
        return False

    for decorator in decorators:
        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
            return True
    return False


@pre(
    lambda node: (
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and isinstance(getattr(node, "body", None), list)
    )
)
@post(lambda result: isinstance(result, bool))
def _is_stub_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True when body has only one placeholder statement.

    Examples:
        >>> fn1 = ast.parse("def f():\\n    pass").body[0]
        >>> isinstance(fn1, ast.FunctionDef)
        True
        >>> _is_stub_body(fn1)
        True

        >>> fn2 = ast.parse("def f():\\n    return 1").body[0]
        >>> isinstance(fn2, ast.FunctionDef)
        True
        >>> _is_stub_body(fn2)
        False
    """
    body = getattr(node, "body", None)
    if not isinstance(body, list):
        return False

    if len(body) != 1:
        return False

    statement = body[0]
    if isinstance(statement, ast.Pass):
        return True

    if isinstance(statement, ast.Raise):
        return _raises_not_implemented(statement)

    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
        value = statement.value.value
        return value is Ellipsis or isinstance(value, str)

    return False


@pre(lambda node: isinstance(node, ast.Raise))
@post(lambda result: isinstance(result, bool))
def _raises_not_implemented(node: ast.Raise) -> bool:
    """Return True if raise statement raises NotImplementedError."""
    if node.exc is None:
        return False

    if isinstance(node.exc, ast.Name):
        return node.exc.id == "NotImplementedError"

    if isinstance(node.exc, ast.Call):
        func = node.exc.func
        if isinstance(func, ast.Name):
            return func.id == "NotImplementedError"
        if isinstance(func, ast.Attribute):
            return func.attr == "NotImplementedError"

    return False
