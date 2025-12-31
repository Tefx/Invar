"""
Validation Pattern Detector (DX-61, P0).

Detects fail-fast validation patterns that could benefit from
error accumulation for better user experience.
"""

import ast
from typing import ClassVar

from deal import post, pre

from invar.core.patterns.detector import BaseDetector
from invar.core.patterns.types import (
    Confidence,
    PatternID,
    PatternSuggestion,
    Priority,
)


class ValidationDetector(BaseDetector):
    """
    Detect fail-fast validation that returns early on first error.

    These are candidates for error accumulation pattern.

    Detection logic:
    - Find functions with multiple early returns of error-like values
    - Look for patterns like: if condition: return Failure/raise
    - Suggest accumulating all errors before returning

    >>> import ast
    >>> detector = ValidationDetector()
    >>> code = '''
    ... def validate(data):
    ...     if "name" not in data:
    ...         return Failure("Missing name")
    ...     if "email" not in data:
    ...         return Failure("Missing email")
    ...     if "age" not in data:
    ...         return Failure("Missing age")
    ...     return Success(data)
    ... '''
    >>> tree = ast.parse(code)
    >>> suggestions = detector.detect(tree, "test.py")
    >>> len(suggestions) > 0
    True
    """

    MIN_EARLY_RETURNS: ClassVar[int] = 3
    ERROR_PATTERNS: ClassVar[set[str]] = {"Failure", "Err", "Error", "Left"}
    VALIDATION_KEYWORDS: ClassVar[set[str]] = {"validate", "check", "verify", "parse"}

    @property
    @post(lambda result: result == PatternID.VALIDATION)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern.

        >>> ValidationDetector().pattern_id
        <PatternID.VALIDATION: 'validation'>
        """
        return PatternID.VALIDATION

    @property
    @post(lambda result: result == Priority.P0)
    def priority(self) -> Priority:
        """Priority tier.

        >>> ValidationDetector().priority
        <Priority.P0: 'P0'>
        """
        return Priority.P0

    @property
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description.

        >>> len(ValidationDetector().description) > 0
        True
        """
        return "Use error accumulation instead of fail-fast validation"

    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Find functions with fail-fast validation patterns.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> code = '''
        ... def check_config(cfg):
        ...     if not cfg.get("host"):
        ...         return Failure("No host")
        ...     if not cfg.get("port"):
        ...         return Failure("No port")
        ...     if not cfg.get("user"):
        ...         return Failure("No user")
        ...     return Success(cfg)
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
        Check if function has fail-fast validation pattern.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> code = '''
        ... def validate(x):
        ...     if not x.a: return Failure("a")
        ...     if not x.b: return Failure("b")
        ...     if not x.c: return Failure("c")
        ...     return Success(x)
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> suggestion = detector._check_function(func, "test.py")
        >>> suggestion is not None
        True
        """
        early_returns = self._count_early_error_returns(node)

        if early_returns >= self.MIN_EARLY_RETURNS:
            confidence = self._calculate_confidence(node, early_returns)

            return self.make_suggestion(
                pattern_id=self.pattern_id,
                priority=self.priority,
                file_path=file_path,
                line=node.lineno,
                message=f"{early_returns} early error returns - consider error accumulation",
                current_code=self._format_function_preview(node),
                suggested_pattern="Collect all errors, return list[Error]",
                confidence=confidence,
                reference_pattern="Pattern 2: Validation for Error Accumulation",
            )

        return None

    @post(lambda result: result >= 0)
    def _count_early_error_returns(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> int:
        """
        Count early returns with error-like values inside if statements.

        Only counts if statements at the top level of the function body,
        not nested functions or lambdas.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> code = '''
        ... def f(x):
        ...     if not x.a: return Failure("a")
        ...     if not x.b: return Failure("b")
        ...     return Success(x)
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> detector._count_early_error_returns(func)
        2
        """
        count = 0

        # Only iterate direct children, not nested functions
        for stmt in node.body:
            count += self._count_if_error_returns(stmt)

        return count

    @post(lambda result: result >= 0)
    def _count_if_error_returns(self, stmt: ast.stmt) -> int:
        """
        Recursively count if statements with error returns, avoiding nested functions.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> stmt = ast.parse("if x: return Failure('e')").body[0]
        >>> detector._count_if_error_returns(stmt)
        1
        """
        count = 0

        if isinstance(stmt, ast.If):
            # Check if body has early error return
            for body_stmt in stmt.body:
                if isinstance(body_stmt, ast.Return) and self._is_error_return(body_stmt):
                    count += 1
                    break
            # Recurse into else/elif but NOT into nested functions
            for body_stmt in stmt.body:
                if not isinstance(body_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    count += self._count_if_error_returns(body_stmt)
            for else_stmt in stmt.orelse:
                if not isinstance(else_stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    count += self._count_if_error_returns(else_stmt)

        return count

    @post(lambda result: isinstance(result, bool))
    def _is_error_return(self, node: ast.Return) -> bool:
        """
        Check if return value looks like an error.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> ret = ast.parse("return Failure('error')").body[0].value
        >>> # This tests the return statement's value
        >>> detector._is_error_return(ast.Return(value=ret))
        True
        """
        if node.value is None:
            return False

        # Check for Failure(...), Err(...), etc.
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                return node.value.func.id in self.ERROR_PATTERNS
            if isinstance(node.value.func, ast.Attribute):
                return node.value.func.attr in self.ERROR_PATTERNS

        return False

    @pre(lambda self, node, early_returns: early_returns >= 0)
    @post(lambda result: result in Confidence)
    def _calculate_confidence(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, early_returns: int
    ) -> Confidence:
        """
        Calculate confidence based on function characteristics.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> func = ast.parse("def validate_config(x): pass").body[0]
        >>> detector._calculate_confidence(func, 3)
        <Confidence.HIGH: 'high'>
        """
        # High confidence if function name suggests validation
        func_name = node.name.lower()
        if any(kw in func_name for kw in self.VALIDATION_KEYWORDS):
            return Confidence.HIGH

        # High confidence if many early returns
        if early_returns >= 5:
            return Confidence.HIGH

        # Medium confidence for moderate early returns
        if early_returns >= 3:
            return Confidence.MEDIUM

        return Confidence.LOW

    @post(lambda result: len(result) > 0 and "def " in result)
    def _format_function_preview(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str:
        """
        Format function preview for display.

        >>> import ast
        >>> detector = ValidationDetector()
        >>> func = ast.parse("def validate(data): pass").body[0]
        >>> preview = detector._format_function_preview(func)
        >>> "validate" in preview
        True
        """
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        params = self.get_function_params(node)
        param_str = ", ".join(name for name, _ in params[:3])
        if len(params) > 3:
            param_str += ", ..."
        return f"{prefix} {node.name}({param_str})"
