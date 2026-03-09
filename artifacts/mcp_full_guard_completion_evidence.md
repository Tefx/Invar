## Large-Repo MCP Full-Guard Completion Evidence

**Target context**: /Users/tefx/Projects/Invar
**Why this is the intended target**: `git worktree list --porcelain` in isolated worktree shows `/Users/tefx/Projects/Invar` as the primary checkout and `/Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.capture-completed-large-repo-mcp-full-guard-evidence` as this isolated worktree.

**Exact MCP invocation / observation commands**:
```
invar_invar_guard(path="/Users/tefx/Projects/Invar", changed=false)
invar_invar_guard_wait(run_id="grd_241421c8ce244860934b07d0", wait_ms=10000)
invar_invar_guard_wait(run_id="grd_241421c8ce244860934b07d0", wait_ms=10000)
invar_invar_guard_status(run_id="grd_241421c8ce244860934b07d0")
invar_invar_guard_wait(run_id="grd_241421c8ce244860934b07d0", wait_ms=10000)
invar_invar_guard_wait(run_id="grd_241421c8ce244860934b07d0", wait_ms=10000)
invar_invar_guard_status(run_id="grd_241421c8ce244860934b07d0")
```

**Deferred run tracking**:
- Initial run id: grd_241421c8ce244860934b07d0
- Observation method: repeated `invar_invar_guard_wait` polling plus terminal `invar_invar_guard_status`
- Terminal status reached: failed

**Observation output**:
```
invar_invar_guard =>
{
  "status": "deferred",
  "run_id": "grd_241421c8ce244860934b07d0",
  "mode": "full_scan",
  "path": "/Users/tefx/Projects/Invar",
  "changed": false,
  "accepted_at": "2026-03-09T15:22:42.758014Z",
  "poll_after_ms": 1000,
  "timeout_reason": "estimated_duration_exceeds_sync_budget"
}

invar_invar_guard_wait => {"status":"running","run_id":"grd_241421c8ce244860934b07d0","phase":"verification","progress":{"completed":0,"total":0},"started_at":"2026-03-09T15:22:42.758478Z","updated_at":"2026-03-09T15:22:42.758478Z"}
invar_invar_guard_wait => {"status":"running","run_id":"grd_241421c8ce244860934b07d0","phase":"verification","progress":{"completed":0,"total":0},"started_at":"2026-03-09T15:22:42.758478Z","updated_at":"2026-03-09T15:22:42.758478Z"}
invar_invar_guard_status => {"status":"running","run_id":"grd_241421c8ce244860934b07d0","phase":"verification","progress":{"completed":0,"total":0},"started_at":"2026-03-09T15:22:42.758478Z","updated_at":"2026-03-09T15:22:42.758478Z"}
invar_invar_guard_wait => {"status":"running","run_id":"grd_241421c8ce244860934b07d0","phase":"verification","progress":{"completed":0,"total":0},"started_at":"2026-03-09T15:22:42.758478Z","updated_at":"2026-03-09T15:22:42.758478Z"}
invar_invar_guard_wait => {"status":"running","run_id":"grd_241421c8ce244860934b07d0","phase":"verification","progress":{"completed":0,"total":0},"started_at":"2026-03-09T15:22:42.758478Z","updated_at":"2026-03-09T15:22:42.758478Z"}
invar_invar_guard_status =>
{
  "status": "failed",
  "run_id": "grd_241421c8ce244860934b07d0",
  "error_kind": "execution_error",
  "message": "Guard subprocess failed with code 1",
  "completed_at": "2026-03-09T15:23:59.066487Z",
  "expires_at": "2026-03-09T15:38:59.066487Z"
}
```

**Artifacts / output paths**:
- /Users/tefx/Projects/Invar — explicit `invar_invar_guard(... path=...)` target in deferred run payload (`"path": "/Users/tefx/Projects/Invar"`), proving large-repo target context.
- /Users/tefx/Projects/Invar/.git — primary checkout root from `git worktree list --porcelain`; identifies intended large-repo checkout distinct from isolated worktree.
- /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.capture-completed-large-repo-mcp-full-guard-evidence/artifacts/mcp_full_guard_completion_evidence.md — captured transcript artifact produced in isolated worktree branch.

**Failure-path proof**:
- Evidence that prior worktree-path ambiguity is closed: `git worktree list --porcelain` shows both paths; `python3 -c "import os; print(os.path.samefile('<worktree>','/Users/tefx/Projects/Invar'))"` returned `False`.
- Evidence that completion was actually observed, not inferred: terminal `invar_invar_guard_status(run_id="grd_241421c8ce244860934b07d0")` returned `"status": "failed"` with `completed_at` timestamp.
