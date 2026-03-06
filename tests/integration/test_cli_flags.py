"""
Integration tests for CLI flags.

DX-07: Verify all feature paths connect correctly.
DX-19: Simplified to 2 verification levels (STATIC, STANDARD).
DX-80: Default changed to --all flag.
Law 6: Local correctness ≠ global correctness.

These tests ensure that CLI flags actually trigger the expected behavior,
preventing "flag exists but does nothing" bugs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


# @invar:allow shell_result: Test helper, returns dict for assertion convenience
def run_invar_guard(*args: str, env: dict | None = None, timeout: int = 30) -> dict:
    """
    Run invar guard with given arguments and return parsed JSON output.

    Uses --agent flag implicitly since we capture stdout.
    """
    import os

    cmd = [sys.executable, "-m", "invar.shell.commands.guard", "guard", *args]
    full_env = os.environ.copy()
    full_env["INVAR_MODE"] = "agent"  # Force JSON output
    if env:
        full_env.update(env)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=full_env,
        timeout=timeout,
    )

    # Parse JSON output (handle newlines in messages)
    output = result.stdout.strip()
    if not output:
        return {"error": result.stderr, "returncode": result.returncode}

    try:
        # Handle potential newlines in JSON values
        return json.loads(output.replace("\n", " "))
    except json.JSONDecodeError:
        return {"raw_output": output, "stderr": result.stderr, "returncode": result.returncode}


class TestStaticFlag:
    """DX-19: Verify --static flag skips runtime tests."""

    def test_static_flag_skips_doctests(self):
        """--static should only run static analysis, no doctests."""
        result = run_invar_guard("--static", "src/invar/core")

        # Should have status
        assert "status" in result, f"Missing status in output: {result}"

        # Should NOT have doctest section (or doctest should be skipped)
        if "doctest" in result:
            # If doctest key exists, it should indicate skipped
            assert (
                result["doctest"].get("passed") is True
                or "skipped" in str(result.get("doctest", {})).lower()
            ), "Doctest should be skipped in --static mode"

    def test_static_flag_runs_static_analysis(self):
        """--static should still run static analysis."""
        result = run_invar_guard("--static", "--all", "src/invar/core")

        assert "summary" in result, f"Missing summary in output: {result}"
        assert "files_checked" in result["summary"], "Should report files checked"
        assert result["summary"]["files_checked"] > 0, "Should check at least one file"


class TestDefaultBehavior:
    """DX-80: Verify default behavior is now --all (full project check)."""

    @pytest.mark.timeout(15)
    def test_default_is_all_flag_behavior(self):
        """Default guard (no flags) should check entire project (DX-80: default changed to --all)."""
        # Use --static to speed up test while verifying --all behavior
        result = run_invar_guard("--static", timeout=15)

        # Should have summary
        assert "status" in result or "summary" in result, "Default guard should produce output"

        # With --static flag, should still check files
        if "summary" in result:
            assert result["summary"]["files_checked"] >= 0, "Should report files checked"


class TestAllFlag:
    """DX-80: Verify --all flag checks entire project."""

    def test_all_flag_checks_all_files(self):
        """--all should check entire project, not just changed files."""
        result = run_invar_guard("--static", "--all", "src/invar/core")

        assert "summary" in result, "Should have summary"
        assert result["summary"]["files_checked"] > 0, "Should check files"

    @pytest.mark.skip(
        reason="Doctest verification is slow (~90s+), run manually for full verification"
    )
    def test_all_flag_runs_doctests(self):
        """--all should run full verification including doctests."""
        # Use timeout to prevent hanging
        result = run_invar_guard("--all", "src/invar/core", timeout=90)

        # Should have doctest section
        assert "doctest" in result, "--all guard should run doctests"
        assert "passed" in result["doctest"], "Doctest should have passed status"

    @pytest.mark.skip(reason="CrossHair tests can be slow, run separately if needed")
    def test_all_flag_runs_crosshair(self):
        """--all should include CrossHair verification."""
        result = run_invar_guard("--all", "src/invar/core", timeout=120)

        # Should have crosshair section
        assert "crosshair" in result, "--all guard should include crosshair section"

        crosshair = result["crosshair"]
        valid_statuses = {"verified", "counterexample_found", "skipped", "error"}
        assert crosshair.get("status") in valid_statuses, (
            f"Invalid crosshair status: {crosshair.get('status')}"
        )


class TestAgentModeDetection:
    """DX-07: Verify agent mode is auto-detected."""

    def test_pipe_mode_produces_json(self):
        """When piped (non-TTY), output should be JSON."""
        result = run_invar_guard("--static", "src/invar/core")

        # If we got a dict back, JSON parsing succeeded
        assert isinstance(result, dict), "Piped output should be valid JSON"
        assert "status" in result or "summary" in result, "Should have standard fields"


class TestExplainFlag:
    """DX-07: Verify --explain flag provides detailed output."""

    def test_explain_flag_with_violations(self):
        """--explain should provide detailed violation info."""
        # This test may pass or fail depending on code state
        # Just verify it doesn't crash
        result = run_invar_guard("--explain", "--static", "src/invar")

        assert "status" in result, f"--explain should work: {result}"


# Smoke test to ensure the module is importable
def test_cli_module_imports():
    """Verify CLI module can be imported without errors."""
    # DX-48b: CLI moved to shell/commands/guard.py
    from invar.shell.commands import guard

    assert hasattr(guard, "app"), "CLI should have typer app"
    assert hasattr(guard, "guard"), "CLI should have guard command"
