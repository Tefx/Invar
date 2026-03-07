"""Wiring-gap detection for Shell call sites.

Spec source: plan.yaml step `wiring-integrity-1.wiring-gap-core` (DX-89).
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.models import FileInfo, RuleConfig, Violation
from invar.core.references import build_symbol_index
from invar.core.wiring_gap_helpers import (
    _build_callable_index,
    _build_module_to_path,
    _CallableInfo,
    _collect_import_maps,
    _collect_simple_assignments,
    _has_forwarding,
    _ImportMaps,
    _locals_before_call,
    _make_wiring_gap_violation,
    _names_passed_as_keyword_values,
    _optional_unpassed_params,
    _parse_source,
    _resolve_callee,
)


@pre(
    lambda file_infos, config, verbose=False: (
        all(isinstance(fi, FileInfo) for fi in file_infos)
        and isinstance(config, RuleConfig)
        and isinstance(verbose, bool)
    )
)
@post(lambda result: all(v.rule == "wiring_gap" for v in result))
def check_wiring_gaps(
    file_infos: list[FileInfo], config: RuleConfig, verbose: bool = False
) -> list[Violation]:
    """Detect local names matching unpassed optional parameters of called functions.

    Spec source: plan.yaml step `wiring-integrity-1.wiring-gap-core`.
    Scope: name-match only, same-project resolution, simple assignments only.

    Examples:
        >>> from invar.core.models import RuleConfig, Symbol, SymbolKind
        >>> sym_build = Symbol(name="build", kind=SymbolKind.FUNCTION, line=1, end_line=2)
        >>> sym_run = Symbol(name="run", kind=SymbolKind.FUNCTION, line=1, end_line=4)
        >>> callee = FileInfo(path="app/callee.py", lines=2, symbols=[sym_build], is_shell=True, source="def build(payload='x'):\\n    return payload")
        >>> def mk(src: str) -> FileInfo:
        ...     return FileInfo(path="app/caller.py", lines=4, symbols=[sym_run], is_shell=True, source=src)

        >>> # 1) basic wiring gap
        >>> out1 = check_wiring_gaps([callee, mk("from app.callee import build\\n\\ndef run():\\n    payload = 'ok'\\n    return build()")], RuleConfig())
        >>> len(out1)
        1

        >>> # 2) param passed explicitly
        >>> check_wiring_gaps([callee, mk("from app.callee import build\\n\\ndef run():\\n    payload = 'ok'\\n    return build(payload=payload)")], RuleConfig())
        []

        >>> # 3) required parameter -> no warning
        >>> req = FileInfo(path="app/callee.py", lines=2, symbols=[sym_build], is_shell=True, source="def build(payload):\\n    return payload")
        >>> check_wiring_gaps([req, mk("from app.callee import build\\n\\ndef run():\\n    payload = 'ok'\\n    return build()")], RuleConfig())
        []

        >>> # 4) _prefix local excluded
        >>> check_wiring_gaps([callee, mk("from app.callee import build\\n\\ndef run():\\n    _payload = 'ok'\\n    return build()")], RuleConfig())
        []

        >>> # 5) non-matching local name
        >>> check_wiring_gaps([callee, mk("from app.callee import build\\n\\ndef run():\\n    body = 'ok'\\n    return build()")], RuleConfig())
        []

        >>> # 6) explicit None suppression
        >>> check_wiring_gaps([callee, mk("from app.callee import build\\n\\ndef run():\\n    payload = 'ok'\\n    return build(payload=None)")], RuleConfig())
        []

        >>> # 7) unresolved third-party callee -> silent skip
        >>> check_wiring_gaps([mk("from requests import get\\n\\ndef run():\\n    timeout = 5\\n    return get('https://example.com')")], RuleConfig())
        []
    """
    _ = config
    parsed = {fi.path: tree for fi in file_infos if (tree := _parse_source(fi.source)) is not None}
    module_to_path = _build_module_to_path(file_infos)
    callable_index = _build_callable_index(parsed)
    symbol_index = build_symbol_index(file_infos)

    violations: list[Violation] = []
    for file_info in file_infos:
        if not file_info.is_shell:
            continue
        tree = parsed.get(file_info.path)
        if tree is None:
            continue
        imports = _collect_import_maps(tree, file_info.path)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                violations.extend(
                    _analyze_function_calls(
                        file_path=file_info.path,
                        function_node=node,
                        imports=imports,
                        callable_index=callable_index,
                        module_to_path=module_to_path,
                        symbol_index=symbol_index,
                        verbose=verbose,
                    )
                )
    return violations


@pre(
    lambda file_path, function_node, imports, callable_index, module_to_path, symbol_index, verbose=False: (
        isinstance(file_path, str)
        and isinstance(function_node, ast.FunctionDef | ast.AsyncFunctionDef)
        and isinstance(imports, _ImportMaps)
        and isinstance(callable_index, dict)
        and isinstance(module_to_path, dict)
        and isinstance(symbol_index, dict)
        and isinstance(verbose, bool)
    )
)
@post(lambda result: all(v.rule == "wiring_gap" for v in result))
def _analyze_function_calls(
    file_path: str,
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    imports: _ImportMaps,
    callable_index: dict[str, dict[str, _CallableInfo]],
    module_to_path: dict[str, str],
    symbol_index: dict[str, set[str]],
    verbose: bool = False,
) -> list[Violation]:
    assignments = _collect_simple_assignments(function_node)
    out: list[Violation] = []

    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or _has_forwarding(node):
            continue
        callee = _resolve_callee(
            file_path=file_path,
            call=node,
            imports=imports,
            callable_index=callable_index,
            module_to_path=module_to_path,
            symbol_index=symbol_index,
        )
        if callee is None or not callee.optional_params:
            continue

        call_line = getattr(node, "lineno", function_node.lineno)
        local_vars = _locals_before_call(assignments, call_line)
        if not local_vars:
            continue

        passed_by_value = _names_passed_as_keyword_values(node)
        optional_unpassed = _optional_unpassed_params(node, callee)
        for var_name in sorted((local_vars - passed_by_value) & optional_unpassed):
            violation = _make_wiring_gap_violation(file_path, call_line, var_name, callee.name)
            if verbose:
                locals_list = ", ".join(sorted(local_vars))
                unpassed_list = ", ".join(sorted(optional_unpassed))
                passed_list = ", ".join(sorted(passed_by_value)) if passed_by_value else "(none)"
                violation.message = (
                    f"{violation.message} "
                    f"match: local '{var_name}' -> optional param '{var_name}'; "
                    f"locals_before_call=({locals_list}); "
                    f"optional_unpassed=({unpassed_list}); "
                    f"passed_keyword_values=({passed_list})"
                )
            out.append(violation)

    return out
