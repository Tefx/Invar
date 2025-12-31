"""
NewType Pattern Detector (DX-61, P0).

Detects opportunities to use NewType for semantic clarity when
multiple parameters share the same primitive type.
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


class NewTypeDetector(BaseDetector):
    """
    Detect functions with 3+ parameters of the same primitive type.

    These are candidates for NewType to prevent parameter confusion.

    Detection logic:
    - Find functions with 3+ str/int/float params of same type
    - Exclude common patterns (e.g., *args, **kwargs)
    - Suggest NewType for semantic differentiation

    >>> import ast
    >>> detector = NewTypeDetector()
    >>> code = '''
    ... def process(user_id: str, order_id: str, product_id: str):
    ...     pass
    ... '''
    >>> tree = ast.parse(code)
    >>> suggestions = detector.detect(tree, "test.py")
    >>> len(suggestions) > 0
    True
    >>> suggestions[0].pattern_id == PatternID.NEWTYPE
    True
    """

    PRIMITIVE_TYPES: ClassVar[set[str]] = {"str", "int", "float", "bool", "bytes"}
    MIN_SAME_TYPE_PARAMS: ClassVar[int] = 3

    @property
    @post(lambda result: result == PatternID.NEWTYPE)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern.

        >>> NewTypeDetector().pattern_id
        <PatternID.NEWTYPE: 'newtype'>
        """
        return PatternID.NEWTYPE

    @property
    @post(lambda result: result == Priority.P0)
    def priority(self) -> Priority:
        """Priority tier.

        >>> NewTypeDetector().priority
        <Priority.P0: 'P0'>
        """
        return Priority.P0

    @property
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description.

        >>> len(NewTypeDetector().description) > 0
        True
        """
        return "Use NewType for semantic clarity with multiple same-type parameters"

    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Find functions with multiple parameters of the same primitive type.

        >>> import ast
        >>> detector = NewTypeDetector()
        >>> code = '''
        ... def good(a: str, b: int):
        ...     pass
        ... def bad(user_id: str, order_id: str, product_id: str):
        ...     pass
        ... '''
        >>> tree = ast.parse(code)
        >>> suggestions = detector.detect(tree, "test.py")
        >>> len(suggestions)
        1
        >>> "bad" in suggestions[0].current_code
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
        Check if function has multiple params of same primitive type.

        >>> import ast
        >>> detector = NewTypeDetector()
        >>> code = "def f(user_id: str, order_id: str, product_id: str): pass"
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> suggestion = detector._check_function(func, "test.py")
        >>> suggestion is not None
        True
        >>> suggestion.confidence == Confidence.HIGH
        True
        """
        params = self.get_function_params(node)

        # Skip if too few parameters
        if len(params) < self.MIN_SAME_TYPE_PARAMS:
            return None

        # Count occurrences of each primitive type
        for prim_type in self.PRIMITIVE_TYPES:
            count = self.count_type_occurrences(params, prim_type)
            if count >= self.MIN_SAME_TYPE_PARAMS:
                # Found opportunity
                matching_params = [name for name, t in params if t == prim_type]
                confidence = self._calculate_confidence(matching_params, node)

                return self.make_suggestion(
                    pattern_id=self.pattern_id,
                    priority=self.priority,
                    file_path=file_path,
                    line=node.lineno,
                    message=f"{count} '{prim_type}' params - consider NewType for semantic clarity",
                    current_code=self._format_signature(node),
                    suggested_pattern=self._suggest_newtypes(matching_params, prim_type),
                    confidence=confidence,
                    reference_pattern="Pattern 1: NewType for Semantic Clarity",
                )

        return None

    @pre(lambda self, param_names, _node: len(param_names) > 0)
    @post(lambda result: result in Confidence)
    def _calculate_confidence(
        self, param_names: list[str], _node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> Confidence:
        """
        Calculate confidence based on parameter naming patterns.

        Higher confidence if names suggest distinct entities (e.g., *_id patterns).

        >>> detector = NewTypeDetector()
        >>> import ast
        >>> func = ast.parse("def f(user_id, order_id, product_id): pass").body[0]
        >>> detector._calculate_confidence(["user_id", "order_id", "product_id"], func)
        <Confidence.HIGH: 'high'>
        """
        # High confidence if names follow *_id, *_name, or *_code patterns
        id_pattern = sum(1 for n in param_names if n.endswith(("_id", "_name", "_code", "_key")))
        if id_pattern >= 2:
            return Confidence.HIGH

        # Medium confidence for descriptive names
        if all(len(n) > 3 for n in param_names):
            return Confidence.MEDIUM

        # Low confidence for short/generic names
        return Confidence.LOW

    @post(lambda result: len(result) > 0 and "def " in result)
    def _format_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """
        Format function signature for display.

        >>> import ast
        >>> detector = NewTypeDetector()
        >>> func = ast.parse("def process(a: str, b: str): pass").body[0]
        >>> sig = detector._format_signature(func)
        >>> "process" in sig
        True
        """
        params = self.get_function_params(node)
        param_str = ", ".join(
            f"{name}: {t}" if t else name
            for name, t in params[:5]  # Limit for readability
        )
        if len(params) > 5:
            param_str += ", ..."
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({param_str})"

    @pre(lambda self, param_names, base_type: len(param_names) > 0 and len(base_type) > 0)
    @post(lambda result: "NewType" in result)
    def _suggest_newtypes(self, param_names: list[str], base_type: str) -> str:
        """
        Generate NewType suggestion for parameters.

        >>> detector = NewTypeDetector()
        >>> detector._suggest_newtypes(["user_id", "order_id"], "str")
        "NewType('UserId', str), NewType('OrderId', str)"
        """
        newtypes = []
        for name in param_names[:3]:  # Limit suggestions
            # Convert snake_case to PascalCase
            pascal = "".join(word.capitalize() for word in name.split("_"))
            newtypes.append(f"NewType('{pascal}', {base_type})")
        if len(param_names) > 3:
            newtypes.append("...")
        return ", ".join(newtypes)
