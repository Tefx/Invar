"""
Literal Pattern Detector (DX-61, P0).

Detects runtime validation for finite value sets that could benefit
from Literal type for compile-time safety.
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


class LiteralDetector(BaseDetector):
    """
    Detect runtime checks for finite value sets.

    These are candidates for Literal type to catch invalid values
    at type-check time instead of runtime.

    Detection logic:
    - Find 'if x not in (...)' or 'if x not in [...]' patterns
    - Look for small sets of string/int literals
    - Suggest Literal type for the parameter

    >>> import ast
    >>> detector = LiteralDetector()
    >>> code = '''
    ... def set_level(level: str) -> None:
    ...     if level not in ("debug", "info", "warning", "error"):
    ...         raise ValueError(f"Invalid level: {level}")
    ... '''
    >>> tree = ast.parse(code)
    >>> suggestions = detector.detect(tree, "test.py")
    >>> len(suggestions) > 0
    True
    """

    MAX_LITERAL_VALUES = 10  # Don't suggest Literal for large sets

    @property
    @post(lambda result: result == PatternID.LITERAL)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern.

        >>> LiteralDetector().pattern_id
        <PatternID.LITERAL: 'literal'>
        """
        return PatternID.LITERAL

    @property
    @post(lambda result: result == Priority.P0)
    def priority(self) -> Priority:
        """Priority tier.

        >>> LiteralDetector().priority
        <Priority.P0: 'P0'>
        """
        return Priority.P0

    @property
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description.

        >>> len(LiteralDetector().description) > 0
        True
        """
        return "Use Literal type for finite value sets"

    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Find functions with runtime finite-set validation.

        >>> import ast
        >>> detector = LiteralDetector()
        >>> code = '''
        ... def process(mode: str):
        ...     if mode not in ["fast", "slow", "auto"]:
        ...         raise ValueError("Bad mode")
        ... '''
        >>> tree = ast.parse(code)
        >>> suggestions = detector.detect(tree, "test.py")
        >>> len(suggestions) > 0
        True
        """
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_suggestions = self._check_function(node, file_path)
                suggestions.extend(func_suggestions)

        return suggestions

    @pre(lambda self, node, file_path: len(file_path) > 0)
    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str
    ) -> list[PatternSuggestion]:
        """
        Check if function has finite-set validation patterns.

        >>> import ast
        >>> detector = LiteralDetector()
        >>> code = '''
        ... def f(x):
        ...     if x not in ("a", "b", "c"):
        ...         raise ValueError("Bad")
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> suggestions = detector._check_function(func, "test.py")
        >>> len(suggestions) > 0
        True
        """
        suggestions = []
        checks = self._find_membership_checks(node)

        for var_name, values, check_line in checks:
            if len(values) <= self.MAX_LITERAL_VALUES:
                confidence = self._calculate_confidence(values)

                suggestions.append(
                    self.make_suggestion(
                        pattern_id=self.pattern_id,
                        priority=self.priority,
                        file_path=file_path,
                        line=check_line,
                        message=f"Runtime check for {len(values)} values - consider Literal type",
                        current_code=self._format_check(var_name, values),
                        suggested_pattern=self._format_literal(var_name, values),
                        confidence=confidence,
                        reference_pattern="Pattern 4: Literal for Finite Value Sets",
                    )
                )

        return suggestions

    @post(lambda result: all(len(name) > 0 and len(vals) > 0 and line > 0 for name, vals, line in result))
    def _find_membership_checks(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> list[tuple[str, list[str | int], int]]:
        """
        Find 'if x not in (...)' patterns.

        Returns list of (var_name, values, line_number).
        Only checks function-level if statements, not nested functions.

        >>> import ast
        >>> detector = LiteralDetector()
        >>> code = '''
        ... def f(x):
        ...     if x not in ("a", "b"):
        ...         raise ValueError("Bad")
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> checks = detector._find_membership_checks(func)
        >>> len(checks) > 0
        True
        >>> checks[0][1]
        ['a', 'b']
        """
        checks: list[tuple[str, list[str | int], int]] = []
        self._collect_membership_checks(node.body, checks)
        return checks

    @pre(lambda self, stmts, checks: stmts is not None and checks is not None)
    def _collect_membership_checks(
        self,
        stmts: list[ast.stmt],
        checks: list[tuple[str, list[str | int], int]],
    ) -> None:
        """
        Recursively collect membership checks, avoiding nested functions.

        >>> import ast
        >>> detector = LiteralDetector()
        >>> stmts = ast.parse("if x not in ('a', 'b'): raise ValueError()").body
        >>> checks: list[tuple[str, list[str | int], int]] = []
        >>> detector._collect_membership_checks(stmts, checks)
        >>> len(checks)
        1
        """
        for stmt in stmts:
            # Skip nested functions
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if isinstance(stmt, ast.If):
                result = self._extract_membership_check(stmt.test)
                if result:
                    var_name, values = result
                    checks.append((var_name, values, stmt.lineno))
                # Recurse into body and else
                self._collect_membership_checks(stmt.body, checks)
                self._collect_membership_checks(stmt.orelse, checks)

    @post(lambda result: result is None or (len(result[0]) > 0 and len(result[1]) > 0))
    def _extract_membership_check(
        self, test: ast.expr
    ) -> tuple[str, list[str | int]] | None:
        """
        Extract variable and values from membership check.

        Handles:
        - 'x not in ("a", "b", "c")'
        - 'x not in ["a", "b", "c"]'

        >>> import ast
        >>> detector = LiteralDetector()
        >>> test = ast.parse("x not in ('a', 'b')", mode="eval").body
        >>> result = detector._extract_membership_check(test)
        >>> result is not None
        True
        >>> result[0]
        'x'
        >>> result[1]
        ['a', 'b']
        """
        # Handle 'x not in (...)'
        if isinstance(test, ast.Compare):
            if (
                len(test.ops) == 1
                and isinstance(test.ops[0], ast.NotIn)
                and len(test.comparators) == 1
            ):
                left = test.left
                right = test.comparators[0]

                if isinstance(left, ast.Name):
                    var_name = left.id
                    values = self._extract_literal_values(right)
                    if values:
                        return (var_name, values)

        return None

    @post(lambda result: result is None or len(result) > 0)
    def _extract_literal_values(self, node: ast.expr) -> list[str | int] | None:
        """
        Extract literal values from tuple/list/set.

        >>> import ast
        >>> detector = LiteralDetector()
        >>> node = ast.parse("('a', 'b', 'c')", mode="eval").body
        >>> detector._extract_literal_values(node)
        ['a', 'b', 'c']
        """
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = []
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(
                    elt.value, (str, int)
                ):
                    values.append(elt.value)
                else:
                    return None  # Non-literal value
            return values
        return None

    @pre(lambda self, values: len(values) > 0)
    @post(lambda result: result in Confidence)
    def _calculate_confidence(self, values: list[str | int]) -> Confidence:
        """
        Calculate confidence based on value characteristics.

        >>> detector = LiteralDetector()
        >>> detector._calculate_confidence(["debug", "info", "warning", "error"])
        <Confidence.HIGH: 'high'>
        """
        # High confidence for small sets of strings
        if all(isinstance(v, str) for v in values) and len(values) <= 5:
            return Confidence.HIGH

        # Medium confidence for larger sets or mixed types
        if len(values) <= 8:
            return Confidence.MEDIUM

        return Confidence.LOW

    @pre(lambda self, var_name, values: len(var_name) > 0 and len(values) > 0)
    @post(lambda result: "not in" in result)
    def _format_check(self, var_name: str, values: list[str | int]) -> str:
        """
        Format the membership check for display.

        >>> detector = LiteralDetector()
        >>> detector._format_check("level", ["debug", "info"])
        "if level not in ('debug', 'info'): raise"
        """
        formatted_values = ", ".join(repr(v) for v in values[:4])
        if len(values) > 4:
            formatted_values += ", ..."
        return f"if {var_name} not in ({formatted_values}): raise"

    @pre(lambda self, _var_name, values: len(_var_name) > 0 and len(values) > 0)
    @post(lambda result: "Literal[" in result)
    def _format_literal(self, _var_name: str, values: list[str | int]) -> str:
        """
        Format the Literal type suggestion.

        >>> detector = LiteralDetector()
        >>> detector._format_literal("level", ["debug", "info", "error"])
        "Literal['debug', 'info', 'error']"
        """
        formatted_values = ", ".join(repr(v) for v in values[:5])
        if len(values) > 5:
            formatted_values += ", ..."
        return f"Literal[{formatted_values}]"
