"""Background run registry for deferred MCP guard execution.

DX-94 source: docs/proposals/DX-94-mcp-full-guard-support-model.md

Implements split-phase guard execution for large full scans:
- invar_guard(changed=false) may return deferred run handle
- status/wait endpoints track monotonic lifecycle
- bounded TTL retention prevents unbounded run-state growth
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from returns.result import Failure, Result, Success

RunStatus = Literal["deferred", "running", "complete", "failed", "cancelled"]

AUTHORITATIVE_FULL_SCAN_COMMAND = "uvx invar-tools guard --all"
WRAPPER_INSTABILITY_CLASSIFICATION = "tooling_parity_wrapper_instability"


class GuardWrapperInstabilityError(RuntimeError):
    """Raised when MCP wrapper path fails before semantic guard verdict."""

    def __init__(self, returncode: int, stderr: str) -> None:
        self.returncode = returncode
        self.stderr = stderr
        detail = stderr or "no stderr"
        super().__init__(f"MCP guard wrapper subprocess exit code {returncode}: {detail}")


# @shell_orchestration: Shared envelope keeps deferred/sync wrapper failures consistent
def build_wrapper_instability_envelope(
    *,
    run_id: str,
    path: str,
    changed: bool,
    subprocess_exit_code: int,
    stderr: str,
) -> Result[dict[str, Any], str]:
    """Build explicit tooling-parity envelope for wrapper failures."""
    return Success(
        {
            "status": "failed",
            "run_id": run_id,
            "error_kind": "wrapper_instability",
            "classification": WRAPPER_INSTABILITY_CLASSIFICATION,
            "path": path,
            "changed": changed,
            "subprocess_exit_code": subprocess_exit_code,
            "stderr": stderr,
            "accepted_verification_path": {
                "command": AUTHORITATIVE_FULL_SCAN_COMMAND,
                "reason": (
                    "When MCP wrapper fails but CLI full-scan passes, treat this as tooling-path "
                    "instability, not DX-91 semantic regression."
                ),
            },
        }
    )


def _utc_now() -> Result[datetime, str]:
    return Success(datetime.now(UTC))


def _iso(ts: datetime) -> Result[str, str]:
    return Success(ts.isoformat().replace("+00:00", "Z"))


# @shell_orchestration: MCP deferred guard JSON normalization (kept local for protocol parity)
# @shell_complexity: Character-level JSON newline escaping requires stateful scan
def _fix_json_newlines(text: str) -> Result[str, str]:
    """Fix unescaped newlines in JSON string values.

    Matches existing MCP parsing fallback in handlers.py.
    """
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == '"':
            result.append('"')
            i += 1
            while i < len(text):
                c = text[i]
                if c == "\\" and i + 1 < len(text):
                    result.append("\\")
                    result.append(text[i + 1])
                    i += 2
                elif c == '"':
                    result.append('"')
                    i += 1
                    break
                elif c == "\n" or c == "\r":
                    result.append("\\n")
                    i += 1
                else:
                    result.append(c)
                    i += 1
        else:
            result.append(text[i])
            i += 1
    return Success("".join(result))


# @shell_orchestration: MCP deferred guard JSON parsing (kept local for protocol parity)
# @shell_complexity: Fallback parse path preserves behavior for malformed newline-containing JSON
def _parse_guard_json(stdout: str) -> Result[dict[str, Any], str]:
    text = stdout.strip()
    if not text:
        return Failure("Guard command returned empty output")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        fixed = _fix_json_newlines(text)
        if isinstance(fixed, Failure):
            return Failure(fixed.failure())
        try:
            parsed = json.loads(fixed.unwrap())
        except json.JSONDecodeError:
            return Failure("Guard command returned invalid JSON output")

    if not isinstance(parsed, dict):
        return Failure("Guard command output must be a JSON object")
    return Success(parsed)


# @shell_orchestration: MCP deferred guard summary normalization (kept local for protocol parity)
# @shell_complexity: Review trigger detection branches over nested payload fields
def _review_suggested(payload: dict[str, Any]) -> Result[bool, str]:
    static = payload.get("static")
    if not isinstance(static, dict):
        return Success(False)

    findings = static.get("findings")
    if not isinstance(findings, list):
        return Success(False)

    for item in findings:
        if isinstance(item, dict) and item.get("rule") == "review_suggested":
            return Success(True)
    return Success(False)


# @shell_orchestration: MCP deferred guard report summarization (kept local for protocol parity)
# @shell_complexity: Summary normalization handles optional/malformed payload fields
def summarize_guard_payload(payload: dict[str, Any]) -> Result[dict[str, Any], str]:
    """Convert full guard payload to DX-94 final summary contract."""
    review_suggested = _review_suggested(payload)
    if isinstance(review_suggested, Failure):
        return Failure(review_suggested.failure())

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        summary = {}

    errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    infos = summary.get("infos", 0)
    files_checked = summary.get("files_checked", 0)
    status = payload.get("status")

    return Success(
        {
            "ok": status == "passed",
            "errors": int(errors) if isinstance(errors, int | float) else 0,
            "warnings": int(warnings) if isinstance(warnings, int | float) else 0,
            "infos": int(infos) if isinstance(infos, int | float) else 0,
            "files_checked": int(files_checked) if isinstance(files_checked, int | float) else 0,
            "review_suggested": review_suggested.unwrap(),
        }
    )


@dataclass
class GuardRun:
    run_id: str
    path: str
    changed: bool
    status: RunStatus
    accepted_at: str
    updated_at: str
    timeout_reason: str
    started_at: str | None = None
    completed_at: str | None = None
    expires_at: str | None = None
    report: dict[str, Any] | None = None
    error_kind: str | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
    task: asyncio.Task[None] | None = None
    done_event: asyncio.Event = field(default_factory=asyncio.Event)


# @invar:allow shell_too_complex: State lifecycle management needs branching
# @shell_orchestration: Coordinates async subprocess lifecycle for MCP
class GuardRunRegistry:
    """In-memory run registry for DX-94 deferred guard execution."""

    def __init__(
        self,
        *,
        retention_seconds: int = 900,
        max_runtime_seconds: int = 1800,
        command_timeout_seconds: int = 3600,
        heartbeat_interval_seconds: float = 2.0,
    ) -> None:
        self._retention_seconds = retention_seconds
        self._max_runtime_seconds = max_runtime_seconds
        self._command_timeout_seconds = command_timeout_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._runs: dict[str, GuardRun] = {}
        self._expired: set[str] = set()
        self._lock = asyncio.Lock()

    async def start(
        self,
        *,
        cmd: list[str],
        path: str,
        changed: bool,
        timeout_reason: str,
    ) -> GuardRun:
        now = _utc_now().unwrap()
        run_id = f"grd_{uuid.uuid4().hex[:24]}"
        run = GuardRun(
            run_id=run_id,
            path=path,
            changed=changed,
            status="deferred",
            accepted_at=_iso(now).unwrap(),
            updated_at=_iso(now).unwrap(),
            timeout_reason=timeout_reason,
        )

        async with self._lock:
            self._cleanup_locked(now)
            self._runs[run_id] = run
            run.task = asyncio.create_task(self._execute_run(run_id, cmd))

        return run

    async def status(self, run_id: str) -> dict[str, Any]:
        async with self._lock:
            self._cleanup_locked(_utc_now().unwrap())
            run = self._runs.get(run_id)
            if run is None:
                if run_id in self._expired:
                    return {
                        "status": "failed",
                        "run_id": run_id,
                        "error_kind": "run_expired",
                        "message": "Run state has expired",
                    }
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "error_kind": "run_not_found",
                    "message": "Run ID not found",
                }
            return self._snapshot(run)

    async def wait(self, run_id: str, wait_ms: int) -> dict[str, Any]:
        async with self._lock:
            self._cleanup_locked(_utc_now().unwrap())
            run = self._runs.get(run_id)
            if run is None:
                if run_id in self._expired:
                    return {
                        "status": "failed",
                        "run_id": run_id,
                        "error_kind": "run_expired",
                        "message": "Run state has expired",
                    }
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "error_kind": "run_not_found",
                    "message": "Run ID not found",
                }

            if run.status in ("complete", "failed", "cancelled"):
                return self._snapshot(run)

            done_event = run.done_event

        timeout_seconds = max(0.0, wait_ms / 1000)
        with suppress(TimeoutError):
            await asyncio.wait_for(done_event.wait(), timeout=timeout_seconds)

        async with self._lock:
            self._cleanup_locked(_utc_now().unwrap())
            run = self._runs.get(run_id)
            if run is None:
                if run_id in self._expired:
                    return {
                        "status": "failed",
                        "run_id": run_id,
                        "error_kind": "run_expired",
                        "message": "Run state has expired",
                    }
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "error_kind": "run_not_found",
                    "message": "Run ID not found",
                }
            return self._snapshot(run)

    async def _execute_run(self, run_id: str, cmd: list[str]) -> None:
        await self._set_running(run_id)

        heartbeat = asyncio.create_task(self._heartbeat(run_id))

        try:
            payload = await asyncio.wait_for(
                self._run_guard_command(cmd),
                timeout=max(0.0, float(self._max_runtime_seconds)),
            )
            await self._set_complete(run_id, payload)
        except asyncio.CancelledError:
            await self._set_cancelled(run_id, "run_cancelled", "Run cancelled before completion")
            raise
        except TimeoutError:
            await self._set_cancelled(
                run_id,
                "run_expired",
                "Run exceeded max runtime and was cancelled",
            )
        except GuardWrapperInstabilityError as exc:
            run = self._runs.get(run_id)
            if run is None:
                return
            details = build_wrapper_instability_envelope(
                run_id=run_id,
                path=run.path,
                changed=run.changed,
                subprocess_exit_code=exc.returncode,
                stderr=exc.stderr,
            )
            if isinstance(details, Failure):
                detail_payload = {
                    "status": "failed",
                    "run_id": run_id,
                    "error_kind": "wrapper_instability",
                    "classification": WRAPPER_INSTABILITY_CLASSIFICATION,
                    "message": details.failure(),
                }
            else:
                detail_payload = details.unwrap()
            await self._set_failed(
                run_id,
                "wrapper_instability",
                str(exc),
                details=detail_payload,
            )
        except subprocess.TimeoutExpired as exc:
            message = f"Guard subprocess timed out ({exc.timeout}s)"
            await self._set_failed(run_id, "execution_error", message)
        except Exception as exc:
            await self._set_failed(run_id, "execution_error", str(exc))
        finally:
            heartbeat.cancel()

    async def _set_running(self, run_id: str) -> None:
        now = _utc_now().unwrap()
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = _iso(now).unwrap()
            run.updated_at = _iso(now).unwrap()

    async def _set_complete(self, run_id: str, payload: dict[str, Any]) -> None:
        now = _utc_now().unwrap()
        report = summarize_guard_payload(payload)
        if isinstance(report, Failure):
            await self._set_failed(run_id, "execution_error", report.failure())
            return
        expires_at = now + timedelta(seconds=self._retention_seconds)
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "complete"
            run.report = report.unwrap()
            run.completed_at = _iso(now).unwrap()
            run.updated_at = _iso(now).unwrap()
            run.expires_at = _iso(expires_at).unwrap()
            run.done_event.set()

    async def _set_failed(
        self,
        run_id: str,
        error_kind: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        now = _utc_now().unwrap()
        expires_at = now + timedelta(seconds=self._retention_seconds)
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "failed"
            run.error_kind = error_kind
            run.message = message
            run.details = details
            run.completed_at = _iso(now).unwrap()
            run.updated_at = _iso(now).unwrap()
            run.expires_at = _iso(expires_at).unwrap()
            run.done_event.set()

    async def _set_cancelled(self, run_id: str, error_kind: str, message: str) -> None:
        now = _utc_now().unwrap()
        expires_at = now + timedelta(seconds=self._retention_seconds)
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            run.status = "cancelled"
            run.error_kind = error_kind
            run.message = message
            run.completed_at = _iso(now).unwrap()
            run.updated_at = _iso(now).unwrap()
            run.expires_at = _iso(expires_at).unwrap()
            run.done_event.set()

    async def _run_guard_command(self, cmd: list[str]) -> dict[str, Any]:
        """Run guard command and parse JSON output.

        Uses asyncio subprocess so cancellation and timeouts can terminate the child.
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(),
                timeout=max(0.0, float(self._command_timeout_seconds)),
            )
        except TimeoutError as exc:
            with suppress(ProcessLookupError):
                proc.kill()
            with suppress(Exception):
                await proc.wait()
            raise subprocess.TimeoutExpired(cmd, self._command_timeout_seconds) from exc
        except asyncio.CancelledError:
            with suppress(ProcessLookupError):
                proc.kill()
            with suppress(Exception):
                await proc.wait()
            raise

        stdout = (stdout_b or b"").decode("utf-8", errors="replace")
        stderr = (stderr_b or b"").decode("utf-8", errors="replace").strip()
        returncode = proc.returncode if proc.returncode is not None else -1

        if returncode != 0:
            raise GuardWrapperInstabilityError(returncode, stderr)

        parsed = _parse_guard_json(stdout)
        if isinstance(parsed, Failure):
            raise RuntimeError(parsed.failure())
        return parsed.unwrap()

    async def _heartbeat(self, run_id: str) -> None:
        """Update updated_at periodically while a run is active."""
        interval = max(0.01, float(self._heartbeat_interval_seconds))
        while True:
            await asyncio.sleep(interval)
            now = _utc_now().unwrap()
            async with self._lock:
                run = self._runs.get(run_id)
                if run is None:
                    return
                if run.status not in ("deferred", "running"):
                    return
                run.updated_at = _iso(now).unwrap()

    def _cleanup_locked(self, now: datetime) -> None:
        stale_running: list[GuardRun] = []
        delete_ids: list[str] = []

        for run_id, run in self._runs.items():
            if run.status in ("deferred", "running") and run.started_at:
                started = datetime.fromisoformat(run.started_at.replace("Z", "+00:00"))
                elapsed = now - started
                if elapsed.total_seconds() > self._max_runtime_seconds:
                    stale_running.append(run)

            if run.status in ("complete", "failed", "cancelled") and run.expires_at:
                expires = datetime.fromisoformat(run.expires_at.replace("Z", "+00:00"))
                if now >= expires:
                    delete_ids.append(run_id)

        for run in stale_running:
            run.status = "cancelled"
            run.error_kind = "run_expired"
            run.message = "Run exceeded max runtime and was cancelled"
            run.updated_at = _iso(now).unwrap()
            run.completed_at = _iso(now).unwrap()
            run.expires_at = _iso(now + timedelta(seconds=self._retention_seconds)).unwrap()
            run.done_event.set()
            if run.task and not run.task.done():
                run.task.cancel()

        for run_id in delete_ids:
            del self._runs[run_id]
            self._expired.add(run_id)

    def _snapshot(self, run: GuardRun) -> dict[str, Any]:
        if run.status in ("deferred", "running"):
            return {
                "status": run.status,
                "run_id": run.run_id,
                "phase": "verification",
                "progress": {"completed": 0, "total": 0},
                "started_at": run.started_at,
                "updated_at": run.updated_at,
            }

        if run.status == "complete":
            return {
                "status": "complete",
                "run_id": run.run_id,
                "report": run.report,
                "completed_at": run.completed_at,
                "expires_at": run.expires_at,
            }

        payload = {
            "status": run.status,
            "run_id": run.run_id,
            "error_kind": run.error_kind,
            "message": run.message,
            "completed_at": run.completed_at,
            "expires_at": run.expires_at,
        }
        if run.details:
            payload.update(run.details)
        return payload


GUARD_RUNS = GuardRunRegistry()
