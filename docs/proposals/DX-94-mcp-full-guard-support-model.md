# DX-94: MCP Full-Guard Support Model for Large Repositories

## Context and Source

- Source A (task boundary): `mcp-full-guard-design.specify-support-model` requires design for `invar_guard(changed=false)` full scans, timeout avoidance, fast-path preservation, compatibility, acceptance criteria including `../tasca`, and migration constraints.
- Source B (current contract docs): `CLAUDE.md` parameter reference defines `invar_guard(changed=False)` as full-project verification.
- Source C (MCP behavior constraints): long-running operations can exceed request timeouts in host environments; large-repository scans are at risk.

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
  "mode": "full_scan",
  "path": "../tasca",
  "changed": false,
  "accepted_at": "2026-03-09T00:00:00Z",
  "poll_after_ms": 1000,
  "timeout_reason": "estimated_duration_exceeds_sync_budget"
}
```

## New Companion Tools

### `invar_guard_status(run_id: str)`

Returns progress snapshot:

```json
{
  "status": "running",
  "run_id": "grd_01J...",
  "phase": "crosshair",
  "progress": {"completed": 312, "total": 910},
  "started_at": "2026-03-09T00:00:00Z",
  "updated_at": "2026-03-09T00:01:42Z"
}
```

### `invar_guard_wait(run_id: str, wait_ms: int = 8000)`

Long-poll with bounded wait. Returns either in-progress timeout or final report:

```json
{
  "status": "complete",
  "run_id": "grd_01J...",
  "report": {
    "ok": true,
    "errors": 0,
    "warnings": 2,
    "review_suggested": false
  }
}
```

Failure envelope:

```json
{
  "status": "failed",
  "run_id": "grd_01J...",
  "error_kind": "execution_error",
  "message": "CrossHair subprocess exited non-zero"
}
```

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

Compatibility contract: no parameter removals, no semantic changes to changed-only mode, additive response/tooling only.

## Acceptance Criteria

1. **Large full scan defers safely**
   - `invar_guard(path="../tasca", changed=false)` returns `status="deferred"` within `sync_budget_ms + 500ms`.
2. **No request-timeout failure on long run**
   - Repeated `invar_guard_wait(run_id, wait_ms<=8000)` eventually returns `status="complete"` or `status="failed"` with explicit error envelope, not transport timeout.
3. **Changed-only path unaffected**
   - `invar_guard(changed=true)` remains synchronous and matches pre-DX-94 behavior and output fields.
4. **Backward-compatible shape for final report**
   - Completed report preserves existing summary keys (`ok`, `errors`, `warnings`, `review_suggested`) used by current UX.
5. **Deterministic lifecycle**
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
