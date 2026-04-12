# DX-94: MCP Full-Guard Support Model for Large Repositories

## Context and Source
- Source A (task boundary): `mcp-full-guard-design.specify-support-model` requires design for `invar_guard(changed=false)` full scans, timeout avoidance, fast-path preservation, compatibility, acceptance criteria, and migration constraints.
- Source B (current contract docs): `CLAUDE.md` parameter reference defines `invar_guard(changed=False)` as full-project verification.
- Source C (MCP behavior constraints): long-running operations can exceed request timeouts in host environments; large-repository scans are at risk.
- Source D (current remediation boundary): `mcp-full-guard-design.gate-fix-blockers` requires closing three explicit blockers: `check_all_rules` property-test reliance, DX-94/runtime mismatch for cancel + wait-timeout envelope assumptions, and concrete deferred cross-repo validation scope when `../tasca` is unavailable.
- Source E (runtime/tooling surface): MCP exposes `invar_guard`, `invar_guard_status`, and `invar_guard_wait`; there is no `invar_guard_cancel` tool in the current surface.
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
- It enables progress semantics for long scans without forcing streaming support in every MCP host.
## API Contract

## Existing Tool (Extended)

### `invar_guard(path=".", changed=true, strict=false, coverage=false, contracts_only=false, mutation=false)`
Behavior:

- `changed=true` (default): unchanged synchronous response contract.
- `changed=false`:
  - If planner estimates run <= `sync_budget_ms`, run synchronously and return final report.
  - If planner estimates run > `sync_budget_ms`, return deferred envelope:
- `mutation=true`: Enables mutation testing phase (DX-97). Runs after all standard phases pass. Output includes `score`, `passed`, `eligible_files`, `ineligible_files`, `files_with_zero_sites`, and bounded `survivor_evidence`. Fail-closed: `timeout>0` or `error>0` causes failure regardless of score.

```json
{
  "status": "deferred",
  "run_id": "grd_01J...",
  "lifecycle": "accepted",
  "mode": "full_scan",
  "path": ".",
  "changed": false,
  "accepted_at": "2026-03-09T00:00:00Z",
  "poll_after_ms": 1000,
  "timeout_reason": "estimated_duration_exceeds_sync_budget"
}
```

Deferred acceptance contract:

- `run_id` is the stable identifier for status/wait operations.
- `lifecycle` starts at `accepted` and can transition only as documented in Acceptance Criteria.
- If acceptance fails before a run is created, `invar_guard` returns immediate terminal `status="failed"` with an error envelope (no `run_id`).
## New Companion Tools
### `invar_guard_status(run_id: str)`

Returns run snapshot:

```json
{
  "status": "running",
  "run_id": "grd_01J...",
  "lifecycle": "running",
  "updated_at": "2026-03-09T00:01:42Z"
}
```

Status contract notes:

- `status` is one of `running | complete | failed | cancelled | expired`.
- `lifecycle` mirrors run-state progression and is monotonic.
- Unknown vs expired runs MUST remain machine-distinct via `error_kind`: unknown -> `run_not_found`, expired -> `run_expired`.
- Clients MUST key unknown-vs-expired handling on `error_kind`, not on message text.

### `invar_guard_wait(run_id: str, wait_ms: int = 8000)`

Long-poll with bounded wait.

Representative non-terminal envelope:

```json
{
  "status": "running",
  "run_id": "grd_01J...",
  "lifecycle": "running",
  "updated_at": "2026-03-09T00:01:42Z"
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
    "review_suggested": false,
    "mutation": {
      "total": 10,
      "killed": 8,
      "survived": 1,
      "timeout": 0,
      "error": 0,
      "score": 80.0,
      "passed": true,
      "eligible_files": 3,
      "ineligible_files": 1,
      "files_with_zero_sites": 1,
      "survivor_evidence": ["src/core/calc.py:42:Add"]
    }
  }
}
```

**DX-97: Mutation output** (when `mutation=true`):
- `total/killed/survived/timeout/error`: Mutant counts by outcome
- `score`: Mutation score percentage (killed/total)
- `passed`: Whether score >= 80% AND timeout==0 AND error==0
- `eligible_files`: Files with mutation sites that were tested
- `ineligible_files`: Files skipped due to parse/import errors
- `files_with_zero_sites`: Files that parsed OK but had no mutation candidates
- `survivor_evidence`: Bounded list (max 5) of surviving mutant locations

