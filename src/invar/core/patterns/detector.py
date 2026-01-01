"""
Pattern Detector Protocol (DX-61).

Base protocol for all pattern detectors.
"""

import ast
from abc import abstractmethod
from typing import Protocol

from deal import post, pre

from invar.core.patterns.types import (
    Confidence,
    Location,
    PatternID,
    PatternSuggestion,
    Priority,
)


class PatternDetector(Protocol):
    """
    Protocol for pattern detectors.

    Each detector identifies opportunities for a specific functional pattern.
    Detectors analyze AST nodes and return suggestions with confidence levels.
    """

    # @invar:allow missing_doctest: Abstract property - no executable implementation
    @property
    @abstractmethod
    @post(lambda result: result in PatternID)
    def pattern_id(self) -> PatternID:
        """Unique identifier for this pattern."""
        ...

    # @invar:allow missing_doctest: Abstract property - no executable implementation
    @property
    @abstractmethod
    @post(lambda result: result in Priority)
    def priority(self) -> Priority:
        """Priority tier (P0 or P1)."""
        ...

    # @invar:allow missing_doctest: Abstract property - no executable implementation
    @property
    @abstractmethod
    @post(lambda result: len(result) > 0)
    def description(self) -> str:
        """Human-readable description of the pattern."""
        ...

    # @invar:allow missing_doctest: Abstract method - no executable implementation
    @abstractmethod
    @post(lambda result: all(isinstance(s, PatternSuggestion) for s in result))
    def detect(self, tree: ast.AST, file_path: str) -> list[PatternSuggestion]:
        """
        Analyze AST and return pattern suggestions.

        Args:
            tree: Parsed AST of the source file
            file_path: Path to the source file (for location reporting)

        Returns:
            List of pattern suggestions found in the file
        """
        ...


class BaseDetector:
    """
    Base class with common detection utilities.

    Provides helper methods for AST analysis that can be reused
    across different pattern detectors.
    """

    @post(lambda result: all(isinstance(name, str) and name for name, _ in result))
    def get_function_params(self, node: ast.FunctionDef) -> list[tuple[str, str | None]]:
        """
        Extract parameter names and type annotations from a function.

        >>> import ast
        >>> code = "def f(a: str, b: int, c): pass"
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> detector = BaseDetector()
        >>> params = detector.get_function_params(func)
        >>> params[0]
        ('a', 'str')
        >>> params[1]
        ('b', 'int')
        >>> params[2]
        ('c', None)
        """
        params = []
        for arg in node.args.args:
            name = arg.arg
            type_hint = None
            if arg.annotation:
                type_hint = self._annotation_to_str(arg.annotation)
            params.append((name, type_hint))
        return params

    @post(lambda result: isinstance(result, str) and len(result) > 0)
    def _annotation_to_str(self, annotation: ast.expr) -> str:
        """
        Convert an annotation AST node to string.

        >>> import ast
        >>> detector = BaseDetector()
        >>> detector._annotation_to_str(ast.Name(id="str"))
        'str'
        >>> detector._annotation_to_str(ast.Constant(value="str"))
        'str'
        """
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            # Handle generics like list[str]
            base = self._annotation_to_str(annotation.value)
            if isinstance(annotation.slice, ast.Tuple):
                args = ", ".join(self._annotation_to_str(e) for e in annotation.slice.elts)
            else:
                args = self._annotation_to_str(annotation.slice)
            return f"{base}[{args}]"
        elif isinstance(annotation, ast.Attribute):
            # Handle qualified names like typing.List
            parts = []
            node = annotation
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Handle X | Y union syntax
            left = self._annotation_to_str(annotation.left)
            right = self._annotation_to_str(annotation.right)
            return f"{left} | {right}"
        else:
            # Python 3.9+ always has ast.unparse (project requires 3.11+)
            result = ast.unparse(annotation)
            return result if result else "<unknown>"

    @pre(lambda self, params, type_name: len(type_name) > 0)
    @post(lambda result: result >= 0)
    def count_type_occurrences(
        self, params: list[tuple[str, str | None]], type_name: str
    ) -> int:
        """
        Count how many parameters have a specific type.

        >>> detector = BaseDetector()
        >>> params = [("a", "str"), ("b", "str"), ("c", "int")]
        >>> detector.count_type_occurrences(params, "str")
        2
        """
        return sum(1 for _, t in params if t == type_name)

    @post(lambda result: isinstance(result, bool))
    def has_match_statement(self, node: ast.FunctionDef) -> bool:
        """
        Check if function contains a match statement.

        >>> import ast
        >>> code = '''
        ... def f(x):
        ...     match x:
        ...         case 1: pass
        ... '''
        >>> tree = ast.parse(code)
        >>> func = tree.body[0]
        >>> detector = BaseDetector()
        >>> detector.has_match_statement(func)
        True
        """
        return any(isinstance(child, ast.Match) for child in ast.walk(node))

    @post(lambda result: all(isinstance(c, str) for c in result))
    def get_enum_cases(self, match_node: ast.Match) -> list[str]:
        """
        Extract case patterns from a match statement.

        >>> import ast
        >>> code = '''
        ... match status:
        ...     case Status.A: pass
        ...     case Status.B: pass
        ... '''
        >>> tree = ast.parse(code)
        >>> match = tree.body[0]
        >>> detector = BaseDetector()
        >>> cases = detector.get_enum_cases(match)
        >>> "Status.A" in cases
        True
        """
        cases = []
        for case in match_node.cases:
            pattern = case.pattern
            if isinstance(pattern, ast.MatchValue):
                cases.append(ast.unparse(pattern.value) if hasattr(ast, "unparse") else str(pattern.value))
            elif isinstance(pattern, ast.MatchAs) and pattern.pattern is None:
                cases.append("_")  # Wildcard
        return cases

    @pre(lambda self, pattern_id, priority, file_path, line, message, current_code, suggested_pattern, confidence, reference_pattern: line > 0)
    @post(lambda result: result.reference_file == ".invar/examples/functional.py")
    def make_suggestion(
        self,
        pattern_id: PatternID,
        priority: Priority,
        file_path: str,
        line: int,
        message: str,
        current_code: str,
        suggested_pattern: str,
        confidence: Confidence,
        reference_pattern: str,
    ) -> PatternSuggestion:
        """
        Create a pattern suggestion with standard reference file.

        >>> from invar.core.patterns.types import PatternID, Priority, Confidence
        >>> detector = BaseDetector()
        >>> suggestion = detector.make_suggestion(
        ...     pattern_id=PatternID.NEWTYPE,
        ...     priority=Priority.P0,
        ...     file_path="test.py",
        ...     line=10,
        ...     message="Test message",
        ...     current_code="def f(): pass",
        ...     suggested_pattern="NewType",
        ...     confidence=Confidence.HIGH,
        ...     reference_pattern="Pattern 1: NewType",
        ... )
        >>> suggestion.reference_file
        '.invar/examples/functional.py'
        """
        return PatternSuggestion(
            pattern_id=pattern_id,
            location=Location(file=file_path, line=line),
            message=message,
            confidence=confidence,
            priority=priority,
            current_code=current_code,
            suggested_pattern=suggested_pattern,
            reference_file=".invar/examples/functional.py",
            reference_pattern=reference_pattern,
        )
