"""Regression tests for MCP full-guard support.

These tests focus on:
1. Full-project call that previously timed out at request layer
2. Changed-only control path (existing, baseline)
3. Targeted-path control path
4. Result/error behavior for long-running scans per chosen model
5. Schema/protocol-level tests for contract changes

Key insight: Isolate request-layer timeout behavior from guard-rule correctness.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from invar.mcp import handlers
from invar.mcp.guard_runs import GuardRunRegistry

pytestmark = pytest.mark.anyio


# ============================================================================
# Helper Functions
# ============================================================================


def _make_payload(
    *,
    status: str = "passed",
    errors: int = 0,
    warnings: int = 0,
    files_checked: int = 12,
    include_review_trigger: bool = False,
) -> dict:
    """Create a mock guard payload matching the expected schema."""
    findings = []
    if include_review_trigger:
        findings.append({"rule": "review_suggested"})
    return {
        "status": status,
        "static": {
            "passed": errors == 0,
            "errors": errors,
            "warnings": warnings,
            "infos": 0,
            "findings": findings,
        },
        "summary": {
            "files_checked": files_checked,
            "errors": errors,
            "warnings": warnings,
            "infos": 0,
        },
    }


class _FakeRegistry:
    """Fake registry for testing deferred execution."""

    def __init__(self, start_response: dict | None = None):
        self._start_response = start_response or {
            "run_id": "grd_test_123",
            "accepted_at": "2026-03-09T00:00:00Z",
            "timeout_reason": "estimated_duration_exceeds_sync_budget",
        }
        self._status_response = {"status": "running", "run_id": "grd_test_123"}
        self._wait_response = {"status": "complete", "run_id": "grd_test_123"}

    async def start(self, **kwargs):
        return SimpleNamespace(**self._start_response)

    async def status(self, run_id: str) -> dict:
        return self._status_response

    async def wait(self, run_id: str, wait_ms: int) -> dict:
        return self._wait_response


# ============================================================================
# Test 1: Full-project call that previously timed out at request layer
# ============================================================================


async def test_full_project_scan_defers_without_hanging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full-project scan should return deferred response without hanging.

    This is the key regression test: previously, full-project scans could
    timeout at the request layer. Now they should return immediately with
    a deferred handle.
    """
    # Use fake registry to avoid actual filesystem operations
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())

    # Force deferral by making the estimator return a value > budget
    monkeypatch.setattr(
        handlers,
        "_should_defer_full_scan",
        lambda path, args, budget: True,
    )

    # This should NOT hang - it should return immediately with deferred status
    result = await handlers._run_guard({"path": ".", "changed": False})

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["status"] == "deferred"
    assert "run_id" in payload
    assert payload["mode"] == "full_scan"
    assert payload["changed"] is False


