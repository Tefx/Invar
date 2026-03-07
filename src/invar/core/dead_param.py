"""Dead parameter detection for function and method definitions.

Identifies function parameters that are never referenced in the function body.
Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre

from invar.core.dead_param_helpers import (
    build_parent_map,
    collect_protocol_classes,
    collect_protocol_method_names,
    collect_registered_callback_names,
    collect_used_names,
    enclosing_class_name,
    has_framework_signature_exemption,
    is_config_shape_param,
    is_exempt_decorated_function,
    iter_checked_params,
    symbol_for_node,
)
from invar.core.entry_points import has_allow_marker, is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, Violation


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

        protocol_classes = collect_protocol_classes(tree)
        protocol_method_names = collect_protocol_method_names(tree, protocol_classes)
        parent_map = build_parent_map(tree)
        callback_names = collect_registered_callback_names(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if is_exempt_decorated_function(node):
                continue

            class_name = enclosing_class_name(node, parent_map)
            if class_name in protocol_classes:
                continue

            if class_name is not None and class_name not in protocol_classes:
                if node.name in protocol_method_names:
                    continue

            symbol = symbol_for_node(node, class_name)
            if has_allow_marker(symbol, file_info.source, "dead_param"):
                continue
            if is_entry_point(symbol, file_info.source):
                continue

            is_registered_callback = node.name in callback_names
            checked_params = iter_checked_params(node.args)
            if not checked_params:
                continue

            used_names = collect_used_names(node)
            for param_name, param_node in checked_params:
                if param_name.startswith("_"):
                    continue
                if is_config_shape_param(node.name, param_name, param_node):
                    continue
                if has_framework_signature_exemption(
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
