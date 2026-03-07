"""Dead parameter detection for function and method definitions.

Identifies function parameters that are never referenced in the function body.
Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.entry_points import has_allow_marker, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, Symbol, SymbolKind, Violation

CALLBACK_REGISTRAR_SUFFIXES: frozenset[str] = frozenset(
    {
        "signal",
        "connect",
        "register",
        "add_signal_handler",
        "set_exception_handler",
        "command",
        "callback",
        "route",
        "custom_route",
    }
)


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


@pre(
    lambda tree, protocol_classes: (
        isinstance(tree, ast.AST) and all(isinstance(name, str) for name in protocol_classes)
    )
)
@post(lambda result: all(isinstance(name, str) for name in result))
def _collect_protocol_method_names(tree: ast.AST, protocol_classes: set[str]) -> set[str]:
    """Collect all method names from Protocol classes in the same file.

    This is used to exempt implementation methods that match Protocol method names,
    even if the implementing class doesn't explicitly inherit from the Protocol.
    """
    method_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in protocol_classes:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_names.add(item.name)
    return method_names


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


@pre(lambda annotation: annotation is None or isinstance(annotation, ast.expr))
@post(lambda result: result is None or isinstance(result, str))
def _annotation_name(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        return _annotation_name(annotation.value)
    return None


@pre(
    lambda function_name, param_name, arg_node: (
        len(function_name) > 0 and len(param_name) > 0 and isinstance(arg_node, ast.arg)
    )
)
@post(lambda result: isinstance(result, bool))
def _is_config_shape_param(function_name: str, param_name: str, arg_node: ast.arg) -> bool:
    """Return True for checker-signature config parameters.

    These are intentionally accepted for uniform checker interface shape.
    """
    if param_name != "config":
        return False
    if not function_name.startswith("check_"):
        return False
    annotation = _annotation_name(arg_node.annotation)
    return annotation in {"RuleConfig", None}


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

    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _collect_names_from_node(stmt, used_names)
            for nested_stmt in stmt.body:
                _collect_names_from_node(nested_stmt, used_names)
            continue
        _collect_names_from_node(stmt, used_names)
    return used_names


@pre(lambda node: isinstance(node, ast.AST))
@post(lambda result: result is None or isinstance(result, str))
def _call_target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_target_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _call_target_name(node.func)
    return None


@pre(lambda call_name: len(call_name) > 0)
@post(lambda result: isinstance(result, bool))
def _is_callback_registrar(call_name: str) -> bool:
    tail = call_name.split(".")[-1]
    return tail in CALLBACK_REGISTRAR_SUFFIXES


@pre(lambda tree: isinstance(tree, ast.AST))
@post(lambda result: all(isinstance(name, str) for name in result))
def _collect_registered_callback_names(tree: ast.AST) -> set[str]:
    callback_keyword_names: set[str] = {
        "callback",
        "handler",
        "hook",
        "instructions",
        "instruction",
    }
    callback_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Name):
            callback_names.add(node.value.id)

        if not isinstance(node, ast.Call):
            continue

        call_name = _call_target_name(node.func)
        is_registrar = call_name is not None and _is_callback_registrar(call_name)

        for arg in node.args:
            if is_registrar and isinstance(arg, ast.Name):
                callback_names.add(arg.id)
            elif is_registrar and isinstance(arg, ast.Attribute):
                callback_names.add(arg.attr)

        for keyword in node.keywords:
            value = keyword.value
            is_callback_keyword = keyword.arg is not None and (
                keyword.arg in callback_keyword_names
                or any(
                    keyword.arg.endswith(suffix)
                    for suffix in ("_callback", "_handler", "_hook", "_instructions")
                )
            )
            if (is_registrar or is_callback_keyword) and isinstance(value, ast.Name):
                callback_names.add(value.id)
            elif is_registrar and isinstance(value, ast.Attribute):
                callback_names.add(value.attr)
    return callback_names


@pre(
    lambda node, param_name, param_node, callback_names, parent_map: (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and len(param_name) > 0
        and isinstance(param_node, ast.arg)
        and all(isinstance(name, str) for name in callback_names)
        and all(isinstance(k, ast.AST) and isinstance(v, ast.AST) for k, v in parent_map.items())
    )
)
@post(lambda result: isinstance(result, bool))
def _has_framework_signature_exemption(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    param_name: str,
    param_node: ast.arg,
    callback_names: set[str],
    parent_map: dict[ast.AST, ast.AST],
) -> bool:
    annotation = _annotation_name(param_node.annotation)
    if param_name == "request" and annotation in {"Request", "HTTPConnection", "WebSocket"}:
        return node.name.startswith(("handle_", "_handle_"))
    if param_name in {"ctx", "context"} and node.name in callback_names:
        return annotation in {"RunContext", "Context", "Any", None}
    if param_name == "raw" and any(
        _decorator_name(decorator) == "contextmanager" for decorator in node.decorator_list
    ):
        current: ast.AST = node
        while current in parent_map:
            current = parent_map[current]
            if isinstance(current, ast.ExceptHandler):
                return True
    return False


@pre(
    lambda node, class_name: (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and isinstance(getattr(node, "name", None), str)
        and (class_name is None or isinstance(class_name, str))
    )
)
@post(lambda result: result is not None)
def _symbol_for_node(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    class_name: str | None,
) -> Symbol:
    kind = SymbolKind.METHOD if class_name is not None else SymbolKind.FUNCTION
    return Symbol(
        name=node.name,
        kind=kind,
        line=node.lineno,
        end_line=getattr(node, "end_lineno", node.lineno),
    )


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
    - framework entry points and registered callback functions
    - explicit ``# @invar:allow dead_param: <reason>`` markers

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
        >>> source6 = "def configure(timeout):" + nl + "    @retry(wait=timeout)" + nl + "    def run():" + nl + "        return 1" + nl + "    return run()" + nl
        >>> file6 = FileInfo(path="core/f.py", lines=5, source=source6)
        >>> check_dead_params([file6], RuleConfig())
        []
        >>> source7 = "def check_rule(file_info, config: RuleConfig):" + nl + "    return file_info.path" + nl
        >>> file7 = FileInfo(path="core/g.py", lines=2, source=source7)
        >>> check_dead_params([file7], RuleConfig())
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
        protocol_method_names = _collect_protocol_method_names(tree, protocol_classes)
        parent_map = _build_parent_map(tree)
        callback_names = _collect_registered_callback_names(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if _is_exempt_decorated_function(node):
                continue

            if (class_name := _enclosing_class_name(node, parent_map)) in protocol_classes:
                continue

            # Exempt non-Protocol class methods when method name matches Protocol method name in same file
            # (structural subtyping: match by method name only, not inheritance)
            if class_name is not None and class_name not in protocol_classes:
                if node.name in protocol_method_names:
                    continue

            symbol = _symbol_for_node(node, class_name)
            if has_allow_marker(symbol, file_info.source, "dead_param"):
                continue

            if is_entry_point(symbol, file_info.source):
                continue

            is_registered_callback = node.name in callback_names

            checked_params = _iter_checked_params(node.args)
            if not checked_params:
                continue

            used_names = _collect_used_names(node)
            for param_name, param_node in checked_params:
                if param_name.startswith("_"):
                    continue

                if _is_config_shape_param(node.name, param_name, param_node):
                    continue

                if _has_framework_signature_exemption(
                    node, param_name, param_node, callback_names, parent_map
                ):
                    continue

                if is_registered_callback:
                    continue

                if param_name in used_names:
                    continue

                violations.append(
                    Violation(
                        rule="dead_param",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=getattr(param_node, "lineno", node.lineno),
                        message=(f"Function '{node.name}' parameter '{param_name}' is never used"),
                        suggestion="Remove unused parameter, rename to _param, or add: # @invar:allow dead_param: <reason>",
                    )
                )

    return violations