async def test_full_project_scan_runs_sync_when_estimate_within_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full-project scan should run synchronously when estimate is within budget."""
    captured_cmd = {}

    async def fake_execute(cmd, timeout=600):
        captured_cmd["cmd"] = cmd
        return [handlers.TextContent(type="text", text='{"status": "passed", "summary": {}}')]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    # Force no deferral
    monkeypatch.setattr(
        handlers,
        "_should_defer_full_scan",
        lambda path, args, budget: False,
    )

    result = await handlers._run_guard({"path": ".", "changed": False})

    assert len(result) == 1
    # Should have run the command, not deferred
    assert "--all" in captured_cmd["cmd"]


# ============================================================================
# Test 2: Changed-only control path (baseline)
# ============================================================================


async def test_changed_only_runs_synchronously(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changed-only path should always run synchronously - baseline behavior."""
    captured_cmd = {}

    async def fake_execute(cmd, timeout=600):
        captured_cmd["cmd"] = cmd
        return [handlers.TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    # Changed=True should NEVER defer
    result = await handlers._run_guard({"path": ".", "changed": True})

    assert len(result) == 1
    assert "--changed" in captured_cmd["cmd"]
    assert "--all" not in captured_cmd["cmd"]


async def test_changed_only_with_various_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changed-only should work with various path inputs."""
    captured_cmd = {}

    async def fake_execute(cmd, timeout=600):
        captured_cmd["cmd"] = cmd
        return [handlers.TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    # Test with explicit path
    result = await handlers._run_guard({"path": "src/core", "changed": True})
    assert len(result) == 1
    assert "src/core" in captured_cmd["cmd"]


# ============================================================================
# Test 3: Targeted-path control path
# ============================================================================


async def test_specific_path_full_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Full scan on specific path should follow full scan behavior."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())
    monkeypatch.setattr(
        handlers,
        "_should_defer_full_scan",
        lambda path, args, budget: True,
    )

    result = await handlers._run_guard({"path": "src/invar/core", "changed": False})

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["status"] == "deferred"
    assert payload["path"] == "src/invar/core"


async def test_targeted_path_changed_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Targeted path with changed=True should run synchronously."""
    captured_cmd = {}

    async def fake_execute(cmd, timeout=600):
        captured_cmd["cmd"] = cmd
        return [handlers.TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    result = await handlers._run_guard({"path": "tests/", "changed": True})

    assert len(result) == 1
    assert "--changed" in captured_cmd["cmd"]


# ============================================================================
# Test 4: Result/error behavior for long-running scans
# ============================================================================


async def test_deferred_run_complete_with_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deferred run should return proper summary when complete."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def fake_run_guard_command(cmd):
        import asyncio

        await asyncio.sleep(0.01)
        return _make_payload(errors=0, warnings=2, include_review_trigger=True)

    registry._run_guard_command = fake_run_guard_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=5000)

    assert final["status"] == "complete"
    assert final["report"]["ok"] is True
    assert final["report"]["errors"] == 0
    assert final["report"]["warnings"] == 2
    assert final["report"]["review_suggested"] is True


async def test_deferred_run_failure_returns_error_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed deferred run should return proper error envelope."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def failing_command(cmd):
        from invar.mcp.guard_runs import GuardWrapperInstabilityError

        raise GuardWrapperInstabilityError(1, "subprocess exit code 1")

    registry._run_guard_command = failing_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=1000)

    assert final["status"] == "failed"
    assert final["error_kind"] == "wrapper_instability"
    assert final["classification"] == "tooling_parity_wrapper_instability"
    assert final["accepted_verification_path"]["command"] == "uvx invar-tools guard --all"
    assert final["subprocess_exit_code"] == 1


async def test_deferred_run_timeout_returns_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Long-running deferred run that exceeds max runtime should be cancelled."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=0)  # Immediate expiry

    async def hanging_command(cmd):
        import asyncio

        await asyncio.sleep(10)  # Will exceed max_runtime_seconds=0

        return _make_payload()

    registry._run_guard_command = hanging_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    # Wait a tiny bit then check status
    import asyncio

    await asyncio.sleep(0.01)
    status = await registry.status(run.run_id)

    assert status["status"] == "cancelled"
    assert status["error_kind"] == "run_expired"


async def test_deferred_run_expired_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expired run should return explicit failed+run_expired status."""
    registry = GuardRunRegistry(retention_seconds=0, max_runtime_seconds=30)

    async def fast_command(cmd):
        return _make_payload()

    registry._run_guard_command = fast_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    # Wait for completion
    await registry.wait(run.run_id, wait_ms=100)

    # Immediately check - should be expired due to retention_seconds=0
    import asyncio

    await asyncio.sleep(0.01)
    status = await registry.status(run.run_id)

    assert status["status"] == "failed"
    assert status["error_kind"] == "run_expired"


async def test_unknown_run_id_returns_run_not_found() -> None:
    """Unknown run IDs should return explicit failed+run_not_found envelope."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    status = await registry.status("grd_missing")

    assert status["status"] == "failed"
    assert status["error_kind"] == "run_not_found"


# ============================================================================
# Test 5: Schema/protocol-level tests
# ============================================================================


