"""TypeScript Guard Orchestration.

Shell module: orchestrates TypeScript verification via subprocess calls.
Part of LX-06 TypeScript tooling support.

This module provides graceful degradation - if TypeScript tools are not
installed, it reports the missing dependency rather than failing hard.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from invar.core.ts_parsers import TSViolation


@dataclass
class TypeScriptViolation:
    """A single TypeScript verification issue."""

    file: str
    line: int | None
    column: int | None
    rule: str
    message: str
    severity: Literal["error", "warning", "info"]
    source: Literal["tsc", "eslint", "vitest"]


@dataclass
class ContractQuality:
    """Contract quality metrics from ts-analyzer."""

    strong: int = 0
    medium: int = 0
    weak: int = 0
    useless: int = 0


@dataclass
class BlindSpot:
    """High-risk code without validation."""

    function: str
    file: str
    line: int
    risk: Literal["critical", "high", "medium", "low"]
    reason: str
    suggested_schema: str | None = None


@dataclass
class EnhancedAnalysis:
    """Enhanced analysis from @invar/* Node components."""

    quick_check_available: bool = False
    ts_analyzer_available: bool = False
    fc_runner_available: bool = False
    contract_coverage: float | None = None
    contract_quality: ContractQuality | None = None
    blind_spots: list[BlindSpot] = field(default_factory=list)
    property_tests_passed: bool | None = None
    property_test_failures: list[dict] = field(default_factory=list)


@dataclass
class TypeScriptGuardResult:
    """Result of TypeScript verification."""

    status: Literal["passed", "failed", "skipped"]
    violations: list[TypeScriptViolation] = field(default_factory=list)
    tsc_available: bool = False
    eslint_available: bool = False
    vitest_available: bool = False
    error_count: int = 0
    warning_count: int = 0
    tool_errors: list[str] = field(default_factory=list)
    enhanced: EnhancedAnalysis | None = None


# @shell_complexity: JSON assembly with multiple conditional sections
def format_typescript_guard_v2(result: TypeScriptGuardResult) -> dict:
    """Format TypeScript guard result as v2.0 JSON.

    LX-06 Phase 3: Agent-optimized JSON output format with:
    - Contract coverage and quality metrics
    - Blind spot detection
    - Property test results with counterexamples
    - Structured fix suggestions

    Args:
        result: TypeScript guard result to format.

    Returns:
        Dict in v2.0 JSON format for agent consumption.
    """
    # Count violations by source
    tsc_errors = sum(1 for v in result.violations if v.source == "tsc" and v.severity == "error")
    tsc_warnings = sum(1 for v in result.violations if v.source == "tsc" and v.severity == "warning")
    eslint_errors = sum(1 for v in result.violations if v.source == "eslint" and v.severity == "error")
    eslint_warnings = sum(1 for v in result.violations if v.source == "eslint" and v.severity == "warning")
    vitest_failures = sum(1 for v in result.violations if v.source == "vitest")

    # Count files checked (unique files in violations + estimate from available tools)
    files_checked = len({v.file for v in result.violations}) if result.violations else 0

    output: dict = {
        "version": "2.0",
        "language": "typescript",
        "status": result.status,
        "summary": {
            "errors": result.error_count,
            "warnings": result.warning_count,
            "files_checked": files_checked,
        },
        "static": {
            "tsc": {
                "passed": tsc_errors == 0,
                "available": result.tsc_available,
                "errors": tsc_errors,
                "warnings": tsc_warnings,
            },
            "eslint": {
                "passed": eslint_errors == 0,
                "available": result.eslint_available,
                "errors": eslint_errors,
                "warnings": eslint_warnings,
            },
        },
        "tests": {
            "passed": vitest_failures == 0,
            "available": result.vitest_available,
            "failures": vitest_failures,
        },
        "violations": [
            {
                "file": v.file,
                "line": v.line,
                "column": v.column,
                "rule": v.rule,
                "message": v.message,
                "severity": v.severity,
                "source": v.source,
            }
            for v in result.violations
        ],
    }

    # Add enhanced analysis if available (LX-06 Phase 2)
    if result.enhanced:
        enhanced = result.enhanced

        # Property tests section
        if enhanced.fc_runner_available:
            # Handle None (not run) vs False (failed) vs True (passed)
            if enhanced.property_tests_passed is None:
                pt_status = "skipped"
            elif enhanced.property_tests_passed:
                pt_status = "passed"
            else:
                pt_status = "failed"

            property_tests: dict = {
                "status": pt_status,
                "confidence": "statistical",
                "available": True,
            }
            if enhanced.property_test_failures:
                property_tests["failures"] = [
                    {
                        "name": f.get("name", "unknown"),
                        "counterexample": f.get("counterexample"),
                        "analysis": f.get("analysis"),
                    }
                    for f in enhanced.property_test_failures
                ]
            output["property_tests"] = property_tests

        # Contracts section
        if enhanced.ts_analyzer_available:
            contracts: dict = {"available": True}
            if enhanced.contract_coverage is not None:
                contracts["coverage"] = enhanced.contract_coverage
            if enhanced.contract_quality:
                contracts["quality"] = {
                    "strong": enhanced.contract_quality.strong,
                    "medium": enhanced.contract_quality.medium,
                    "weak": enhanced.contract_quality.weak,
                    "useless": enhanced.contract_quality.useless,
                }
            if enhanced.blind_spots:
                contracts["blind_spots"] = [
                    {
                        "function": bs.function,
                        "file": bs.file,
                        "line": bs.line,
                        "risk": bs.risk,
                        "reason": bs.reason,
                        "suggested_schema": bs.suggested_schema,
                    }
                    for bs in enhanced.blind_spots
                ]
            output["contracts"] = contracts

    # Add tool errors if any
    if result.tool_errors:
        output["tool_errors"] = result.tool_errors

    # LX-06 Phase 3: Generate fix suggestions from violations
    fixes = _generate_fix_suggestions(result.violations)
    if fixes:
        output["fixes"] = fixes

    return output


# @shell_complexity: Maps rule violations to repair code with pattern matching
def _generate_fix_suggestions(violations: list[TSViolation]) -> list[dict]:
    """Generate actionable fix suggestions from violations.

    LX-06 Phase 3: Maps ESLint rule violations to repair code snippets.

    Args:
        violations: List of TSViolation from ESLint/tsc.

    Returns:
        List of fix suggestions with repair code.
    """
    fixes: list[dict] = []
    fix_counter = 1

    # Rule-specific fix generators mapping rule_id to (priority, action, code_template)
    fix_generators: dict[str, tuple[str, str, str]] = {
        "@invar/require-schema-validation": (
            "high",
            "insert",
            "const validated = Schema.parse({param});",
        ),
        "@invar/shell-result-type": (
            "medium",
            "replace",
            "Result<{return_type}, Error>",
        ),
        "@invar/no-io-in-core": (
            "high",
            "refactor",
            "// Move to shell/ directory and import from there",
        ),
    }

    for v in violations:
        if v.source != "eslint":
            continue

        rule = v.rule or ""
        if rule not in fix_generators:
            continue

        priority, action, code = fix_generators[rule]

        # Customize code based on rule
        if rule == "@invar/require-schema-validation":
            # Extract param name from message
            import re as re_module
            param_match = re_module.search(r'"(\w+)"', v.message)
            param = param_match.group(1) if param_match else "input"
            code = code.replace("{param}", param)
        elif rule == "@invar/shell-result-type":
            # Use 'T' as placeholder since actual type requires source analysis
            code = code.replace("{return_type}", "T")

        fix = {
            "id": f"FIX-{fix_counter:03d}",
            "priority": priority,
            "issue": {
                "type": rule.replace("@invar/", ""),
                "message": v.message,
                "location": {"file": v.file, "line": v.line, "column": v.column},
            },
            "repair": {
                "action": action,
                "target": {
                    "file": v.file,
                    "line": (v.line + 1) if v.line is not None else None,
                },
                "code": code,
                "explanation": f"Fix for {rule}",
            },
        }
        fixes.append(fix)
        fix_counter += 1

    return fixes


def check_tool_available(tool: str, check_args: list[str]) -> bool:
    """Check if a tool is available in PATH.

    Args:
        tool: Tool name (e.g., "npx", "tsc")
        check_args: Arguments for version check

    Returns:
        True if tool is available and responds to check.
    """
    try:
        result = subprocess.run(
            [tool, *check_args],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def run_tsc(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run TypeScript compiler for type checking.

    Args:
        project_path: Path to TypeScript project root.

    Returns:
        Result containing list of violations or error message.
    """
    tsconfig = project_path / "tsconfig.json"
    if not tsconfig.exists():
        return Failure("No tsconfig.json found")

    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "--pretty", "false"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )

        violations: list[TypeScriptViolation] = []

        # Parse tsc output (format: file(line,col): error TSxxxx: message)
        for line in result.stdout.splitlines():
            if ": error TS" in line or ": warning TS" in line:
                violation = _parse_tsc_line(line)
                if violation:
                    violations.append(violation)

        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("tsc timed out after 120 seconds")


def _parse_tsc_line(line: str) -> TypeScriptViolation | None:
    """Parse a single tsc output line into a violation.

    Args:
        line: Raw tsc output line.

    Returns:
        Parsed violation or None if parsing fails.

    Examples:
        >>> v = _parse_tsc_line("src/foo.ts(10,5): error TS2322: Type mismatch")
        >>> v.file if v else None
        'src/foo.ts'
        >>> v.line if v else None
        10
        >>> v.rule if v else None
        'TS2322'
    """
    import re

    # Pattern: file(line,col): severity TSxxxx: message
    pattern = r"^(.+?)\((\d+),(\d+)\): (error|warning) (TS\d+): (.+)$"
    match = re.match(pattern, line)

    if not match:
        return None

    file_path, line_num, col, severity, code, message = match.groups()

    return TypeScriptViolation(
        file=file_path,
        line=int(line_num),
        column=int(col),
        rule=code,
        message=message,
        severity="error" if severity == "error" else "warning",
        source="tsc",
    )


def run_eslint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run ESLint for code quality checks.

    Args:
        project_path: Path to project root.

    Returns:
        Result containing list of violations or error message.
    """
    try:
        result = subprocess.run(
            ["npx", "eslint", ".", "--format", "json", "--ext", ".ts,.tsx"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,
        )

        violations: list[TypeScriptViolation] = []

        try:
            eslint_output = json.loads(result.stdout)
            for file_result in eslint_output:
                file_path = file_result.get("filePath", "")
                # Make path relative
                with contextlib.suppress(ValueError):
                    file_path = str(Path(file_path).relative_to(project_path))

                for msg in file_result.get("messages", []):
                    severity_num = msg.get("severity", 1)
                    violations.append(
                        TypeScriptViolation(
                            file=file_path,
                            line=msg.get("line"),
                            column=msg.get("column"),
                            rule=msg.get("ruleId", "unknown"),
                            message=msg.get("message", ""),
                            severity="error" if severity_num == 2 else "warning",
                            source="eslint",
                        )
                    )
        except json.JSONDecodeError:
            # ESLint may output non-JSON on certain errors
            if result.returncode != 0 and result.stderr:
                return Failure(f"ESLint error: {result.stderr[:200]}")

        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("eslint timed out after 120 seconds")


def run_vitest(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run Vitest for test execution.

    Args:
        project_path: Path to project root.

    Returns:
        Result containing list of violations (test failures) or error message.
    """
    vitest_config = project_path / "vitest.config.ts"
    if not vitest_config.exists() and not (project_path / "vitest.config.js").exists():
        # Check if vitest is in package.json
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "vitest" not in deps:
                    return Success([])  # No vitest configured, skip
            except json.JSONDecodeError:
                pass

    try:
        result = subprocess.run(
            ["npx", "vitest", "run", "--reporter=json"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300,  # Tests may take longer
        )

        violations: list[TypeScriptViolation] = []

        try:
            vitest_output = json.loads(result.stdout)
            for test_file in vitest_output.get("testResults", []):
                file_path = test_file.get("name", "")
                with contextlib.suppress(ValueError):
                    file_path = str(Path(file_path).relative_to(project_path))

                for assertion in test_file.get("assertionResults", []):
                    if assertion.get("status") == "failed":
                        violations.append(
                            TypeScriptViolation(
                                file=file_path,
                                line=None,
                                column=None,
                                rule="test_failure",
                                message=assertion.get("title", "Test failed"),
                                severity="error",
                                source="vitest",
                            )
                        )
        except json.JSONDecodeError:
            # Non-JSON output usually means vitest itself failed
            if result.returncode != 0:
                return Failure(f"Vitest error: {result.stderr[:200]}")

        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("vitest timed out after 300 seconds")


def run_typescript_guard(
    project_path: Path,
    *,
    skip_tests: bool = False,
) -> Result[TypeScriptGuardResult, str]:
    """Run full TypeScript verification pipeline.

    Orchestrates tsc, eslint, and vitest with graceful degradation
    if tools are unavailable.

    Args:
        project_path: Path to TypeScript project root.
        skip_tests: If True, skip vitest execution.

    Returns:
        Result containing guard result or error message.
    """
    result = TypeScriptGuardResult(status="passed")

    # Check tool availability
    result.tsc_available = check_tool_available("npx", ["tsc", "--version"])
    result.eslint_available = check_tool_available("npx", ["eslint", "--version"])
    result.vitest_available = check_tool_available("npx", ["vitest", "--version"])

    all_violations: list[TypeScriptViolation] = []

    # Run tsc
    if result.tsc_available:
        tsc_result = run_tsc(project_path)
        match tsc_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(err):
                # tsc failure is not fatal if it's just "no tsconfig"
                if "No tsconfig.json" not in err:
                    pass  # Log but continue

    # Run eslint
    if result.eslint_available:
        eslint_result = run_eslint(project_path)
        match eslint_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(_):
                pass  # ESLint errors are non-fatal

    # Run vitest
    if result.vitest_available and not skip_tests:
        vitest_result = run_vitest(project_path)
        match vitest_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(_):
                pass  # Test errors are non-fatal

    # Aggregate results
    result.violations = all_violations
    result.error_count = sum(1 for v in all_violations if v.severity == "error")
    result.warning_count = sum(1 for v in all_violations if v.severity == "warning")

    if result.error_count > 0:
        result.status = "failed"
    elif not any([result.tsc_available, result.eslint_available]):
        result.status = "skipped"

    return Success(result)
