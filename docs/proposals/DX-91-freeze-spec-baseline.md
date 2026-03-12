# DX-91 Spec Freeze Baseline

## Freeze Metadata

- Freeze date (UTC): 2026-03-12
- Working tree requirement: clean at freeze capture and gate handoff
- Execution environment: isolated git worktree `.vectl/worktrees/freeze-spec-snapshot`

## Baseline Commit and State

**Canonical freeze snapshot:** `git rev-parse HEAD` output recorded at freeze handoff time.

**Reproducibility proof:**
```
# Record at freeze handoff
git rev-parse HEAD        → <exact-sha>
git status --short        → (empty output)
git diff --stat          → (empty output)
```

**Verification:** Re-running these commands at any point during the implementation phase MUST yield:
- Same `<exact-sha>` as recorded at freeze handoff
- Empty `git status --short` (clean working tree)
- No uncommitted changes

If the commit hash differs or the tree is dirty, the freeze is invalidated.

## Baseline Proposal Sections (Authoritative)

The following proposal sections define the execution baseline for downstream implementation and verification:

1. `docs/proposals/DX-91-generated-file-contracts.md`
   - `dx-91-generated-file-contract/2-generated-files-contract`
   - `dx-91-generated-file-contract/3-implementation-work-split`
   - `dx-91-generated-file-contract/4-marker-system-contract`
   - `dx-91-generated-file-contract/5-intentionally-deferred`
   - `dx-91-generated-file-contract/6-verification-matrix`
   - `dx-91-generated-file-contract/7-no-unresolved-ambiguity-checklist`
2. `docs/proposals/DX-91-migration-semantics.md`
   - `dx-91-migration-semantics-specification/2-keep-remove-boundary-canonical`
   - `dx-91-migration-semantics-specification/3-init-v2-behavior`
   - `dx-91-migration-semantics-specification/4-migration-behavior-v1-v2`
   - `dx-91-migration-semantics-specification/5-dev-sync-scope-reduced`
3. `docs/proposals/DX-91-simplification.md`
   - `dx-91-invar-simplification/1-what-to-keep`
   - `dx-91-invar-simplification/2-what-to-remove`
   - `dx-91-invar-simplification/3-simplified-invar-init`

## Freeze Guards

1. No additional DX-91 proposal edits are folded into the active implementation window without an explicit replan.
2. No code changes are allowed between this freeze snapshot and the subsequent phase gate review for this phase.
3. If any baseline proposal section changes, the freeze is invalidated and must be re-issued with a new snapshot commit.

## Gate Readiness Declaration

This phase is ready for independent gate review against the frozen baseline above.

## Source-of-Truth Boundaries

For all downstream implementation and verification, the following sources are canonical:

| Topic | Canonical Source | Notes |
|-------|------------------|-------|
| Generated file contracts | `DX-91-generated-file-contracts.md` §2-4 | Contract definitions |
| Keep/remove lists | `DX-91-migration-semantics.md` §2.2 | Deletion reference |
| init v2 behavior | `DX-91-migration-semantics.md` §3 | Command surface |
| Migration steps | `DX-91-migration-semantics.md` §4 | Migration execution |
| Marker semantics | `DX-91-migration-semantics.md` §3.3, §4.4, §10.4 | Inside-marker behavior |
| CLAUDE.md content | `DX-91-claude-md-draft.md` §2 | Injected section |
| INVAR.md content | `DX-91-invar-md-draft.md` (entire) | Full document |
| Idempotent re-run | `DX-91-migration-semantics.md` §10.4 | Edge case handling |
| Backup semantics | `DX-91-migration-semantics.md` §4.3-4.4, §10.2 | Optional-file handling |