Terminal failure envelope:

```json
{
  "status": "failed",
  "run_id": "grd_01J...",
  "lifecycle": "failed",
  "error_kind": "execution_error",
  "message": "CrossHair subprocess exited non-zero"
}
```

Deferred full-scan failure-mode coverage (`error_kind`):

- `planner_error`: pre-execution estimator/planner failed before worker handoff.
- `queue_persist_error`: run accepted but background work could not be persisted/scheduled.
- `execution_error`: worker started but verification execution failed.
- `run_not_found`: unknown `run_id` (never existed or malformed for this namespace).
- `run_expired`: run metadata existed but exceeded retention TTL before retrieval.

Contract semantics:

- `report` appears only when `status="complete"` and is the sole final report schema.
- Non-terminal waits are represented by continued non-terminal status (typically `running`) and absence of final `report`.
- Explicit `wait_timeout`/`next_poll_after_ms` envelope keys are not required by the current DX-94 contract.

Current-surface note:

- `invar_guard_cancel` is not part of the current MCP tool surface and is therefore not a DX-94 acceptance requirement in this gate.

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
5. New fields (`lifecycle`, `error_kind`) are additive and safe for clients that ignore unknown keys.
6. Cancellation behavior is implementation-internal unless/until a dedicated cancel tool is introduced in a separate step.

Compatibility contract: no parameter removals, no semantic changes to changed-only mode, additive response/tooling only.
## Acceptance Criteria
1. **Large full scan defers safely**
   - `invar_guard(changed=false)` returns `status="deferred"` within `sync_budget_ms + 500ms` when planner estimate exceeds budget (validated in-repo in gate context).
2. **No request-timeout failure on long run**
   - Repeated `invar_guard_wait(run_id, wait_ms<=8000)` eventually returns terminal status (`complete|failed|cancelled|expired`), not transport timeout.
3. **Unknown vs expired taxonomy is machine-distinct**
   - Unknown `run_id` maps to `error_kind="run_not_found"`; expired `run_id` maps to `error_kind="run_expired"`.
4. **Deferred full-scan failure coverage is explicit**
   - Failure modes include planner failure, queue persistence failure, worker execution failure, and run-state expiry/not-found with distinct `error_kind` values.
5. **Contract semantics for non-terminal wait are minimal and stable**
   - `invar_guard_wait` may return non-terminal status (typically `running`) without final `report`; clients continue polling until terminal status.
   - Contract does not require explicit wait-timeout envelope keys.
6. **Changed-only path unaffected**
   - `invar_guard(changed=true)` remains synchronous and matches pre-DX-94 behavior and output fields.
7. **Backward-compatible shape for final report**
   - Completed report preserves existing summary keys (`ok`, `errors`, `warnings`, `review_suggested`) used by current UX.
8. **Deterministic lifecycle**
   - `run_id` is stable; lifecycle/status progression is monotonic through terminal outcomes.
9. **Cross-repo validation is explicitly staged when `../tasca` is unavailable**
   - Gate-context verification is in-repo only (deferred handshake + lifecycle/taxonomy behavior).
   - Cross-repo evidence is deferred to field validation and must include: command context/path, deferred acceptance proof, and terminal outcome proof on the external repo.
10. **Property-test blocker is removed from DX-94 acceptance coupling**
   - DX-94 acceptance does not assume universal property-pass of `src/invar/core/rules.py::check_all_rules`.
   - Rule-semantic/property stabilization remains a separate prerequisite track and must be evidenced independently.
## Non-Goals
- Rewriting verification engines (doctest/CrossHair/Hypothesis internals).
- Changing rule semantics or severity policy.
- Forcing async behavior for changed-only scans.
- Defining UI progress rendering details for every host.
- Introducing a new MCP cancel tool in this remediation loop.
## Migration Constraints
1. Additive rollout only; no breaking removals.
2. Keep existing `invar_guard` signature valid.
3. Introduce only currently implemented companion tools (`invar_guard_status`, `invar_guard_wait`) behind feature-gated release notes.
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
   - Rejected: does not solve deferred full-scan reliability objective for large external repositories.
