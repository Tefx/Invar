# DX-94: MCP Full-Guard Support Model for Large Repositories

## Context and Source

- Source A (task boundary): `mcp-full-guard-design.specify-support-model` requires design for `invar_guard(changed=false)` full scans, timeout avoidance, fast-path preservation, compatibility, acceptance criteria including `../tasca`, and migration constraints.
- Source B (current contract docs): `CLAUDE.md` parameter reference defines `invar_guard(changed=False)` as full-project verification.
- Source C (MCP behavior constraints): long-running operations can exceed request timeouts in host environments; large-repository scans are at risk.
- Source D (current step boundary): `mcp-full-guard-design.verify-design-fix` requires explicit closure for cancellation contract, non-terminal wait-timeout schema, partial-result semantics, and extended deferred failure-mode coverage.

## Problem Statement

`invar_guard(changed=false)` on large repositories is semantically correct but operationally fragile in MCP contexts with finite request budgets. The current one-shot request/response model couples full verification duration to a single RPC timeout window.

## Decision: Split-Phase Execution Model (Deferred Full Scan)

### Chosen Model

Use a split-phase model for large full scans while preserving synchronous behavior for fast workloads:

1. `invar_guard(...)` remains the entry point.
2. For `changed=false` calls expected to exceed sync budget, `invar_guard` returns quickly with a run handle (`deferred` response).
3. Client retrieves completion via polling/long-poll (`invar_guard_wait`) and optional status snapshots (`invar_guard_status`).

This decouples request lifetime from scan lifetime and avoids transport-level timeout failures.

### Why This Model

- It directly addresses timeout failure mode by returning before host timeout budget is exceeded.
- It avoids changing changed-only behavior.
- It enables progress and cancellation semantics for long scans without forcing streaming support in every MCP host.

## API Contract

## Existing Tool (Extended)

### `invar_guard(path=".", changed=true, strict=false, coverage=false, contracts_only=false)`

Behavior:

- `changed=true` (default): unchanged synchronous response contract.
- `changed=false`:
  - If planner estimates run <= `sync_budget_ms`, run synchronously and return final report.
  - If planner estimates run > `sync_budget_ms`, return deferred envelope:

```json
{
  "status": "deferred",
  "run_id": "grd_01J...",
  "lifecycle": "accepted",
  "mode": "full_scan",
  "path": "../tasca",
  "changed": false,
  "accepted_at": "2026-03-09T00:00:00Z",
  "poll_after_ms": 1000,
  "timeout_reason": "estimated_duration_exceeds_sync_budget"
}
```

Deferred acceptance contract:

- `run_id` is the stable identifier for status/wait/cancel operations.
- `lifecycle` starts at `accepted` and can transition only as documented in Acceptance Criteria.
- If acceptance fails before a run is created, `invar_guard` returns immediate terminal `status="failed"` with an error envelope (no `run_id`).

## New Companion Tools

### `invar_guard_status(run_id: str)`

Returns progress snapshot:

```json
{
  "status": "running",
  "run_id": "grd_01J...",
  "lifecycle": "running",
  "phase": "crosshair",
  "progress": {"completed": 312, "total": 910},
  "partial_report": {
    "ok_so_far": true,
    "errors": 0,
    "warnings": 1,
    "review_suggested": false,
    "is_partial": true
  },
  "started_at": "2026-03-09T00:00:00Z",
  "updated_at": "2026-03-09T00:01:42Z"
}
```

Status contract notes:

- `status` is transport-level result shape and remains one of: `running | complete | failed | cancelled`.
- `lifecycle` mirrors run-state progression and is monotonic.
- `partial_report` is optional, and when present MUST include `is_partial=true`.

### `invar_guard_wait(run_id: str, wait_ms: int = 8000)`

Long-poll with bounded wait.

Non-terminal wait-timeout envelope (unambiguous schema):

```json
{
  "status": "running",
  "run_id": "grd_01J...",
  "lifecycle": "running",
  "wait_timeout": true,
  "next_poll_after_ms": 1000,
  "updated_at": "2026-03-09T00:01:42Z",
  "partial_report": {
    "ok_so_far": true,
    "errors": 0,
    "warnings": 1,
    "review_suggested": false,
    "is_partial": true
  }
}
```

Terminal completion envelope:

```json
{
  "status": "complete",
  "run_id": "grd_01J...",
  "lifecycle": "complete",
  "report": {
    "ok": true,
    "errors": 0,
    "warnings": 2,
    "review_suggested": false
  }
}
```

Terminal cancellation envelope:

```json
{
  "status": "cancelled",
  "run_id": "grd_01J...",
  "lifecycle": "cancelled",
  "cancelled_at": "2026-03-09T00:02:10Z",
  "cancel_reason": "user_requested",
  "partial_report": {
    "ok_so_far": false,
    "errors": 2,
    "warnings": 1,
    "review_suggested": true,
    "is_partial": true
  }
}
```

Terminal failure envelope:

```json
{
  "status": "failed",
  "run_id": "grd_01J...",
  "lifecycle": "failed",
  "error_kind": "execution_error",
  "message": "CrossHair subprocess exited non-zero",
  "partial_report": {
    "ok_so_far": false,
    "errors": 2,
    "warnings": 1,
    "review_suggested": true,
    "is_partial": true
  }
}
```

Deferred full-scan failure-mode coverage (`error_kind`):

- `planner_error`: pre-execution estimator/planner failed before worker handoff.
- `queue_persist_error`: run accepted but background work could not be persisted/scheduled.
- `execution_error`: worker started but verification execution failed.
- `run_not_found`: unknown `run_id` (invalid or already cleaned up).
- `run_expired`: run metadata existed but exceeded retention TTL before retrieval.