async def test_deferred_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deferred response should match expected schema."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())
    monkeypatch.setattr(
        handlers,
        "_should_defer_full_scan",
        lambda path, args, budget: True,
    )

    result = await handlers._run_guard({"path": ".", "changed": False})

    payload = json.loads(result[0].text)

    # Required fields per DX-94 spec
    assert payload["status"] == "deferred"
    assert "run_id" in payload
    assert payload["mode"] == "full_scan"
    assert "path" in payload
    assert payload["changed"] is False
    assert "accepted_at" in payload
    assert "poll_after_ms" in payload
    assert "timeout_reason" in payload


async def test_guard_status_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard status response should match expected schema."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())

    result = await handlers._run_guard_status({"run_id": "grd_test_123"})

    payload = json.loads(result[0].text)

    # Status should have run_id and status
    assert "run_id" in payload
    assert "status" in payload


async def test_guard_wait_response_schema_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard wait response for complete run should match schema."""
    # Use a real registry with a fast fake command
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def fake_run_guard_command(cmd):
        import asyncio

        await asyncio.sleep(0.01)
        return _make_payload(errors=0, warnings=2)

    registry._run_guard_command = fake_run_guard_command
    monkeypatch.setattr(handlers, "GUARD_RUNS", registry)

    # Start a run and wait for it
    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="test",
    )

    result = await handlers._run_guard_wait({"run_id": run.run_id, "wait_ms": 5000})

    payload = json.loads(result[0].text)

    assert payload["status"] == "complete"
    assert "run_id" in payload
    assert "report" in payload
    # Report should have standard fields
    assert "ok" in payload["report"]
    assert "errors" in payload["report"]
    assert "warnings" in payload["report"]


async def test_guard_wait_response_schema_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard wait response for failed run should match schema."""
    fake_registry = _FakeRegistry()
    fake_registry._wait_response = {
        "status": "failed",
        "run_id": "grd_test_123",
        "error_kind": "wrapper_instability",
        "message": "Test error",
        "classification": "tooling_parity_wrapper_instability",
        "accepted_verification_path": {"command": "uvx invar-tools guard --all"},
    }
    monkeypatch.setattr(handlers, "GUARD_RUNS", fake_registry)

    result = await handlers._run_guard_wait({"run_id": "grd_test_123", "wait_ms": 5000})

    payload = json.loads(result[0].text)

    assert payload["status"] == "failed"
    assert payload["error_kind"] == "wrapper_instability"
    assert payload["classification"] == "tooling_parity_wrapper_instability"
    assert payload["accepted_verification_path"]["command"] == "uvx invar-tools guard --all"
    assert payload["message"] == "Test error"


async def test_sync_full_scan_failure_surfaces_authoritative_cli_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synchronous changed=false failures must classify wrapper instability explicitly."""

    class _FailureResult:
        def __init__(self) -> None:
            self.returncode = 1
            self.stdout = ""
            self.stderr = "subprocess exit code 1"

    monkeypatch.setattr(handlers, "_should_defer_full_scan", lambda path, args, budget: False)
    monkeypatch.setattr(handlers.subprocess, "run", lambda *args, **kwargs: _FailureResult())

    result = await handlers._run_guard({"path": ".", "changed": False})

    payload = json.loads(result[0].text)
    assert payload["status"] == "failed"
    assert payload["error_kind"] == "wrapper_instability"
    assert payload["classification"] == "tooling_parity_wrapper_instability"
    assert payload["accepted_verification_path"]["command"] == "uvx invar-tools guard --all"


# ============================================================================
# Test 6: Edge cases and error handling
# ============================================================================


async def test_invalid_path_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid path should return error, not hang or crash."""
    result = await handlers._run_guard({"path": "-e rm -rf /", "changed": True})

    assert len(result) == 1
    assert "Error" in result[0].text
    assert "cannot start with '-'" in result[0].text


