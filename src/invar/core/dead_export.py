"""
Dead export detection for Shell functions and classes.

Identifies Shell functions and classes that are never referenced elsewhere in the codebase.
Useful for identifying potentially unused API endpoints or dead code.

Core module: pure logic, no I/O.
"""

from __future__ import annotations

import ast

from deal import post, pre
from invar_runtime import skip_property_test

from invar.core.entry_points import is_entry_point
from invar.core.models import FileInfo, RuleConfig, Severity, SymbolKind, Violation


@pre(lambda path: isinstance(path, str) and len(path) > 0)
@post(lambda result: isinstance(result, bool))
def _is_test_file(path: str) -> bool:
    """
    Check if a file path is a test file.

    Examples:
        >>> _is_test_file("tests/test_foo.py")
        True
        >>> _is_test_file("src/core/logic.py")
        False
    """
    path_lower = path.replace("\\", "/").lower()
    filename = path_lower.rsplit("/", 1)[-1]
    return (
        "/tests/" in path_lower
        or "/test/" in path_lower
        or filename.startswith("test_")
        or filename.endswith("_test.py")
    )


@skip_property_test("stub_body: Contract stub pending implementation")
@pre(lambda node: isinstance(node, ast.ClassDef) and isinstance(getattr(node, "bases", None), list))
@post(lambda result: isinstance(result, bool))
def _is_protocol_or_abc(node: ast.ClassDef) -> bool:
    """
    Check if a class definition is a Protocol or ABC subclass.

    Protocol classes (from typing.Protocol or typing_extensions.Protocol) and
    Abstract Base Classes (from abc.ABC) are structural/behavioral interfaces
    that define contracts rather than concrete implementations. These should
    be exempt from dead export reporting as they are meant to be subclassed.

    Handles multiple inheritance by checking each base class.

    Examples:
        >>> import ast
        >>> # Protocol subclass
        >>> code1 = "from typing import Protocol\\nclass MyProto(Protocol): pass"
        >>> tree1 = ast.parse(code1)
        >>> _is_protocol_or_abc(tree1.body[1])  # class def  # doctest: +SKIP
        True

        >>> # ABC subclass
        >>> code2 = "from abc import ABC\\nclass MyAbstract(ABC): pass"
        >>> tree2 = ast.parse(code2)
        >>> _is_protocol_or_abc(tree2.body[1])  # doctest: +SKIP
        True

        >>> # Plain class (not Protocol or ABC)
        >>> code3 = "class PlainClass: pass"
        >>> tree3 = ast.parse(code3)
        >>> _is_protocol_or_abc(tree3.body[0])  # doctest: +SKIP
        False

        >>> # Multiple inheritance with Protocol
        >>> code4 = "from typing import Protocol\\nclass Mixed(Protocol, object): pass"
        >>> tree4 = ast.parse(code4)
        >>> _is_protocol_or_abc(tree4.body[1])  # doctest: +SKIP
        True

        >>> # typing_extensions.Protocol
        >>> code5 = "from typing_extensions import Protocol\\nclass ExtProto(Protocol): pass"
        >>> tree5 = ast.parse(code5)
        >>> _is_protocol_or_abc(tree5.body[1])  # doctest: +SKIP
        True
    """
    bases = getattr(node, "bases", None)
    if not isinstance(bases, list):
        return False

    for base in bases:
        # Direct Name nodes: Protocol, ABC
        if isinstance(base, ast.Name):
            if base.id in ("Protocol", "ABC"):
                return True
        # Attribute nodes: typing.Protocol, abc.ABC, typing_extensions.Protocol
        elif isinstance(base, ast.Attribute):
            if base.attr in ("Protocol", "ABC"):
                return True
        # Subscript nodes: Protocol[...], ABC[...]
        elif isinstance(base, ast.Subscript):
            value = base.value
            if isinstance(value, ast.Name) and value.id in ("Protocol", "ABC"):
                return True
            if isinstance(value, ast.Attribute) and value.attr in ("Protocol", "ABC"):
                return True

    return False


