"""DX-94 integration tests for deferred MCP full-guard lifecycle."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp.types import TextContent
from returns.result import Result, Success

from invar.mcp import handlers
from invar.mcp.guard_runs import GuardRunRegistry

pytestmark = pytest.mark.anyio


def _unwrap_success(result: Result[handlers.HandlerPayload, str]) -> list[TextContent]:
    assert isinstance(result, Success)
    payload = result.unwrap()
    assert isinstance(payload, list)
    return payload


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

    async def fake_execute(cmd: list[str], timeout: int = 600, **kwargs: object):
        del timeout, kwargs
        captured["cmd"] = cmd
        return Success([handlers.TextContent(type="text", text="sync")])

    monkeypatch.setattr(handlers, "_execute_command", fake_execute)

    async def fail_start(**kwargs):
        raise AssertionError(f"Deferred start should not be called: {kwargs}")

    monkeypatch.setattr(handlers.GUARD_RUNS, "start", fail_start)

    result = await handlers._run_guard({"path": ".", "changed": True})
    payload = _unwrap_success(result)

    assert len(payload) == 1
    assert payload[0].text == "sync"
    assert "--changed" in captured["cmd"]
    assert "--all" not in captured["cmd"]


async def test_changed_false_defers_when_estimate_exceeds_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DX-94: changed=false defers with run handle for long scans."""
    monkeypatch.setattr(handlers, "GUARD_RUNS", _FakeRegistry())
    monkeypatch.setattr(
        handlers, "_should_defer_full_scan", lambda path, args, budget: Success(True)
    )

    result = await handlers._run_guard({"path": ".", "changed": False})
    payload = _unwrap_success(result)

    assert len(payload) == 1
    payload = json.loads(payload[0].text)
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
    status_payload_list = _unwrap_success(status_result)
    wait_payload_list = _unwrap_success(wait_result)

    status_payload = json.loads(status_payload_list[0].text)
    wait_payload = json.loads(wait_payload_list[0].text)

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


async def test_guard_run_registry_updates_updated_at_while_running() -> None:
    """DX-94: running snapshots should expose liveness via updated_at."""
    registry = GuardRunRegistry(
        retention_seconds=30,
        max_runtime_seconds=30,
        heartbeat_interval_seconds=0.01,
    )

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

    # Ensure the background task has transitioned to running.
    snap1: dict[str, object] = {}
    for _ in range(50):
        snap1 = await registry.status(run.run_id)
        if snap1.get("status") == "running":
            break
        await asyncio.sleep(0.001)

    assert snap1.get("status") == "running"
    updated1 = snap1.get("updated_at")
    assert isinstance(updated1, str)

    await asyncio.sleep(0.03)
    snap2 = await registry.status(run.run_id)
    assert snap2.get("status") == "running"
    updated2 = snap2.get("updated_at")
    assert isinstance(updated2, str)

    gate.set()

    assert updated2 != updated1


async def test_guard_run_registry_failed_envelope() -> None:
    """DX-94: failed runs return explicit failure envelope."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def failing_command(cmd: list[str]) -> dict[str, object]:
        del cmd
        from invar.mcp.guard_runs import GuardWrapperInstabilityError

        raise GuardWrapperInstabilityError(1, "CrossHair subprocess exited non-zero")

    registry._run_guard_command = failing_command

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=100)
    assert final["status"] == "failed"
    assert final["error_kind"] == "wrapper_instability"
    assert final["classification"] == "tooling_parity_wrapper_instability"
    assert final["accepted_verification_path"]["command"] == "uvx invar-tools guard --all"
    assert final["subprocess_exit_code"] == 1


async def test_guard_run_registry_expiry_semantics() -> None:
    """DX-94: terminal run expiry maps to explicit failed+run_expired envelope."""
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

    assert expired["status"] == "failed"
    assert expired["error_kind"] == "run_expired"


async def test_guard_run_registry_unknown_run_id_semantics() -> None:
    """DX-94: unknown run IDs map to explicit failed+run_not_found envelope."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    unknown = await registry.status("grd_missing")

    assert unknown["status"] == "failed"
    assert unknown["error_kind"] == "run_not_found"


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


async def test_guard_run_registry_completes_with_mutation_in_summary() -> None:
    """DX-97: mutation data passes through deferred final-report parity."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    mutation_payload = _payload(
        status="passed",
        errors=0,
        warnings=1,
        include_review_trigger=False,
    )
    # Add DX-97 additive mutation output to the guard payload
    mutation_payload["mutation"] = {
        "total": 10,
        "killed": 8,
        "survived": 2,
        "timeout": 0,
        "error": 0,
        "score": 80.0,
        "passed": True,
        "eligible_files": 3,
        "ineligible_files": 1,
        "files_with_zero_sites": 1,
        "survivor_evidence": ["core.py:42:Add: x + y -> x - y"],
    }

    async def fake_run_guard_command_with_mutation(cmd: list[str]) -> dict[str, object]:
        del cmd
        await asyncio.sleep(0.01)
        return mutation_payload

    registry._run_guard_command = fake_run_guard_command_with_mutation

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=100)

    assert final["status"] == "complete"
    assert "mutation" in final["report"], "mutation key must be in final deferred report"
    mut = final["report"]["mutation"]
    assert mut["total"] == 10
    assert mut["killed"] == 8
    assert mut["survived"] == 2
    assert mut["eligible_files"] == 3
    assert mut["ineligible_files"] == 1
    assert mut["files_with_zero_sites"] == 1
    assert len(mut["survivor_evidence"]) == 1


async def test_guard_run_registry_completes_without_mutation_when_absent() -> None:
    """DX-97: no mutation key in final report when guard payload has none."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    async def fake_run_guard_command_no_mutation(cmd: list[str]) -> dict[str, object]:
        del cmd
        await asyncio.sleep(0.01)
        return _payload(status="passed", errors=0, warnings=0)

    registry._run_guard_command = fake_run_guard_command_no_mutation

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=100)

    assert final["status"] == "complete"
    assert "mutation" not in final["report"], (
        "mutation key must be absent from final deferred report when not present in payload"
    )


async def test_guard_run_registry_mutation_skipped_zero_sites_distinct() -> None:
    """DX-97: files_with_zero_sites distinguishes 'no sites' from 'all killed'."""
    registry = GuardRunRegistry(retention_seconds=30, max_runtime_seconds=30)

    payload = _payload(status="passed", errors=0, warnings=0)
    payload["mutation"] = {
        "total": 0,
        "killed": 0,
        "survived": 0,
        "timeout": 0,
        "error": 0,
        "score": 100.0,
        "passed": True,
        "eligible_files": 0,
        "ineligible_files": 0,
        "files_with_zero_sites": 3,
        "survivor_evidence": [],
    }

    async def fake_cmd(cmd: list[str]) -> dict[str, object]:
        del cmd
        await asyncio.sleep(0.01)
        return payload

    registry._run_guard_command = fake_cmd

    run = await registry.start(
        cmd=["python", "-m", "invar.shell.commands.guard", "guard", ".", "--all"],
        path=".",
        changed=False,
        timeout_reason="estimated_duration_exceeds_sync_budget",
    )

    final = await registry.wait(run.run_id, wait_ms=100)

    assert final["status"] == "complete"
    mut = final["report"]["mutation"]
    # Score is 100% (no sites = pass), but files_with_zero_sites shows it's a vacuous pass
    assert mut["score"] == 100.0
    assert mut["passed"] is True
    assert mut["files_with_zero_sites"] == 3