async def test_path_with_shell_chars_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Path with shell characters should return error."""
    result = await handlers._run_guard({"path": "; rm -rf /", "changed": True})

    assert len(result) == 1
    assert "Error" in result[0].text
    assert "forbidden character" in result[0].text


async def test_sync_budget_ms_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    """sync_budget_ms parameter should be respected."""
    captured_budget = {}

    def capture_budget(path, args, budget):
        captured_budget["budget"] = budget
        return True  # Always defer

    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())
    monkeypatch.setattr(handlers, "_should_defer_full_scan", capture_budget)

    # Custom budget
    await handlers._run_guard({"path": ".", "changed": False, "sync_budget_ms": 5000})

    assert captured_budget["budget"] == 5000


async def test_guard_status_requires_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard status should require run_id."""
    result = await handlers._run_guard_status({})

    assert len(result) == 1
    assert "Error" in result[0].text
    assert "run_id" in result[0].text


async def test_guard_wait_requires_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard wait should require run_id."""
    result = await handlers._run_guard_wait({})

    assert len(result) == 1
    assert "Error" in result[0].text
    assert "run_id" in result[0].text


async def test_guard_wait_wait_ms_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard wait should bound wait_ms to 0-10000ms."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())

    # Test negative
    result = await handlers._run_guard_wait({"run_id": "grd_test_123", "wait_ms": -100})
    payload = json.loads(result[0].text)
    # Should still work, just bounded

    # Test too high
    result = await handlers._run_guard_wait({"run_id": "grd_test_123", "wait_ms": 50000})
    payload = json.loads(result[0].text)
    # Should still work, just bounded


# ============================================================================
# Test 7: Estimator behavior
# ============================================================================


async def test_estimate_contracts_only_lower_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """contracts_only mode should estimate faster scan."""
    from pathlib import Path

    # Mock to return known file count
    with patch.object(handlers, "_estimate_candidate_file_count", return_value=100):
        # With contracts_only=True
        estimate_with_contracts = handlers._estimate_full_scan_duration_ms(
            ".", {"contracts_only": True}
        )

        # With contracts_only=False
        estimate_without_contracts = handlers._estimate_full_scan_duration_ms(
            ".", {"contracts_only": False}
        )

        # contracts_only should be faster
        assert estimate_with_contracts < estimate_without_contracts


async def test_estimate_strict_mode_adds_overhead(monkeypatch: pytest.MonkeyPatch) -> None:
    """strict mode should estimate slightly slower."""
    with patch.object(handlers, "_estimate_candidate_file_count", return_value=100):
        # With strict=True
        estimate_with_strict = handlers._estimate_full_scan_duration_ms(
            ".", {"strict": True, "contracts_only": False}
        )

        # With strict=False
        estimate_without_strict = handlers._estimate_full_scan_duration_ms(
            ".", {"strict": False, "contracts_only": False}
        )

        # strict should add some overhead
        assert estimate_with_strict > estimate_without_strict


# ============================================================================
# Test 8: Integration - Full flow
# ============================================================================


async def test_full_flow_changed_false_deferred_then_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full flow: changed=False -> deferred -> wait -> complete."""
    # Create a real registry with fake command
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def successful_command(cmd):
        import asyncio

        await asyncio.sleep(0.01)
        return _make_payload(errors=0, warnings=1)

    registry._run_guard_command = successful_command

    # Patch GUARD_RUNS to use our registry
    monkeypatch.setattr(handlers, "GUARD_RUNS", registry)
    monkeypatch.setattr(
        handlers,
        "_should_defer_full_scan",
        lambda path, args, budget: True,
    )

    # Step 1: Initial call - should defer
    result = await handlers._run_guard({"path": ".", "changed": False})
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["status"] == "deferred"
    run_id = payload["run_id"]

    # Step 2: Wait for completion
    final = await handlers._run_guard_wait({"run_id": run_id, "wait_ms": 5000})
    final_payload = json.loads(final[0].text)
    assert final_payload["status"] == "complete"
    assert final_payload["report"]["ok"] is True
    assert final_payload["report"]["errors"] == 0
    assert final_payload["report"]["warnings"] == 1
