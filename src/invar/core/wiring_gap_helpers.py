"""Private helpers for DX-89 wiring-gap detection."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from deal import post, pre
from invar_runtime import skip_property_test

from invar.core.models import FileInfo, Severity, Violation


@dataclass(frozen=True)
class _CallableInfo:
    name: str
    ordered_params: tuple[str, ...]
    optional_params: frozenset[str]


@dataclass(frozen=True)
class _ImportMaps:
    module_aliases: dict[str, str]
    symbol_aliases: dict[str, tuple[str, str]]


@pre(lambda source: source is None or isinstance(source, str))
@post(lambda result: result is None or isinstance(result, ast.Module))
def _parse_source(source: str | None) -> ast.Module | None:
    if not source:
        return None
    try:
        return ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return None


@pre(lambda path: isinstance(path, str) and len(path) > 0)
@post(lambda result: isinstance(result, str))
def _path_to_module(path: str) -> str:
    normalized = path.replace("\\", "/")
    if not normalized.endswith(".py"):
        return ""
    if normalized.endswith("/__init__.py"):
        return normalized[: -len("/__init__.py")].replace("/", ".")
    return normalized[:-3].replace("/", ".")


@pre(lambda file_infos: all(isinstance(fi, FileInfo) for fi in file_infos))
@post(lambda result: all(isinstance(k, str) and isinstance(v, str) for k, v in result.items()))
def _build_module_to_path(file_infos: list[FileInfo]) -> dict[str, str]:
    module_to_path: dict[str, str] = {}
    for file_info in file_infos:
        module = _path_to_module(file_info.path)
        if module:
            module_to_path[module] = file_info.path
    return module_to_path


@pre(
    lambda class_node: (
        isinstance(class_node, ast.ClassDef) and isinstance(getattr(class_node, "body", None), list)
    )
)
@post(lambda result: result is None or isinstance(result, ast.FunctionDef | ast.AsyncFunctionDef))
def _find_init(class_node: ast.ClassDef) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "__init__":
            return node
    return None


@pre(
    lambda node, drop_first=False: (
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and isinstance(getattr(node, "args", None), ast.arguments)
        and isinstance(drop_first, bool)
    )
)
@post(lambda result: isinstance(result, _CallableInfo))
def _callable_from_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    drop_first: bool = False,
) -> _CallableInfo:
    args = node.args
    positional = [arg.arg for arg in [*args.posonlyargs, *args.args]]
    if drop_first and positional and positional[0] in {"self", "cls"}:
        positional = positional[1:]

    defaults_count = len(args.defaults)
    optional_positional = positional[-defaults_count:] if defaults_count > 0 else []
    kwonly = [arg.arg for arg in args.kwonlyargs]
    optional_kwonly = [
        kwonly[i] for i, default in enumerate(args.kw_defaults) if default is not None
    ]

    return _CallableInfo(
        name=node.name,
        ordered_params=(*positional, *kwonly),
        optional_params=frozenset([*optional_positional, *optional_kwonly]),
    )


@pre(
    lambda parsed: all(
        isinstance(path, str)
        and isinstance(tree, ast.Module)
        and isinstance(getattr(tree, "body", None), list)
        for path, tree in parsed.items()
    )
)
@post(lambda result: all(isinstance(k, str) and isinstance(v, dict) for k, v in result.items()))
def _build_callable_index(parsed: dict[str, ast.Module]) -> dict[str, dict[str, _CallableInfo]]:
    index: dict[str, dict[str, _CallableInfo]] = {}
    for module_path in parsed:
        tree = parsed[module_path]
        current: dict[str, _CallableInfo] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                current[node.name] = _callable_from_function(node)
            elif isinstance(node, ast.ClassDef):
                init = _find_init(node)
                if init is not None:
                    current[node.name] = _callable_from_function(init, drop_first=True)
        if current:
            index[module_path] = current
    return index


@pre(
    lambda current_module, module, level: (
        isinstance(current_module, str)
        and (module is None or isinstance(module, str))
        and isinstance(level, int)
        and level >= 0
    )
)
@post(lambda result: result is None or isinstance(result, str))
def _resolve_import_module(current_module: str, module: str | None, level: int) -> str | None:
    if level == 0:
        return module
    parts = current_module.split(".") if current_module else []
    if parts:
        parts = parts[:-1]
    up = max(level - 1, 0)
    if up > len(parts):
        return None
    base = parts[: len(parts) - up]
    if module:
        return ".".join([*base, module])
    return ".".join(base) if base else None


@pre(
    lambda tree, file_path: (
        isinstance(tree, ast.Module) and isinstance(file_path, str) and len(file_path) > 0
    )
)
@post(lambda result: isinstance(result, _ImportMaps))
def _collect_import_maps(tree: ast.Module, file_path: str) -> _ImportMaps:
    current_module = _path_to_module(file_path)
    module_aliases: dict[str, str] = {}
    symbol_aliases: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_aliases[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_module(current_module, node.module, node.level)
            if resolved is None:
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                symbol_aliases[alias.asname or alias.name] = (resolved, alias.name)
    return _ImportMaps(module_aliases=module_aliases, symbol_aliases=symbol_aliases)


@pre(lambda function_node: isinstance(function_node, ast.FunctionDef | ast.AsyncFunctionDef))
@post(lambda result: all(isinstance(name, str) and isinstance(line, int) for name, line in result))
def _collect_simple_assignments(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, int]]:
    names: list[tuple[str, int]] = []
    for node in ast.walk(function_node):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            names.append((node.targets[0].id, getattr(node, "lineno", 0)))
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            names.append((node.target.id, getattr(node, "lineno", 0)))
    return names


@pre(
    lambda call: (
        isinstance(call, ast.Call)
        and isinstance(getattr(call, "args", None), list)
        and isinstance(getattr(call, "keywords", None), list)
    )
)
@post(lambda result: isinstance(result, bool))
def _has_forwarding(call: ast.Call) -> bool:
    if any(isinstance(arg, ast.Starred) for arg in call.args):
        return True
    return any(keyword.arg is None for keyword in call.keywords)


@skip_property_test(
    "strategy_entropy: nested callable/symbol indexes produce oversized generated data"
)
@pre(
    lambda file_path, call, imports, callable_index, module_to_path, symbol_index: (
        isinstance(file_path, str)
        and isinstance(call, ast.Call)
        and hasattr(call, "func")
        and isinstance(imports, _ImportMaps)
        and isinstance(callable_index, dict)
        and isinstance(module_to_path, dict)
        and isinstance(symbol_index, dict)
    )
)
@post(lambda result: result is None or isinstance(result, _CallableInfo))
def _resolve_callee(
    file_path: str,
    call: ast.Call,
    imports: _ImportMaps,
    callable_index: dict[str, dict[str, _CallableInfo]],
    module_to_path: dict[str, str],
    symbol_index: dict[str, set[str]],
) -> _CallableInfo | None:
    func = call.func
    if isinstance(func, ast.Name):
        local_name = func.id
        local_defs = callable_index.get(file_path, {})
        if local_name in local_defs:
            return local_defs[local_name]

        imported = imports.symbol_aliases.get(local_name)
        if imported is not None:
            module_name, symbol_name = imported
            path = module_to_path.get(module_name)
            if path is not None:
                return callable_index.get(path, {}).get(symbol_name)

        candidates = symbol_index.get(local_name, set())
        if len(candidates) == 1:
            only_path = next(iter(candidates))
            return callable_index.get(only_path, {}).get(local_name)
        return None

    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        module_name = imports.module_aliases.get(func.value.id)
        if module_name is None:
            return None
        path = module_to_path.get(module_name)
        if path is None:
            return None
        return callable_index.get(path, {}).get(func.attr)

    return None


@pre(
    lambda assignments, line: (
        all(isinstance(name, str) and isinstance(n, int) for name, n in assignments)
        and isinstance(line, int)
        and line >= 0
    )
)
@post(lambda result: all(isinstance(name, str) for name in result))
def _locals_before_call(assignments: list[tuple[str, int]], line: int) -> set[str]:
    return {
        name
        for name, assign_line in assignments
        if assign_line < line and not name.startswith("_") and name not in {"self", "cls"}
    }


@pre(lambda call: isinstance(call, ast.Call) and isinstance(getattr(call, "keywords", None), list))
@post(lambda result: all(isinstance(name, str) for name in result))
def _names_passed_as_keyword_values(call: ast.Call) -> set[str]:
    return {kw.value.id for kw in call.keywords if kw.arg and isinstance(kw.value, ast.Name)}


@pre(
    lambda call, callee: (
        isinstance(call, ast.Call)
        and isinstance(getattr(call, "args", None), list)
        and isinstance(getattr(call, "keywords", None), list)
        and isinstance(callee, _CallableInfo)
    )
)
@post(lambda result: all(isinstance(name, str) for name in result))
def _optional_unpassed_params(call: ast.Call, callee: _CallableInfo) -> set[str]:
    passed_keywords = {kw.arg for kw in call.keywords if kw.arg}
    positional_params = set(callee.ordered_params[: len(call.args)])
    return set(callee.optional_params) - passed_keywords - positional_params


@skip_property_test(
    "crosshair_incompatible: pydantic Violation model rejects symbolic execution values"
)
@pre(
    lambda file_path, line, var_name, callee_name: (
        isinstance(file_path, str)
        and isinstance(line, int)
        and isinstance(var_name, str)
        and isinstance(callee_name, str)
        and len(file_path) > 0
        and line >= 0
        and len(var_name) > 0
        and len(callee_name) > 0
    )
)
@post(lambda result: result.rule == "wiring_gap")
def _make_wiring_gap_violation(
    file_path: str,
    line: int,
    var_name: str,
    callee_name: str,
) -> Violation:
    return Violation(
        rule="wiring_gap",
        severity=Severity.WARNING,
        file=str(file_path),
        line=int(line),
        message=(
            f"Local variable '{var_name!s}' matches optional parameter "
            f"on call to '{callee_name!s}' but is not passed"
        ),
        suggestion=(
            f"Pass '{var_name!s}={var_name!s}' explicitly, rename local variable, "
            "or confirm omission intentionally"
        ),
    )