Partial-result semantics:

- `partial_report` is progress-state metadata and MUST NOT be treated as final guard output.
- `report` appears only when `status="complete"` and is the sole final report schema.
- `partial_report` can appear on `running`, `failed`, or `cancelled` to support diagnostics.
- If no verification layer has produced summary data yet, `partial_report` may be omitted.

### `invar_guard_cancel(run_id: str, reason: str | null = null)`

Cancellation API for deferred runs:

```json
{
  "status": "cancelled",
  "run_id": "grd_01J...",
  "lifecycle": "cancelled",
  "cancelled_at": "2026-03-09T00:02:10Z",
  "cancel_reason": "user_requested"
}
```

Cancellation contract:

- Idempotent: cancelling an already-cancelled run returns the same cancelled envelope.
- Terminal-state behavior:
  - `complete`: return `status="complete"` unchanged.
  - `failed`: return `status="failed"` unchanged.
  - unknown/expired `run_id`: return `status="failed"`, `error_kind="run_not_found"`.
- End-to-end guarantee: after successful cancellation, subsequent `status`/`wait` calls for the same `run_id` return `status="cancelled"` (no reversion to `running`).

## Timeout-Avoidance Strategy

1. Introduce `sync_budget_ms` (default 8000 for MCP-facing calls).
2. Add an initial planning pass (cheap estimator based on candidate file count and enabled layers).
3. If estimate exceeds budget, immediately return deferred handle.
4. Execute long run in background worker with persisted run state.
5. Use bounded long-poll (`invar_guard_wait`) to avoid idle timeout while reducing polling chatter.

### Rationale for Avoiding Request Timeouts

Timeouts occur when one request must remain open for the entire verification duration. The deferred model eliminates that requirement by returning acceptance quickly and moving long work behind a run handle. Each subsequent `wait` call has bounded duration and can be retried idempotently, so transport timeout no longer terminates the underlying verification.

## Preserving Changed-Only Fast Path

- `changed=true` stays synchronous and default.
- No planner-induced deferral for changed-only unless explicitly requested by future flag (out of scope here).
- Existing call sites relying on immediate changed-only result remain unaffected.

## Backward Compatibility Expectations

1. Default behavior remains unchanged for common path (`changed=true`).
2. Full-scan callers must tolerate either:
   - immediate final report (small repos), or
   - deferred envelope (large repos).
3. CLI can preserve blocking UX by internally looping on `wait` until complete.
4. Existing MCP clients that only support one-shot full scan may require minor adaptation to follow run handles.
5. New fields (`lifecycle`, `wait_timeout`, `next_poll_after_ms`, `partial_report`) are additive and safe for clients that ignore unknown keys.
6. `invar_guard_cancel` is additive; legacy clients can omit cancellation support.

Compatibility contract: no parameter removals, no semantic changes to changed-only mode, additive response/tooling only.

## Acceptance Criteria

1. **Large full scan defers safely**
   - `invar_guard(path="../tasca", changed=false)` returns `status="deferred"` within `sync_budget_ms + 500ms`.
2. **No request-timeout failure on long run**
    - Repeated `invar_guard_wait(run_id, wait_ms<=8000)` eventually returns `status="complete"` or `status="failed"` with explicit error envelope, not transport timeout.
3. **Non-terminal wait timeout is explicit**
   - `invar_guard_wait` timeout while run is still active returns `status="running"` + `wait_timeout=true` + `next_poll_after_ms`.
4. **Cancellation contract is end-to-end**
   - `invar_guard_cancel(run_id)` yields terminal cancelled envelope and all follow-up `status`/`wait` calls remain `status="cancelled"`.
5. **Partial-result semantics are unambiguous**
   - `partial_report` never replaces final `report`; final report exists only in `status="complete"`.
6. **Deferred full-scan failure coverage is explicit**
   - Failure modes include planner failure, queue persistence failure, worker execution failure, and run-state expiry/not-found with distinct `error_kind` values.
7. **Changed-only path unaffected**
    - `invar_guard(changed=true)` remains synchronous and matches pre-DX-94 behavior and output fields.
8. **Backward-compatible shape for final report**
    - Completed report preserves existing summary keys (`ok`, `errors`, `warnings`, `review_suggested`) used by current UX.
9. **Deterministic lifecycle**
    - `run_id` is stable, status transitions are monotonic: `deferred -> running -> complete|failed|cancelled`.

## Non-Goals

- Rewriting verification engines (doctest/CrossHair/Hypothesis internals).
- Changing rule semantics or severity policy.
- Forcing async behavior for changed-only scans.
- Defining UI progress rendering details for every host.

## Migration Constraints

1. Additive rollout only; no breaking removals.
2. Keep existing `invar_guard` signature valid.
3. Introduce companion tools behind feature-gated release notes.
4. Maintain final-report schema parity between sync and deferred completion paths.
5. Ensure run-state storage has bounded retention and cleanup policy (TTL-based) to avoid unbounded disk growth.
6. Document canonical `error_kind` set for deferred failures: `planner_error`, `queue_persist_error`, `execution_error`, `run_not_found`, `run_expired`.

## Rollout Notes

1. Phase 1: implement deferred internals + status/wait tools.
2. Phase 2: adapt MCP client guidance and docs.
3. Phase 3: enable for `changed=false` with estimator threshold.
4. Phase 4: collect telemetry on deferred rate and completion latency.

## Alternatives Considered

1. Increase MCP timeout globally.
   - Rejected: host-specific, brittle, and still finite.
2. Stream full logs in single request.
   - Rejected: requires robust streaming support across hosts and still risks connection drop.
3. Keep one-shot and advise smaller repos.
   - Rejected: does not solve required `../tasca` full-scan reliability objective.
