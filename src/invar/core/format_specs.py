"""
Format-driven property testing specifications.

DX-28: Format specifications for generating realistic test data
that matches production formats, enabling property tests to catch
semantic bugs like inverted filter conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deal import post, pre


@dataclass
class FormatSpec:
    """Base specification for a data format.

    A FormatSpec describes the structure of data used in a function,
    enabling Hypothesis to generate realistic test cases.

    Examples:
        >>> spec = FormatSpec(name="simple")
        >>> spec.name
        'simple'
    """

    name: str
    description: str = ""


@dataclass
class LineFormat(FormatSpec):
    """Specification for line-based text formats.

    Examples:
        >>> spec = LineFormat(
        ...     name="log_line",
        ...     prefix_pattern="<timestamp>",
        ...     separator=": ",
        ...     keywords=["error", "warning", "info"]
        ... )
        >>> spec.separator
        ': '
    """

    prefix_pattern: str = ""
    separator: str = ""
    keywords: list[str] = field(default_factory=list)
    suffix_pattern: str = ""


@dataclass
class CrossHairOutputSpec(FormatSpec):
    """Specification for CrossHair verification output format.

    CrossHair outputs counterexamples in a specific format:
    `file.py:line: error: ErrorType when calling func(args)`

    This spec enables generating realistic CrossHair output for testing
    counterexample extraction logic.

    Examples:
        >>> spec = CrossHairOutputSpec()
        >>> spec.name
        'crosshair_output'
        >>> ": error:" in spec.error_marker
        True
    """

    name: str = "crosshair_output"
    description: str = "CrossHair symbolic verification output"

    # Format components
    file_pattern: str = r"[a-z_]+\.py"
    line_pattern: str = r"\\d+"
    error_marker: str = ": error:"
    error_types: list[str] = field(
        default_factory=lambda: [
            "IndexError",
            "KeyError",
            "ValueError",
            "TypeError",
            "AssertionError",
            "ZeroDivisionError",
            "AttributeError",
        ]
    )

    @pre(lambda self, filename, line, error_type, function, args: self.error_marker and line > 0)
    @post(lambda result: isinstance(result, str) and len(result) > 0)
    def format_counterexample(
        self,
        filename: str = "test.py",
        line: int = 1,
        error_type: str = "AssertionError",
        function: str = "func",
        args: str = "x=0",
    ) -> str:
        """
        Generate a counterexample line in CrossHair format.

        Examples:
            >>> spec = CrossHairOutputSpec()
            >>> line = spec.format_counterexample("foo.py", 42, "ValueError", "bar", "x=-1")
            >>> line
            'foo.py:42: error: ValueError when calling bar(x=-1)'
            >>> ": error:" in line
            True
        """
        return f"{filename}:{line}: error: {error_type} when calling {function}({args})"

    @pre(lambda self, count, include_success, include_errors: count >= 0 and (not include_errors or (len(self.error_types) > 0 and bool(self.error_marker))))
    @post(lambda result: isinstance(result, list))
    def generate_output(
        self,
        count: int = 3,
        include_success: bool = True,
        include_errors: bool = True,
    ) -> list[str]:
        """
        Generate sample CrossHair output with counterexamples.

        Examples:
            >>> spec = CrossHairOutputSpec()
            >>> output = spec.generate_output(count=2, include_success=False, include_errors=True)
            >>> len([l for l in output if ": error:" in l])
            2
            >>> all(": error:" in line for line in output if line)
            True
        """
        lines: list[str] = []

        if include_success:
            lines.append("Checking module...")

        if include_errors:
            for i in range(count):
                error_type = self.error_types[i % len(self.error_types)]
                lines.append(
                    self.format_counterexample(
                        f"file{i}.py", i + 1, error_type, f"func{i}", f"x={i}"
                    )
                )

        if include_success:
            lines.append("")  # Empty line at end

        return lines


@dataclass
class PytestOutputSpec(FormatSpec):
    """Specification for pytest output format.

    Examples:
        >>> spec = PytestOutputSpec()
        >>> spec.name
        'pytest_output'
    """

    name: str = "pytest_output"
    description: str = "pytest test runner output"

    passed_marker: str = "PASSED"
    failed_marker: str = "FAILED"
    error_marker: str = "ERROR"
    separator: str = "::"


# Pre-built specs for common formats
CROSSHAIR_SPEC = CrossHairOutputSpec()
PYTEST_SPEC = PytestOutputSpec()


@post(lambda result: all(isinstance(line, str) and line.strip() for line in result))  # Non-empty strings
def extract_by_format(text: str, spec: CrossHairOutputSpec) -> list[str]:
    """
    Extract lines matching a format specification.

    This is a reference implementation showing how FormatSpec
    can be used to create format-aware extraction.

    Examples:
        >>> spec = CrossHairOutputSpec()
        >>> text = "info\\nfile.py:1: error: Bug\\nok"
        >>> extract_by_format(text, spec)
        ['file.py:1: error: Bug']
    """
    return [
        line.strip()
        for line in text.split("\n")
        if line.strip() and spec.error_marker in line.lower()
    ]
