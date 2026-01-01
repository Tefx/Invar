"""TypeScript tool output parsers (pure logic).

This module contains pure parsing functions for TypeScript tool outputs.
Part of LX-06 TypeScript tooling support.

All functions are pure - they transform strings to structured data
without any I/O operations.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from deal import post, pre


@dataclass(frozen=True)
class TSViolation:
    """A single TypeScript verification issue (immutable)."""

    file: str
    line: int | None
    column: int | None
    rule: str
    message: str
    severity: Literal["error", "warning", "info"]
    source: Literal["tsc", "eslint", "vitest"]


@pre(lambda line: "\n" not in line)  # Single line only
@post(lambda result: result is None or result.source == "tsc")
def parse_tsc_line(line: str) -> TSViolation | None:
    """Parse a single tsc output line into a violation.

    Args:
        line: Raw tsc output line.

    Returns:
        Parsed violation or None if parsing fails.

    Examples:
        >>> v = parse_tsc_line("src/foo.ts(10,5): error TS2322: Type mismatch")
        >>> v.file if v else None
        'src/foo.ts'
        >>> v.line if v else None
        10
        >>> v.rule if v else None
        'TS2322'
        >>> v.severity if v else None
        'error'

        >>> v = parse_tsc_line("src/bar.ts(1,1): warning TS6133: Unused var")
        >>> v.severity if v else None
        'warning'

        >>> parse_tsc_line("random text") is None
        True

        >>> parse_tsc_line("") is None
        True
    """
    # Pattern: file(line,col): severity TSxxxx: message
    pattern = r"^(.+?)\((\d+),(\d+)\): (error|warning) (TS\d+): (.+)$"
    match = re.match(pattern, line)

    if not match:
        return None

    file_path, line_num, col, severity, code, message = match.groups()

    return TSViolation(
        file=file_path,
        line=int(line_num),
        column=int(col),
        rule=code,
        message=message,
        severity="error" if severity == "error" else "warning",
        source="tsc",
    )


@pre(lambda output: output is not None)  # Accepts any string including empty
@post(lambda result: all(v.source == "tsc" for v in result))
def parse_tsc_output(output: str) -> list[TSViolation]:
    """Parse full tsc output into violations list.

    Args:
        output: Full tsc stdout output.

    Returns:
        List of parsed violations.

    Examples:
        >>> output = '''src/a.ts(1,1): error TS2322: Type A
        ... src/b.ts(2,3): warning TS6133: Unused
        ... Some other line'''
        >>> violations = parse_tsc_output(output)
        >>> len(violations)
        2
        >>> violations[0].file
        'src/a.ts'

        >>> parse_tsc_output("")
        []
    """
    violations: list[TSViolation] = []
    for line in output.splitlines():
        if ": error TS" in line or ": warning TS" in line:
            violation = parse_tsc_line(line)
            if violation:
                violations.append(violation)
    return violations


@pre(lambda output, base_path="": output is not None)  # Accepts any string including empty
@post(lambda result: all(v.source == "eslint" for v in result))
def parse_eslint_json(output: str, base_path: str = "") -> list[TSViolation]:
    """Parse ESLint JSON output into violations list.

    Args:
        output: ESLint JSON stdout output.
        base_path: Base path to make file paths relative (optional).

    Returns:
        List of parsed violations.

    Examples:
        >>> output = '''[{
        ...   "filePath": "/project/src/foo.ts",
        ...   "messages": [
        ...     {"line": 10, "column": 5, "severity": 2,
        ...      "ruleId": "no-unused-vars", "message": "Unused var"}
        ...   ]
        ... }]'''
        >>> violations = parse_eslint_json(output, "/project")
        >>> len(violations)
        1
        >>> violations[0].rule
        'no-unused-vars'
        >>> violations[0].severity
        'error'

        >>> parse_eslint_json("invalid json")
        []

        >>> parse_eslint_json("")
        []
    """
    violations: list[TSViolation] = []

    try:
        eslint_output = json.loads(output)
    except json.JSONDecodeError:
        return violations

    # ESLint output must be a list
    if not isinstance(eslint_output, list):
        return violations

    for file_result in eslint_output:
        # Each file result must be a dict
        if not isinstance(file_result, dict):
            continue

        file_path = file_result.get("filePath", "")

        # Make path relative if base_path provided
        if base_path and isinstance(file_path, str) and file_path.startswith(base_path):
            file_path = file_path[len(base_path) :].lstrip("/\\")

        messages = file_result.get("messages", [])
        if not isinstance(messages, list):
            continue

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            severity_num = msg.get("severity", 1)
            violations.append(
                TSViolation(
                    file=str(file_path),
                    line=msg.get("line"),
                    column=msg.get("column"),
                    rule=msg.get("ruleId") or "unknown",
                    message=str(msg.get("message", "")),
                    severity="error" if severity_num == 2 else "warning",
                    source="eslint",
                )
            )

    return violations


@pre(lambda output, base_path="": output is not None)  # Accepts any string including empty
@post(lambda result: all(v.source == "vitest" for v in result))
def parse_vitest_json(output: str, base_path: str = "") -> list[TSViolation]:
    """Parse Vitest JSON output into violations list.

    Args:
        output: Vitest JSON stdout output.
        base_path: Base path to make file paths relative (optional).

    Returns:
        List of violations (test failures only).

    Examples:
        >>> output = '''{
        ...   "testResults": [{
        ...     "name": "/project/tests/foo.test.ts",
        ...     "assertionResults": [
        ...       {"status": "failed", "title": "should work"}
        ...     ]
        ...   }]
        ... }'''
        >>> violations = parse_vitest_json(output, "/project")
        >>> len(violations)
        1
        >>> violations[0].rule
        'test_failure'

        >>> parse_vitest_json("invalid json")
        []

        >>> output_pass = '{"testResults": [{"name": "x", "assertionResults": [{"status": "passed", "title": "ok"}]}]}'
        >>> parse_vitest_json(output_pass)
        []
    """
    violations: list[TSViolation] = []

    try:
        vitest_output = json.loads(output)
    except json.JSONDecodeError:
        return violations

    # Vitest output must be a dict with testResults
    if not isinstance(vitest_output, dict):
        return violations

    test_results = vitest_output.get("testResults", [])
    if not isinstance(test_results, list):
        return violations

    for test_file in test_results:
        # Each test file must be a dict
        if not isinstance(test_file, dict):
            continue

        file_path = test_file.get("name", "")

        # Make path relative if base_path provided
        if base_path and isinstance(file_path, str) and file_path.startswith(base_path):
            file_path = file_path[len(base_path) :].lstrip("/\\")

        assertion_results = test_file.get("assertionResults", [])
        if not isinstance(assertion_results, list):
            continue

        for assertion in assertion_results:
            if not isinstance(assertion, dict):
                continue
            if assertion.get("status") == "failed":
                # Extract detailed failure message from failureMessages if available
                title = str(assertion.get("title", "Test failed"))
                failure_msgs = assertion.get("failureMessages", [])
                if isinstance(failure_msgs, list) and failure_msgs:
                    # Use first failure message, truncate if too long
                    detail = str(failure_msgs[0])[:200]
                    message = f"{title}: {detail}"
                else:
                    message = title
                violations.append(
                    TSViolation(
                        file=str(file_path),
                        line=None,
                        column=None,
                        rule="test_failure",
                        message=message,
                        severity="error",
                        source="vitest",
                    )
                )

    return violations
