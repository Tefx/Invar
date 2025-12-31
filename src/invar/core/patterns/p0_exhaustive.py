"""
Exhaustive Match Pattern Detector (DX-61, P0).

Detects match statements on enums that don't use assert_never
for exhaustiveness checking.
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


class ExhaustiveMatchDetector(BaseDetector):
    """
    Detect non-exhaustive match statements on enums.

    These are candidates for assert_never pattern to ensure
    all cases are handled at compile time.

    Detection logic:
    - Find match statements
    - Check if wildcard case exists but doesn't use assert_never
    - Suggest adding assert_never for exhaustiveness

    >>> import ast
    >>> detector = ExhaustiveMatchDetector()
    >>> code = '''
    ... def handle(status: Status) -> str:
    ...     match status:
    ...         case Status.PENDING:
    ...             return "pending"
    ...         case Status.DONE:
    ...             return "done"
    ...         case _:
    ...             return "unknown"
    ... '''
    >>> tree = ast.parse(code)
    >>> suggestions = detector.detect(tree, "test.py")
    >>> len(suggestions) > 0
    True
    """

    @property
    @post(lambda result: result == PatternID.EXHAUSTIVE)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern.

        >>> ExhaustiveMatchDetector().pattern_id
        <PatternID.EXHAUSTIVE: 'exhaustive'>
        """
        return PatternID.EXHAUSTIVE

    @property
    @post(lambda result: result == Priority.P0)
    def priority(self) -> Priority:
        """Priority tier.

        >>> ExhaustiveMatchDetector().priority
        <Priority.P0: 'P0'>
        """
        return Priority.P0

    @property
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description.

        >>> len(ExhaustiveMatchDetector().description) > 0
        True
        """
        return "Use assert_never for exhaustive enum matching"

    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Find match statements with non-exhaustive patterns.

        >>> import ast
        >>> detector = ExhaustiveMatchDetector()
        >>> code = '''
        ... def f(x):
        ...     match x:
        ...         case A.ONE: return 1
        ...         case _: return 0
        ... '''
        >>> tree = ast.parse(code)
        >>> suggestions = detector.detect(tree, "test.py")
        >>> len(suggestions) > 0
        True
        """
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Match):
                suggestion = self._check_match(node, file_path)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    @pre(lambda self, node, file_path: len(file_path) > 0)
    def _check_match(
        self, node: ast.Match, file_path: str
    ) -> PatternSuggestion | None:
        """
        Check if match statement could benefit from assert_never.

        >>> import ast
        >>> detector = ExhaustiveMatchDetector()
        >>> code = '''
        ... match x:
        ...     case Status.A: pass
        ...     case _: pass
        ... '''
        >>> tree = ast.parse(code)
        >>> match = tree.body[0]
        >>> suggestion = detector._check_match(match, "test.py")
        >>> suggestion is not None
        True
        """
        has_wildcard = False
        uses_assert_never = False
        has_enum_patterns = False
        enum_cases = []

        for case in node.cases:
            pattern = case.pattern

            # Check for wildcard
            if isinstance(pattern, ast.MatchAs) and pattern.pattern is None:
                has_wildcard = True
                # Check if body uses assert_never
                uses_assert_never = self._uses_assert_never(case.body)

            # Check for enum-like patterns (e.g., Status.PENDING)
            elif isinstance(pattern, ast.MatchValue):
                if isinstance(pattern.value, ast.Attribute):
                    has_enum_patterns = True
                    enum_cases.append(ast.unparse(pattern.value) if hasattr(ast, "unparse") else "...")

        # Suggest if: has enum patterns + has wildcard + doesn't use assert_never
        if has_enum_patterns and has_wildcard and not uses_assert_never:
            confidence = self._calculate_confidence(enum_cases)

            return self.make_suggestion(
                pattern_id=self.pattern_id,
                priority=self.priority,
                file_path=file_path,
                line=node.lineno,
                message="Match has wildcard without assert_never - missing cases won't be caught",
                current_code=self._format_match_preview(enum_cases),
                suggested_pattern="case _: assert_never(x)  # Type error if cases missing",
                confidence=confidence,
                reference_pattern="Pattern 5: Exhaustive Match",
            )

        return None

    @post(lambda result: isinstance(result, bool))
    def _uses_assert_never(self, body: list[ast.stmt]) -> bool:
        """
        Check if body contains assert_never call.

        >>> import ast
        >>> detector = ExhaustiveMatchDetector()
        >>> body = ast.parse("assert_never(x)").body
        >>> detector._uses_assert_never(body)
        True
        """
        for stmt in body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                func = stmt.value.func
                if isinstance(func, ast.Name) and func.id == "assert_never":
                    return True
        return False

    @post(lambda result: result in Confidence)
    def _calculate_confidence(self, enum_cases: list[str]) -> Confidence:
        """
        Calculate confidence based on context.

        >>> detector = ExhaustiveMatchDetector()
        >>> detector._calculate_confidence(["Status.A", "Status.B", "Status.C"])
        <Confidence.HIGH: 'high'>
        """
        # High confidence if multiple enum cases from same type
        if len(enum_cases) >= 2:
            # Check if all from same enum
            prefixes = [c.split(".")[0] if "." in c else c for c in enum_cases]
            if len(set(prefixes)) == 1:
                return Confidence.HIGH

        # Medium confidence for any enum patterns
        if enum_cases:
            return Confidence.MEDIUM

        return Confidence.LOW

    @post(lambda result: "match" in result and "case" in result)
    def _format_match_preview(self, enum_cases: list[str]) -> str:
        """
        Format match statement preview.

        >>> detector = ExhaustiveMatchDetector()
        >>> detector._format_match_preview(["Status.A", "Status.B"])
        'match ...: case Status.A | Status.B | _: ...'
        """
        cases_str = " | ".join(enum_cases[:3])
        if len(enum_cases) > 3:
            cases_str += " | ..."
        return f"match ...: case {cases_str} | _: ..."
