"""DX-94 integration tests for deferred MCP full-guard lifecycle."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from invar.mcp import handlers
from invar.mcp.guard_runs import GuardRunRegistry

pytestmark = pytest.mark.anyio


def _payload(
    *,
    status: str = "passed",
    errors: int = 0,
    warnings: int = 0,
    include_review_trigger: bool = False,
) -> dict[str, object]:
    findings: list[dict[str, object]] = []
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
            "files_checked": 12,
            "errors": errors,
            "warnings": warnings,
            "infos": 0,
        },
    }


class _FakeRegistry:
    async def start(self, *, cmd: list[str], path: str, changed: bool, timeout_reason: str):
        del cmd, changed
        assert path == "."
        return SimpleNamespace(
            run_id="grd_test_123",
            accepted_at="2026-03-09T00:00:00Z",
            timeout_reason=timeout_reason,
        )

    async def status(self, run_id: str) -> dict[str, object]:
        return {"status": "running", "run_id": run_id}

    async def wait(self, run_id: str, wait_ms: int) -> dict[str, object]:
        return {"status": "complete", "run_id": run_id, "wait_ms": wait_ms}


async def test_changed_true_remains_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """DX-94: changed=true path must preserve synchronous behavior."""
    captured: dict[str, list[str]] = {}

    async def fake_execute(cmd: list[str], timeout: int = 600):
        del timeout
        captured["cmd"] = cmd
        return [handlers.TextContent(type="text", text="sync")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    async def fail_start(**kwargs):
        raise AssertionError(f"Deferred start should not be called: {kwargs}")

    monkeypatch.setattr(handlers.GUARD_RUNS, "start", fail_start)

    result = await handlers._run_guard({"path": ".", "changed": True})

    assert len(result) == 1
    assert result[0].text == "sync"
    assert "--changed" in captured["cmd"]
    assert "--all" not in captured["cmd"]


async def test_changed_false_defers_when_estimate_exceeds_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DX-94: changed=false defers with run handle for long scans."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())
    monkeypatch.setattr(handlers, "_should_defer_full_scan", lambda path, args, budget: True)

    result = await handlers._run_guard({"path": ".", "changed": False})

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["status"] == "deferred"
    assert payload["run_id"] == "grd_test_123"
    assert payload["mode"] == "full_scan"
    assert payload["changed"] is False
    assert payload["timeout_reason"] == "estimated_duration_exceeds_sync_budget"


async def test_guard_status_and_wait_handlers_use_run_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DX-94: status/wait endpoints return JSON lifecycle envelopes."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())

    status_result = await handlers._run_guard_status({"run_id": "grd_abc"})
    wait_result = await handlers._run_guard_wait({"run_id": "grd_abc", "wait_ms": 20000})

    status_payload = json.loads(status_result[0].text)
    wait_payload = json.loads(wait_result[0].text)

    assert status_payload == {"status": "running", "run_id": "grd_abc"}
    assert wait_payload["status"] == "complete"
    assert wait_payload["run_id"] == "grd_abc"
    assert wait_payload["wait_ms"] == 10000


async def test_guard_run_registry_completes_with_summary_contract() -> None:
    """DX-94: completion report preserves summary keys required by UX."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def fake_run_guard_command(cmd: list[str]) -> dict[str, object]:
        del cmd
        await asyncio.sleep(0.01)
        return _payload(status="passed", errors=0, warnings=2, include_review_trigger=True)

    registry._run_guard_command = fake_run_guard_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    first = await registry.status(run.run_id)
    final = await registry.wait(run.run_id, wait_ms=100)

    assert first["status"] in {"deferred", "running"}
    assert final["status"] == "complete"
    assert final["report"] == {
        "ok": True,
        "errors": 0,
        "warnings": 2,
        "infos": 0,
        "files_checked": 12,
        "review_suggested": True,
    }


async def test_guard_run_registry_failed_envelope() -> None:
    """DX-94: failed runs return explicit failure envelope."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def failing_command(cmd: list[str]) -> dict[str, object]:
        del cmd
        raise RuntimeError("CrossHair subprocess exited non-zero")

    registry._run_guard_command = failing_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=100)
    assert final["status"] == "failed"
    assert final["error_kind"] == "execution_error"
    assert "CrossHair subprocess exited non-zero" in final["message"]


async def test_guard_run_registry_expiry_semantics() -> None:
    """DX-94: terminal run state expires and reports explicit expiry."""
    registry = GuardRunRegistry(retention_seconds=0, max_runtime_seconds=30)

    async def fake_run_guard_command(cmd: list[str]) -> dict[str, object]:
        del cmd
        return _payload()

    registry._run_guard_command = fake_run_guard_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    await registry.wait(run.run_id, wait_ms=100)
    await asyncio.sleep(0.01)
    expired = await registry.status(run.run_id)

    assert expired["status"] == "expired"


async def test_guard_run_registry_cancellation_semantics_for_stale_run() -> None:
    """DX-94: stale running jobs transition to cancelled deterministically."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=0)

    gate = asyncio.Event()

    async def hanging_command(cmd: list[str]) -> dict[str, object]:
        del cmd
        await gate.wait()
        return _payload()

    registry._run_guard_command = hanging_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    await asyncio.sleep(0.01)
    cancelled = await registry.status(run.run_id)

    gate.set()

    assert cancelled["status"] == "cancelled"
    assert cancelled["error_kind"] == "run_expired"
