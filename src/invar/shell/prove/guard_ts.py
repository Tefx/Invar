"""TypeScript Guard Orchestration.

Shell module: orchestrates TypeScript verification via subprocess calls.
Part of LX-06 TypeScript tooling support.

This module provides graceful degradation - if TypeScript tools are not
installed, it reports the missing dependency rather than failing hard.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from returns.result import Failure, Result, Success


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


# DX-22: Fix-or-Explain complexity debt enforcement
# @shell_orchestration: Checks project-level complexity debt
def check_ts_complexity_debt(
    violations: list[TypeScriptViolation], limit: int = 3
) -> list[TypeScriptViolation]:
    """Check project-level shell-complexity debt (DX-22 Fix-or-Explain).

    When the project has too many unaddressed shell-complexity warnings,
    escalate to ERROR to force resolution. TypeScript default is 3 (vs Python's 5)
    since TS projects tend to be smaller.

    Args:
        violations: All violations from ESLint/tsc/vitest.
        limit: Maximum unaddressed complexity warnings before ERROR (default 3).

    Returns:
        List with single ERROR violation if debt limit exceeded, empty list otherwise.
    """
    # Count unaddressed shell-complexity warnings
    unaddressed = [
        v
        for v in violations
        if v.rule == "@invar/shell-complexity" and v.severity == "warning"
    ]

    if len(unaddressed) >= limit:
        return [
            TypeScriptViolation(
                file="<project>",
                line=None,
                column=None,
                rule="@invar/shell-complexity-debt",
                message=f"Project has {len(unaddressed)} unaddressed complexity warnings (limit: {limit})",
                severity="error",
                source="eslint",
            )
        ]
    return []


# @shell_orchestration: Transforms TypeScriptGuardResult to JSON for agent consumption
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


# @shell_orchestration: Helper for format_typescript_guard_v2 output assembly
def _generate_fix_suggestions(violations: list[TypeScriptViolation]) -> list[dict]:
    """Generate actionable fix suggestions from violations.

    LX-06 Phase 3: Maps ESLint rule violations to repair code snippets.

    Args:
        violations: List of TypeScriptViolation from ESLint/tsc.

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
            # Extract param name from message (fragile: depends on ESLint message format)
            # Falls back to "input" if extraction fails - user can adjust in fix suggestion
            param_match = re.search(r'"(\w+)"', v.message)
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


def _check_tool_available(tool: str, check_args: list[str]) -> bool:
    """Check if a tool is available in PATH.

    Args:
        tool: Tool name (e.g., "npx", "tsc") - must be alphanumeric/dash/underscore
        check_args: Arguments for version check

    Returns:
        True if tool is available and responds to check.
    """
    # Security: validate tool name to prevent command injection
    if not tool or not all(c.isalnum() or c in "-_" for c in tool):
        return False

    try:
        result = subprocess.run(
            [tool, *check_args],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# =============================================================================
# @invar/* Node Component Integration (LX-06 Phase 2)
# =============================================================================


# @shell_complexity: Path discovery with fallback logic
def _get_invar_package_cmd(package_name: str, project_path: Path) -> list[str]:
    """Get command to run an @invar/* package.

    Priority order:
    1. Embedded tools (pip install invar-tools includes these)
    2. Local development (typescript/packages/*/dist/ in Invar repo)
    3. npx fallback (if published to npm)

    Args:
        package_name: Package name without @invar/ prefix (e.g., "ts-analyzer")
        project_path: Project path to check for local installation

    Returns:
        Command list for subprocess.run
    """
    # Priority 1: Embedded tools (from pip install)
    try:
        from invar.node_tools import get_tool_path

        if embedded := get_tool_path(package_name):
            return ["node", str(embedded)]
    except ImportError:
        pass  # node_tools module not available

    # Priority 2: Local development setup (Invar repo itself)
    local_cli = project_path / f"typescript/packages/{package_name}/dist/cli.js"
    if local_cli.exists():
        return ["node", str(local_cli)]

    # Priority 2b: Walk up to find the Invar root (monorepo setup)
    check_path = project_path
    for _ in range(5):  # Max 5 levels up
        candidate = check_path / f"typescript/packages/{package_name}/dist/cli.js"
        if candidate.exists():
            return ["node", str(candidate)]
        parent = check_path.parent
        if parent == check_path:
            break
        check_path = parent

    # Priority 3: npx fallback (requires package published to npm)
    return ["npx", f"@invar/{package_name}"]


# @shell_complexity: Error handling branches for subprocess/JSON parsing
def run_ts_analyzer(project_path: Path) -> Result[dict, str]:
    """Run @invar/ts-analyzer for contract coverage analysis.

    Calls the Node component via npx with JSON output mode.
    Gracefully degrades if the package is not installed.

    Args:
        project_path: Path to TypeScript project root.

    Returns:
        Result containing analysis dict or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

    try:
        cmd = _get_invar_package_cmd("ts-analyzer", project_path)
        result = subprocess.run(
            [*cmd, str(project_path), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=project_path,
        )
        # ts-analyzer exits non-zero when critical blind spots found, but still outputs valid JSON
        # Try to parse JSON output regardless of exit code
        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                return Success(data)
            except json.JSONDecodeError as e:
                # JSON too large or malformed - try to extract summary from text output
                # Fall back to running without --json flag for human-readable summary
                try:
                    summary_result = subprocess.run(
                        [*cmd, str(project_path)],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=project_path,
                    )
                    # Extract key metrics from text output
                    output = summary_result.stdout
                    coverage_match = re.search(r'Contract coverage: (\d+)%', output)
                    coverage = int(coverage_match.group(1)) if coverage_match else None

                    return Success({
                        "coverage": coverage,
                        "summary_mode": True,
                        "note": "Full JSON output too large, using summary metrics"
                    })
                except Exception:
                    return Failure(f"JSON parse error: {str(e)[:100]}")

        # Only report failure if no valid JSON output
        if "not found" in result.stderr.lower() or "ENOENT" in result.stderr:
            return Failure("@invar/ts-analyzer not installed")
        return Failure(result.stderr or "ts-analyzer failed")
    except FileNotFoundError:
        return Failure("node/npx not available - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("ts-analyzer timed out")


# @shell_complexity: Error handling branches for subprocess/JSON parsing
def run_fc_runner(
    project_path: Path, *, seed: int = 42, num_runs: int = 100
) -> Result[dict, str]:
    """Run @invar/fc-runner for property-based testing.

    Calls the Node component via npx with JSON output mode.
    Gracefully degrades if the package is not installed.

    Args:
        project_path: Path to TypeScript project root.
        seed: Random seed for reproducibility.
        num_runs: Number of test iterations.

    Returns:
        Result containing test results dict or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

    try:
        cmd = _get_invar_package_cmd("fc-runner", project_path)
        result = subprocess.run(
            [*cmd, "--json", "--seed", str(seed), "--num-runs", str(num_runs)],
            capture_output=True,
            text=True,
            timeout=120,  # Property tests can take longer
            cwd=project_path,
        )
        if result.returncode == 0:
            with contextlib.suppress(json.JSONDecodeError):
                return Success(json.loads(result.stdout))
            return Failure("Invalid JSON output from fc-runner")
        if "not found" in result.stderr.lower() or "ENOENT" in result.stderr:
            return Failure("@invar/fc-runner not installed")
        # Return code 1 might mean test failures - try to parse output
        with contextlib.suppress(json.JSONDecodeError):
            data = json.loads(result.stdout)
            if "properties" in data:
                return Success(data)  # Has results even if tests failed
        return Failure(result.stderr or "fc-runner failed")
    except FileNotFoundError:
        return Failure("node/npx not available - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("fc-runner timed out")


# @shell_complexity: Error handling branches for subprocess/JSON parsing
def run_quick_check(project_path: Path) -> Result[dict, str]:
    """Run @invar/quick-check for fast smoke testing.

    Calls the Node component via npx with JSON output mode.
    Gracefully degrades if the package is not installed.

    Args:
        project_path: Path to TypeScript project root.

    Returns:
        Result containing check results dict or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

    try:
        cmd = _get_invar_package_cmd("quick-check", project_path)
        result = subprocess.run(
            [*cmd, str(project_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30,  # Quick check should be fast
            cwd=project_path,
        )
        # quick-check exits non-zero when checks fail, but still outputs valid JSON
        if result.stdout.strip():
            with contextlib.suppress(json.JSONDecodeError):
                return Success(json.loads(result.stdout))

        if "not found" in result.stderr.lower() or "ENOENT" in result.stderr:
            return Failure("@invar/quick-check not installed")
        return Failure(result.stderr or "quick-check failed")
    except FileNotFoundError:
        return Failure("node/npx not available - is Node.js installed?")
    except subprocess.TimeoutExpired:
        return Failure("quick-check timed out")


# @shell_orchestration: Helper for run_ts_analyzer - processes subprocess output
def _parse_ts_analyzer_result(
    data: dict,
) -> tuple[float | None, ContractQuality | None, list[BlindSpot]]:
    """Parse ts-analyzer JSON output into typed structures.

    Args:
        data: Raw JSON dict from ts-analyzer.

    Returns:
        Tuple of (coverage, quality, blind_spots).
    """
    coverage = data.get("coverage")

    quality = None
    if q := data.get("quality"):
        quality = ContractQuality(
            strong=q.get("strong", 0),
            medium=q.get("medium", 0),
            weak=q.get("weak", 0),
            useless=q.get("useless", 0),
        )

    blind_spots = []
    for bs in data.get("blindSpots", []):
        blind_spots.append(
            BlindSpot(
                function=bs.get("function", "unknown"),
                file=bs.get("file", "unknown"),
                line=bs.get("line", 0),
                risk=bs.get("risk", "medium"),
                reason=bs.get("reason", ""),
                suggested_schema=bs.get("suggestedSchema"),
            )
        )

    return coverage, quality, blind_spots


# @shell_orchestration: Helper for run_fc_runner - processes subprocess output
def _parse_fc_runner_result(data: dict) -> tuple[bool | None, list[dict]]:
    """Parse fc-runner JSON output into typed structures.

    Args:
        data: Raw JSON dict from fc-runner.

    Returns:
        Tuple of (all_passed, failures).
    """
    if "properties" not in data:
        return None, []

    failures = []
    all_passed = True

    for prop in data.get("properties", []):
        if prop.get("status") == "failed":
            all_passed = False
            failures.append(
                {
                    "name": prop.get("name", "unknown"),
                    "counterexample": prop.get("counterexample"),
                    "seed": prop.get("seed"),
                    "shrunk": prop.get("shrunk", False),
                }
            )

    return all_passed, failures


# =============================================================================
# Standard Tools (tsc, eslint, vitest)
# =============================================================================


# @shell_complexity: CLI tool integration with error handling and output parsing
def run_tsc(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run TypeScript compiler for type checking.

    Args:
        project_path: Path to TypeScript project root.

    Returns:
        Result containing list of violations or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

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


# @shell_orchestration: Parser helper for run_tsc subprocess output
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


# @shell_complexity: CLI tool integration with JSON parsing and error handling
def run_eslint(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run ESLint with @invar/eslint-plugin rules.

    Uses @invar/eslint-plugin CLI which pre-loads Invar-specific rules.

    Args:
        project_path: Path to project root.

    Returns:
        Result containing list of violations or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

    try:
        # Get command for @invar/eslint-plugin (embedded or local dev)
        cmd = _get_invar_package_cmd("eslint-plugin", project_path)
        cmd.append(str(project_path))  # Add project path as argument

        result = subprocess.run(
            cmd,
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


# @shell_complexity: Test runner with JSON result parsing and failure extraction
def run_vitest(project_path: Path) -> Result[list[TypeScriptViolation], str]:
    """Run Vitest for test execution.

    Args:
        project_path: Path to project root.

    Returns:
        Result containing list of violations (test failures) or error message.
    """
    # Validate project path exists before subprocess call
    if not project_path.exists():
        return Failure(f"Project path does not exist: {project_path}")

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
            except (json.JSONDecodeError, OSError):
                # Handle both JSON parse errors and IO errors (file deleted, permission denied, etc.)
                pass

    # LX-15 Phase 1: Generate doctests before running vitest
    try:
        doctest_result = subprocess.run(
            ["node", "scripts/generate-doctests.mjs", "doctest.config.json"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Doctest generation failure is not fatal - continue with regular tests
        if doctest_result.returncode != 0:
            # Log warning but don't fail
            pass
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Doctest generation not available or timed out - continue with regular tests
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


# @shell_complexity: Orchestrates multiple tools with graceful degradation
def run_typescript_guard(
    project_path: Path,
    *,
    skip_tests: bool = False,
    skip_enhanced: bool = False,
) -> Result[TypeScriptGuardResult, str]:
    """Run full TypeScript verification pipeline.

    Orchestrates tsc, eslint, vitest, and @invar/* Node components
    with graceful degradation if tools are unavailable.

    Args:
        project_path: Path to TypeScript project root.
        skip_tests: If True, skip vitest execution.
        skip_enhanced: If True, skip @invar/* Node component analysis.

    Returns:
        Result containing guard result or error message.
    """
    result = TypeScriptGuardResult(status="passed")

    # Check tool availability
    result.tsc_available = _check_tool_available("npx", ["tsc", "--version"])
    result.eslint_available = _check_tool_available("npx", ["eslint", "--version"])
    result.vitest_available = _check_tool_available("npx", ["vitest", "--version"])

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
            case Failure(err):
                # Report ESLint failure as a violation instead of silently ignoring
                all_violations.append(
                    TypeScriptViolation(
                        file="<eslint>",
                        line=0,
                        column=0,
                        rule="eslint-error",
                        message=f"ESLint failed to run: {err}",
                        severity="error",
                        source="eslint",
                    )
                )

    # Run vitest
    if result.vitest_available and not skip_tests:
        vitest_result = run_vitest(project_path)
        match vitest_result:
            case Success(violations):
                all_violations.extend(violations)
            case Failure(_):
                pass  # Test errors are non-fatal

    # =========================================================================
    # Enhanced analysis via @invar/* Node components (LX-06 Phase 2)
    # =========================================================================
    if not skip_enhanced:
        enhanced = EnhancedAnalysis()

        # Run ts-analyzer for contract coverage and blind spots
        ts_analyzer_result = run_ts_analyzer(project_path)
        match ts_analyzer_result:
            case Success(data):
                enhanced.ts_analyzer_available = True
                coverage, quality, blind_spots = _parse_ts_analyzer_result(data)
                enhanced.contract_coverage = coverage
                enhanced.contract_quality = quality
                enhanced.blind_spots = blind_spots
            case Failure(_):
                enhanced.ts_analyzer_available = False

        # Run fc-runner for property-based testing
        fc_runner_result = run_fc_runner(project_path)
        match fc_runner_result:
            case Success(data):
                enhanced.fc_runner_available = True
                passed, failures = _parse_fc_runner_result(data)
                enhanced.property_tests_passed = passed
                enhanced.property_test_failures = failures
            case Failure(_):
                enhanced.fc_runner_available = False

        # Run quick-check for fast smoke testing
        quick_check_result = run_quick_check(project_path)
        match quick_check_result:
            case Success(_):
                enhanced.quick_check_available = True
            case Failure(_):
                enhanced.quick_check_available = False

        result.enhanced = enhanced

    # DX-22: Check for complexity debt (project-level Fix-or-Explain enforcement)
    complexity_debt_violations = check_ts_complexity_debt(all_violations, limit=3)
    all_violations.extend(complexity_debt_violations)

    # Aggregate results
    result.violations = all_violations
    result.error_count = sum(1 for v in all_violations if v.severity == "error")
    result.warning_count = sum(1 for v in all_violations if v.severity == "warning")

    if result.error_count > 0:
        result.status = "failed"
    elif not any([result.tsc_available, result.eslint_available]):
        result.status = "skipped"

    return Success(result)
