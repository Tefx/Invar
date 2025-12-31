"""TypeScript Guard Orchestration.

Shell module: orchestrates TypeScript verification via subprocess calls.
Part of LX-06 TypeScript tooling support.

This module provides graceful degradation - if TypeScript tools are not
installed, it reports the missing dependency rather than failing hard.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 (used at runtime)
from typing import Literal

from returns.result import Failure, Result, Success

from invar.core.ts_parsers import (
    TSViolation,
    parse_eslint_json,
    parse_tsc_output,
    parse_vitest_json,
)


@dataclass
class TypeScriptGuardResult:
    """Result of TypeScript verification."""

    status: Literal["passed", "failed", "skipped"]
    violations: list[TSViolation] = field(default_factory=list)
    tsc_available: bool = False
    eslint_available: bool = False
    vitest_available: bool = False
    error_count: int = 0
    warning_count: int = 0
    tool_errors: list[str] = field(default_factory=list)  # Non-fatal tool errors


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


# @shell_complexity: Subprocess orchestration with error handling
def run_tsc(project_path: Path) -> Result[list[TSViolation], str]:
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

        # Delegate parsing to pure core function
        # Parse both stdout and stderr - tsc outputs to both
        violations = parse_tsc_output(result.stdout)
        violations.extend(parse_tsc_output(result.stderr))
        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("tsc timed out after 120 seconds")


# @shell_complexity: Subprocess orchestration with JSON parsing fallback
def run_eslint(project_path: Path) -> Result[list[TSViolation], str]:
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

        # Delegate parsing to pure core function
        violations = parse_eslint_json(result.stdout, str(project_path))

        # Check for non-JSON errors
        if not violations and result.returncode != 0 and result.stderr:
            return Failure(f"ESLint error: {result.stderr[:200]}")

        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("eslint timed out after 120 seconds")


# @shell_complexity: Subprocess orchestration with config detection
def run_vitest(project_path: Path) -> Result[list[TSViolation], str]:
    """Run Vitest for test execution.

    Args:
        project_path: Path to project root.

    Returns:
        Result containing list of violations (test failures) or error message.
    """
    import json

    vitest_config = project_path / "vitest.config.ts"
    vitest_config_js = project_path / "vitest.config.js"
    pkg_json = project_path / "package.json"

    # Check if vitest is configured
    has_vitest_config = vitest_config.exists() or vitest_config_js.exists()

    if not has_vitest_config:
        # No config file - check package.json for vitest dependency
        if not pkg_json.exists():
            return Success([])  # No package.json, skip vitest
        try:
            pkg = json.loads(pkg_json.read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "vitest" not in deps:
                return Success([])  # No vitest configured, skip
        except (json.JSONDecodeError, OSError):
            return Success([])  # Can't read package.json, skip vitest

    try:
        result = subprocess.run(
            ["npx", "vitest", "run", "--reporter=json"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300,  # Tests may take longer
        )

        # Delegate parsing to pure core function
        violations = parse_vitest_json(result.stdout, str(project_path))

        # Check for non-JSON errors
        if not violations and result.returncode != 0 and result.stderr:
            return Failure(f"Vitest error: {result.stderr[:200]}")

        return Success(violations)

    except FileNotFoundError:
        return Failure("npx not found - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("vitest timed out after 300 seconds")


# @shell_complexity: Multi-tool orchestration with graceful degradation
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
    # CRITICAL: Validate project_path exists and is a directory
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")
    if not project_path.is_dir():
        return Failure(f"Project path is not a directory: {project_path}")

    result = TypeScriptGuardResult(status="passed")

    # Check tool availability
    result.tsc_available = check_tool_available("npx", ["tsc", "--version"])
    result.eslint_available = check_tool_available("npx", ["eslint", "--version"])
    result.vitest_available = check_tool_available("npx", ["vitest", "--version"])

    all_violations: list[TSViolation] = []

    # Run tsc
    if result.tsc_available:
        tsc_result = run_tsc(project_path)
        match tsc_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(err):
                # tsc failure is not fatal if it's just "no tsconfig"
                if "No tsconfig.json" not in err:
                    result.tool_errors.append(f"tsc: {err}")

    # Run eslint
    if result.eslint_available:
        eslint_result = run_eslint(project_path)
        match eslint_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(err):
                result.tool_errors.append(f"eslint: {err}")

    # Run vitest
    if result.vitest_available and not skip_tests:
        vitest_result = run_vitest(project_path)
        match vitest_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(err):
                result.tool_errors.append(f"vitest: {err}")

    # Aggregate results
    result.violations = all_violations
    result.error_count = sum(1 for v in all_violations if v.severity == "error")
    result.warning_count = sum(1 for v in all_violations if v.severity == "warning")

    if result.error_count > 0:
        result.status = "failed"
    elif not any([result.tsc_available, result.eslint_available]):
        result.status = "skipped"

    return Success(result)
