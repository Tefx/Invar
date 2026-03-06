"""Dead parameter detection for function and method definitions.

Identifies function parameters that are never referenced in the function body.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Severity, Violation


@pre(lambda decorator: isinstance(decorator, ast.expr))
@post(lambda result: result is None or isinstance(result, str))
def _decorator_name(decorator: ast.expr) -> str | None:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    return None


@pre(lambda base: isinstance(base, ast.expr))
@post(lambda result: isinstance(result, bool))
def _is_protocol_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "Protocol"
    if isinstance(base, ast.Attribute):
        return base.attr == "Protocol"
    if isinstance(base, ast.Subscript):
        return _is_protocol_base(base.value)
    return False


@pre(lambda tree: isinstance(tree, ast.AST))
@post(lambda result: all(isinstance(name, str) for name in result))
def _collect_protocol_classes(tree: ast.AST) -> set[str]:
    protocol_classes: set[str] = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any(_is_protocol_base(base) for base in node.bases)
    }

    while True:
        additions: set[str] = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and node.name not in protocol_classes
            and any(
                isinstance(base, ast.Name) and base.id in protocol_classes for base in node.bases
            )
        }
        if not additions:
            break
        protocol_classes.update(additions)

    return protocol_classes


@pre(lambda tree: isinstance(tree, ast.AST))
@post(
    lambda result: all(isinstance(k, ast.AST) and isinstance(v, ast.AST) for k, v in result.items())
)
def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        parents.update(dict.fromkeys(ast.iter_child_nodes(node), node))
    return parents


@pre(
    lambda node, parent_map: (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and all(isinstance(k, ast.AST) and isinstance(v, ast.AST) for k, v in parent_map.items())
    )
)
@post(lambda result: result is None or isinstance(result, str))
def _enclosing_class_name(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    parent_map: dict[ast.AST, ast.AST],
) -> str | None:
    current: ast.AST = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, ast.ClassDef):
            return current.name
    return None


@pre(
    lambda node: (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and hasattr(node, "decorator_list")
    )
)
@post(lambda result: isinstance(result, bool))
def _is_exempt_decorated_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    decorator_names: set[str] = set()
    for decorator in node.decorator_list:
        name = _decorator_name(decorator)
        if name is not None:
            decorator_names.add(name)
    return "property" in decorator_names or "abstractmethod" in decorator_names


@pre(
    lambda args: (
        isinstance(args, ast.arguments)
        and hasattr(args, "posonlyargs")
        and hasattr(args, "args")
        and hasattr(args, "kwonlyargs")
    )
)
@post(
    lambda result: all(
        isinstance(name, str) and isinstance(arg_node, ast.arg) for name, arg_node in result
    )
)
def _iter_checked_params(args: ast.arguments) -> list[tuple[str, ast.arg]]:
    params: list[tuple[str, ast.arg]] = []
    for arg_node in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
        if arg_node.arg in {"self", "cls"}:
            continue
        params.append((arg_node.arg, arg_node))
    return params


@pre(
    lambda node, used_names: (
        isinstance(node, ast.AST) and all(isinstance(v, str) for v in used_names)
    )
)
@post(lambda result: result is None)
def _collect_names_from_node(node: ast.AST, used_names: set[str]) -> None:
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        used_names.add(node.id)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for decorator in node.decorator_list:
            _collect_names_from_node(decorator, used_names)

        for default in node.args.defaults:
            _collect_names_from_node(default, used_names)

        for kw_default in node.args.kw_defaults:
            if kw_default is not None:
                _collect_names_from_node(kw_default, used_names)

        for arg_node in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
            node.args.vararg,
            node.args.kwarg,
        ]:
            if arg_node is not None and arg_node.annotation is not None:
                _collect_names_from_node(arg_node.annotation, used_names)

        if node.returns is not None:
            _collect_names_from_node(node.returns, used_names)
        return

    if isinstance(node, ast.ClassDef):
        for base in node.bases:
            _collect_names_from_node(base, used_names)
        for keyword in node.keywords:
            _collect_names_from_node(keyword.value, used_names)
        for decorator in node.decorator_list:
            _collect_names_from_node(decorator, used_names)
        return

    for child in ast.iter_child_nodes(node):
        _collect_names_from_node(child, used_names)


@pre(
    lambda node: isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and hasattr(node, "body")
)
@post(lambda result: all(isinstance(v, str) for v in result))
def _collect_used_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    used_names: set[str] = set()
    for stmt in node.body:
        _collect_names_from_node(stmt, used_names)
    return used_names


@pre(
    lambda file_infos, config: (
        all(isinstance(fi, FileInfo) for fi in file_infos) and isinstance(config, RuleConfig)
    )
)
@post(lambda result: all(v.rule == "dead_param" for v in result))
def check_dead_params(file_infos: list[FileInfo], config: RuleConfig) -> list[Violation]:
    """Check for unused function parameters.

    Exclusions:
    - ``self`` and ``cls``
    - ``*args`` and ``**kwargs``
    - ``@property`` and ``@abstractmethod`` methods
    - methods declared on Protocol classes
    - parameters consumed by decorator expressions in nested definitions

    Examples:
        >>> from invar.core.models import FileInfo, RuleConfig
        >>> nl = chr(10)
        >>> source1 = "def add(x, y):" + nl + "    return y" + nl
        >>> file1 = FileInfo(path="core/a.py", lines=2, source=source1)
        >>> violations1 = check_dead_params([file1], RuleConfig())
        >>> len(violations1)
        1
        >>> "add" in violations1[0].message and "x" in violations1[0].message
        True

        >>> source2 = "class Repo:" + nl + "    def save(self, value):" + nl + "        return value" + nl
        >>> file2 = FileInfo(path="core/b.py", lines=3, source=source2)
        >>> check_dead_params([file2], RuleConfig())
        []

        >>> source3 = "def forward(*args, **kwargs):" + nl + "    return run(*args, **kwargs)" + nl
        >>> file3 = FileInfo(path="core/c.py", lines=2, source=source3)
        >>> check_dead_params([file3], RuleConfig())
        []

        >>> source4 = "from abc import abstractmethod" + nl + "class Service:" + nl + "    @abstractmethod" + nl + "    def run(self, token):" + nl + "        ..." + nl
        >>> file4 = FileInfo(path="core/d.py", lines=5, source=source4)
        >>> check_dead_params([file4], RuleConfig())
        []

        >>> source5 = "class User:" + nl + "    @property" + nl + "    def name(self):" + nl + "        ..." + nl
        >>> file5 = FileInfo(path="core/e.py", lines=4, source=source5)
        >>> check_dead_params([file5], RuleConfig())
        []

        >>> source6 = "def configure(timeout):" + nl + "    @retry(wait=timeout)" + nl + "    def run():" + nl + "        return 1" + nl + "    return run()" + nl
        >>> file6 = FileInfo(path="core/f.py", lines=5, source=source6)
        >>> check_dead_params([file6], RuleConfig())
        []
    """
    _ = config

    violations: list[Violation] = []
    for file_info in file_infos:
        if not file_info.source:
            continue

        try:
            tree = ast.parse(file_info.source)
        except (SyntaxError, TypeError, ValueError):
            continue

        protocol_classes = _collect_protocol_classes(tree)
        parent_map = _build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if _is_exempt_decorated_function(node):
                continue

            class_name = _enclosing_class_name(node, parent_map)
            if class_name is not None and class_name in protocol_classes:
                continue

            checked_params = _iter_checked_params(node.args)
            if not checked_params:
                continue

            used_names = _collect_used_names(node)
            for param_name, param_node in checked_params:
                if param_name in used_names:
                    continue

                violations.append(
                    Violation(
                        rule="dead_param",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=getattr(param_node, "lineno", node.lineno),
                        message=(f"Function '{node.name}' parameter '{param_name}' is never used"),
                        suggestion="Remove parameter or prefix with _ if intentionally unused",
                    )
                )

    return violations
