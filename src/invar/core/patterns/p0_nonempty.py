"""
NonEmpty Pattern Detector (DX-61, P0).

Detects runtime empty-collection checks that could benefit from
compile-time NonEmpty type safety.
"""

import ast

from deal import post, pre

from invar.core.patterns.detector import BaseDetector
from invar.core.patterns.types import (
    Confidence,
    PatternID,
    PatternSuggestion,
    Priority,
)


class NonEmptyDetector(BaseDetector):
    """
    Detect runtime checks for empty collections.

    These are candidates for NonEmpty type to guarantee non-emptiness
    at compile time instead of runtime.

    Detection logic:
    - Find 'if not items:' or 'if len(items) == 0:' patterns
    - Look for raises or early returns after such checks
    - Suggest NonEmpty type for the parameter

    >>> import ast
    >>> detector = NonEmptyDetector()
    >>> code = '''
    ... def summarize(items: list[str]) -> str:
    ...     if not items:
    ...         raise ValueError("Cannot summarize empty list")
    ...     return f"First: {items[0]}"
    ... '''
    >>> tree = ast.parse(code)
    >>> suggestions = detector.detect(tree, "test.py")
    >>> len(suggestions) > 0
    True
    """

    @property
    @post(lambda result: result == PatternID.NONEMPTY)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern.

        >>> NonEmptyDetector().pattern_id
        <PatternID.NONEMPTY: 'nonempty'>
        """
        return PatternID.NONEMPTY

    @property
    @post(lambda result: result == Priority.P0)
    def priority(self) -> Priority:
        """Priority tier.

        >>> NonEmptyDetector().priority
        <Priority.P0: 'P0'>
        """
        return Priority.P0

    @property
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description.

        >>> len(NonEmptyDetector().description) > 0
        True
        """
        return "Use NonEmpty type for compile-time non-empty guarantees"

    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Find functions with runtime empty-collection checks.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> code = '''
        ... def process(data: list[int]):
        ...     if len(data) == 0:
        ...         raise ValueError("Empty data")
        ...     return data[0]
        ... '''
        >>> tree = ast.parse(code)
        >>> suggestions = detector.detect(tree, "test.py")
        >>> len(suggestions) > 0
        True
        """
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                suggestion = self._check_function(node, file_path)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    @pre(lambda self, node, file_path: len(file_path) > 0)
    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> PatternSuggestion | None:
        """
        Check if function has empty-collection guard patterns.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> code = '''
        ... def f(items):
        ...     if not items:
        ...         raise ValueError("Empty")
        ...     return items[0]
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> suggestion = detector._check_function(func, "test.py")
        >>> suggestion is not None
        True
        """
        empty_checks = self._find_empty_checks(node)

        if empty_checks:
            var_name, check_line = empty_checks[0]
            param_type = self._get_param_type(node, var_name)
            confidence = self._calculate_confidence(node, var_name, param_type)

            return self.make_suggestion(
                pattern_id=self.pattern_id,
                priority=self.priority,
                file_path=file_path,
                line=check_line,
                message=f"Runtime empty check on '{var_name}' - consider NonEmpty type",
                current_code=self._format_check(var_name, param_type),
                suggested_pattern=f"NonEmpty[{param_type or 'T'}] guarantees non-empty at compile time",
                confidence=confidence,
                reference_pattern="Pattern 3: NonEmpty for Compile-Time Safety",
            )

        return None

    @post(lambda result: all(isinstance(v, str) and line > 0 for v, line in result))
    def _find_empty_checks(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[tuple[str, int]]:
        """
        Find 'if not x' or 'if len(x) == 0' patterns with raise/return.

        Only checks if statements at the function level, not nested functions.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> code = '''
        ... def f(items):
        ...     if not items:
        ...         raise ValueError("Empty")
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> checks = detector._find_empty_checks(func)
        >>> len(checks) > 0
        True
        >>> checks[0][0]
        'items'
        """
        checks: list[tuple[str, int]] = []
        self._collect_empty_checks(node.body, checks)
        return checks

    @pre(lambda self, stmts, checks: stmts is not None and checks is not None)
    def _collect_empty_checks(
        self, stmts: list[ast.stmt], checks: list[tuple[str, int]]
    ) -> None:
        """
        Recursively collect empty checks, avoiding nested functions.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> stmts = ast.parse("if not x: raise ValueError('e')").body
        >>> checks: list[tuple[str, int]] = []
        >>> detector._collect_empty_checks(stmts, checks)
        >>> len(checks)
        1
        """
        for stmt in stmts:
            # Skip nested functions
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if isinstance(stmt, ast.If):
                var_name = self._extract_empty_check_var(stmt.test)
                if var_name and self._has_raise_or_return(stmt.body):
                    checks.append((var_name, stmt.lineno))
                # Recurse into if body and else
                self._collect_empty_checks(stmt.body, checks)
                self._collect_empty_checks(stmt.orelse, checks)

    @post(lambda result: result is None or (isinstance(result, str) and len(result) > 0))
    def _extract_empty_check_var(self, test: ast.expr) -> str | None:
        """
        Extract variable name from empty-check condition.

        Handles:
        - 'not items' -> 'items'
        - 'len(items) == 0' -> 'items'
        - 'len(items) < 1' -> 'items'

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> test = ast.parse("not items", mode="eval").body
        >>> detector._extract_empty_check_var(test)
        'items'
        """
        # Handle 'not items'
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            if isinstance(test.operand, ast.Name):
                return test.operand.id

        # Handle 'len(items) == 0' or 'len(items) < 1'
        if isinstance(test, ast.Compare):
            if len(test.ops) == 1 and len(test.comparators) == 1:
                left = test.left
                op = test.ops[0]
                right = test.comparators[0]

                # Check for len(x) on left
                if (
                    isinstance(left, ast.Call)
                    and isinstance(left.func, ast.Name)
                    and left.func.id == "len"
                    and len(left.args) == 1
                    and isinstance(left.args[0], ast.Name)
                ):
                    var_name = left.args[0].id

                    # Check for == 0 or < 1
                    if isinstance(right, ast.Constant):
                        if isinstance(op, ast.Eq) and right.value == 0:
                            return var_name
                        if isinstance(op, ast.Lt) and right.value == 1:
                            return var_name

        return None

    @post(lambda result: isinstance(result, bool))
    def _has_raise_or_return(self, body: list[ast.stmt]) -> bool:
        """
        Check if body contains raise or return statement.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> body = ast.parse("raise ValueError('x')").body
        >>> detector._has_raise_or_return(body)
        True
        """
        return any(isinstance(stmt, (ast.Raise, ast.Return)) for stmt in body)

    @pre(lambda self, node, var_name: len(var_name) > 0)
    def _get_param_type(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, var_name: str
    ) -> str | None:
        """
        Get type annotation for a parameter.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> func = ast.parse("def f(items: list[str]): pass").body[0]
        >>> detector._get_param_type(func, "items")
        'list[str]'
        """
        for arg in node.args.args:
            if arg.arg == var_name and arg.annotation:
                return self._annotation_to_str(arg.annotation)
        return None

    @pre(lambda self, _node, var_name, param_type: len(var_name) > 0)
    @post(lambda result: result in Confidence)
    def _calculate_confidence(
        self,
        _node: ast.FunctionDef | ast.AsyncFunctionDef,
        var_name: str,
        param_type: str | None,
    ) -> Confidence:
        """
        Calculate confidence based on context.

        >>> import ast
        >>> detector = NonEmptyDetector()
        >>> func = ast.parse("def f(items: list[str]): pass").body[0]
        >>> detector._calculate_confidence(func, "items", "list[str]")
        <Confidence.HIGH: 'high'>
        """
        # High confidence if typed as list[T]
        if param_type and param_type.startswith("list["):
            return Confidence.HIGH

        # Medium confidence if var name suggests collection
        if any(kw in var_name.lower() for kw in ("items", "list", "elements", "data")):
            return Confidence.MEDIUM

        return Confidence.LOW

    @pre(lambda self, var_name, param_type: len(var_name) > 0)
    @post(lambda result: len(result) > 0 and "if not" in result)
    def _format_check(self, var_name: str, param_type: str | None) -> str:
        """
        Format the empty check for display.

        >>> detector = NonEmptyDetector()
        >>> detector._format_check("items", "list[str]")
        'if not items: raise ... (items: list[str])'
        """
        type_info = f" ({var_name}: {param_type})" if param_type else ""
        return f"if not {var_name}: raise ...{type_info}"