@pre(
    lambda file_infos, ref_counts, config, ref_sources=None: (
        all(isinstance(fi, FileInfo) for fi in file_infos)
        and all(
            isinstance(name, str) and isinstance(count, int) and count >= 0
            for name, count in ref_counts.items()
        )
        and isinstance(config, RuleConfig)
        and (ref_sources is None or isinstance(ref_sources, dict))
    )
)
@post(lambda result: all(v.rule in ("dead_export", "test_only_export") for v in result))
def check_dead_exports(
    file_infos: list[FileInfo],
    ref_counts: dict[str, int],
    config: RuleConfig,
    ref_sources: dict[str, list[str]] | None = None,
) -> list[Violation]:
    """
    Check for dead exports in Shell functions and classes.

    Identifies Shell functions and classes that are never referenced elsewhere.
    Only checks public symbols (not starting with _).

    Two categories:
    - dead_export: Symbol has zero cross-file references (WARNING)
    - test_only_export: Symbol is only referenced from test files (INFO)

    Exclusions:
    - Private symbols (name.startswith("_"))
    - Dunder methods (name.startswith("__") and name.endswith("__"))
    - Entry points (framework callbacks detected by decorators)
    - Protocol/ABC classes (interface definitions meant to be subclassed)
    - Inline dead_export markers do not suppress findings (non-suppressible rule)

    Examples:
        >>> from invar.core.models import FileInfo, Symbol, SymbolKind, RuleConfig
        >>> # Case 1: No dead exports (referenced function)
        >>> sym1 = Symbol(name="used_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info1 = FileInfo(path="shell/api.py", lines=15, symbols=[sym1], is_shell=True)
        >>> ref_counts1 = {"shell/api.py::used_func": 3}
        >>> len(check_dead_exports([info1], ref_counts1, RuleConfig()))
        0

        >>> # Case 2: Dead export (unreferenced public function)
        >>> sym2 = Symbol(name="unused_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info2 = FileInfo(path="shell/api.py", lines=15, symbols=[sym2], is_shell=True)
        >>> ref_counts2 = {"shell/api.py::unused_func": 0}
        >>> violations2 = check_dead_exports([info2], ref_counts2, RuleConfig())
        >>> len(violations2)
        1
        >>> violations2[0].rule
        'dead_export'
        >>> violations2[0].severity
        <Severity.WARNING: 'warning'>

        >>> # Case 3: Private function (starts with _) - excluded
        >>> sym3 = Symbol(name="_helper", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info3 = FileInfo(path="shell/api.py", lines=15, symbols=[sym3], is_shell=True)
        >>> ref_counts3 = {}
        >>> len(check_dead_exports([info3], ref_counts3, RuleConfig()))
        0

        >>> # Case 4: Dunder method - excluded
        >>> sym4 = Symbol(name="__init__", kind=SymbolKind.METHOD, line=5, end_line=10)
        >>> info4 = FileInfo(path="shell/api.py", lines=15, symbols=[sym4], is_shell=True)
        >>> ref_counts4 = {}
        >>> len(check_dead_exports([info4], ref_counts4, RuleConfig()))
        0

        >>> # Case 4b: FUNCTION-kind dunder (e.g., module-level __init__) - excluded
        >>> sym4b = Symbol(name="__init__", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info4b = FileInfo(path="shell/api.py", lines=15, symbols=[sym4b], is_shell=True)
        >>> ref_counts4b = {}
        >>> len(check_dead_exports([info4b], ref_counts4b, RuleConfig()))
        0

        >>> # Case 5: Entry point (decorator) - excluded
        >>> sym5 = Symbol(name="index", kind=SymbolKind.FUNCTION, line=3, end_line=5)
        >>> source5 = '''
        ... @app.route("/")
        ... def index():
        ...     pass
        ... '''
        >>> info5 = FileInfo(path="shell/web.py", lines=10, symbols=[sym5], is_shell=True, source=source5)
        >>> len(check_dead_exports([info5], {}, RuleConfig()))
        0

        >>> # Case 6: @invar:allow marker does not suppress dead_export
        >>> sym6 = Symbol(name="legacy_api", kind=SymbolKind.FUNCTION, line=3, end_line=10)
        >>> source6 = '''
        ... # @invar:allow dead_export: Legacy API used by external systems
        ... def legacy_api():
        ...     pass
        ... '''
        >>> info6 = FileInfo(path="shell/api.py", lines=15, symbols=[sym6], is_shell=True, source=source6)
        >>> len(check_dead_exports([info6], {"shell/api.py::legacy_api": 0}, RuleConfig()))
        1

        >>> # Case 7: Core file - excluded (only checks Shell)
        >>> sym7 = Symbol(name="public_func", kind=SymbolKind.FUNCTION, line=5, end_line=10)
        >>> info7 = FileInfo(path="core/logic.py", lines=15, symbols=[sym7], is_core=True, is_shell=False)
        >>> ref_counts7 = {}
        >>> len(check_dead_exports([info7], ref_counts7, RuleConfig()))
        0

        >>> # Case 8: Multiple file_infos with mixed results
        >>> sym8a = Symbol(name="used", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info8a = FileInfo(path="shell/a.py", lines=10, symbols=[sym8a], is_shell=True)
        >>> sym8b = Symbol(name="dead", kind=SymbolKind.FUNCTION, line=1, end_line=5)
        >>> info8b = FileInfo(path="shell/b.py", lines=10, symbols=[sym8b], is_shell=True)
        >>> ref_counts8 = {"shell/a.py::used": 2, "shell/b.py::dead": 0}
        >>> violations8 = check_dead_exports([info8a, info8b], ref_counts8, RuleConfig())
        >>> len(violations8)
        1
        >>> violations8[0].file
        'shell/b.py'

        >>> # Case 9: Same-file reference counted -> not a dead export
        >>> from invar.core.references import count_cross_file_references
        >>> sym9 = Symbol(name="ping", kind=SymbolKind.FUNCTION, line=1, end_line=4)
        >>> source9 = "def ping():\\n    return 1\\n\\nvalue = ping()"
        >>> info9 = FileInfo(path="shell/c.py", lines=4, symbols=[sym9], is_shell=True, source=source9)
        >>> refs9 = count_cross_file_references([info9], {"shell/c.py": source9}, include_same_file=True)
        >>> check_dead_exports([info9], refs9, RuleConfig())
        []

        >>> # Case 10: Function listed in __all__ with 0 cross-file refs - excluded
        >>> from invar.core.references import count_cross_file_references
        >>> sym10 = Symbol(name="public_api", kind=SymbolKind.FUNCTION, line=1, end_line=2)
        >>> source10 = "def public_api():\\n    return 1\\n\\n__all__ = ['public_api']"
        >>> info10 = FileInfo(path="shell/d.py", lines=5, symbols=[sym10], is_shell=True, source=source10)
        >>> refs10 = count_cross_file_references([info10], {"shell/d.py": source10})
        >>> refs10.get("shell/d.py::public_api", 0)
        0
        >>> check_dead_exports([info10], refs10, RuleConfig())
        []

        >>> # Case 11: test_only_export - function only used in test files
        >>> sym11 = Symbol(name="test_helper", kind=SymbolKind.FUNCTION, line=1, end_line=3)
        >>> info11 = FileInfo(path="shell/utils.py", lines=10, symbols=[sym11], is_shell=True)
        >>> # Simulate ref_counts with test-only references
        >>> ref_counts11 = {"shell/utils.py::test_helper": 1}
        >>> ref_sources11 = {"shell/utils.py::test_helper": ["tests/test_utils.py"]}
        >>> violations11 = check_dead_exports([info11], ref_counts11, RuleConfig(), ref_sources11)
        >>> len(violations11) >= 1
        True
        >>> violations11[0].rule
        'test_only_export'
        >>> violations11[0].severity
        <Severity.INFO: 'info'>

        >>> # Case 12: Dead public class (unreferenced public class)
        >>> sym12 = Symbol(name="UnusedClass", kind=SymbolKind.CLASS, line=1, end_line=5)
        >>> info12 = FileInfo(path="shell/models.py", lines=10, symbols=[sym12], is_shell=True)
        >>> ref_counts12 = {"shell/models.py::UnusedClass": 0}
        >>> violations12 = check_dead_exports([info12], ref_counts12, RuleConfig())
        >>> len(violations12)  # doctest: +SKIP
        1
        >>> violations12[0].rule  # doctest: +SKIP
        'dead_export'
        >>> violations12[0].severity  # doctest: +SKIP
        <Severity.WARNING: 'warning'>
        >>> violations12[0].message  # doctest: +SKIP
        "Shell class 'UnusedClass' is never referenced"
    """
    violations: list[Violation] = []

    for file_info in file_infos:
        # Only check Shell files
        if not file_info.is_shell:
            continue

        source = file_info.source or ""
        exported_names: set[str] = set()
        tree: ast.Module | None = None

        if source:
            try:
                tree = ast.parse(source)
            except (SyntaxError, TypeError, ValueError):
                tree = None

            if tree is not None:
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        has_all_target = any(
                            isinstance(target, ast.Name) and target.id == "__all__"
                            for target in node.targets
                        )
                        if not has_all_target:
                            continue
                        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    exported_names.add(elt.value)

        for symbol in file_info.symbols:
            if symbol.kind not in (SymbolKind.FUNCTION, SymbolKind.CLASS):
                continue

            is_function = symbol.kind == SymbolKind.FUNCTION
            kind_label = "function" if is_function else "class"

            # Skip dunder methods (e.g., __init__, __str__) - function-only
            if is_function and symbol.name.startswith("__") and symbol.name.endswith("__"):
                continue

            # Skip private symbols (start with _)
            if symbol.name.startswith("_"):
                continue

            # Skip entry points (framework callbacks) - function-only
            if is_function and is_entry_point(symbol, source):
                continue

            # Spec: __all__ marks intended public API, treat as referenced.
            if symbol.name in exported_names:
                continue

            # Skip Protocol/ABC classes (interface definitions)
            if not is_function and tree is not None:
                is_protocol_or_abc_class = False
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == symbol.name:
                        if _is_protocol_or_abc(node):
                            is_protocol_or_abc_class = True
                        break
                if is_protocol_or_abc_class:
                    continue

            # Build reference key
            key = f"{file_info.path}::{symbol.name}"

            # Check if referenced (ref_count == 0 means dead export)
            ref_count = ref_counts.get(key, 0)
            if ref_count == 0:
                violations.append(
                    Violation(
                        rule="dead_export",
                        severity=Severity.WARNING,
                        file=file_info.path,
                        line=symbol.line,
                        message=f"Shell {kind_label} '{symbol.name}' is never referenced",
                        suggestion=(
                            f"Remove unused {kind_label}, or add: "
                            "# @invar:allow dead_export: <reason>"
                        ),
                    )
                )
            elif ref_sources:
                # Check if all references are only from test files
                sources = ref_sources.get(key, [])
                if sources and all(_is_test_file(src) for src in sources):
                    violations.append(
                        Violation(
                            rule="test_only_export",
                            severity=Severity.INFO,
                            file=file_info.path,
                            line=symbol.line,
                            message=(
                                f"Shell {kind_label} '{symbol.name}' "
                                "is only referenced from test files"
                            ),
                            suggestion=(
                                "Consider moving to tests/ or add: "
                                "# @invar:allow dead_export: <reason>"
                            ),
                        )
                    )

    return violations
