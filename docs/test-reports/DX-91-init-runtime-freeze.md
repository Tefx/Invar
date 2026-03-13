# DX-91 Init Runtime Freeze Snapshot

Date: 2026-03-12
Step: freeze-init-runtime-snapshot

## Runtime Proof Snapshot (Frozen)

- Proof commit captured before freeze artifact commit: `bcde322920e8af5b590e5d38e99fe2126d16ac09`
- Clean-tree check at capture time: `git status --short` -> no output
- Environment declaration:
  - `pwd` -> `/Users/tefx/Projects/Invar/.vectl/worktrees/freeze-init-runtime-snapshot`
  - `git rev-parse --abbrev-ref HEAD` -> `vectl/step-freeze-init-runtime-snapshot`
  - `uname -s` -> `Darwin`
  - `python3 --version` -> `Python 3.14.3`

## Protected Regression Entrypoints (Locked)

These are frozen as protected regression entrypoints for downstream phases.

Historical note: this freeze snapshot captures pre-retirement symbol names and is
archival evidence only; active DX-91 runtime no longer ships `invar uninstall`.

1. `tests/integration/test_dx91_init_entrypoints.py`
   - Entrypoint under test: `invar.shell.commands.init.init`
   - Covers: main-path generation, relative/absolute target file handling, migration edge handling, explicit deletions, stale-state precedence, interrupted write recovery, repeated-run idempotency.

2. `tests/integration/test_dx91_destructive_regression_harness.py`
   - Entrypoints under test (real command APIs, no harness-local write-through):
     - `invar.shell.commands.uninstall.collect_removal_targets`
     - `invar.shell.commands.uninstall.execute_removal`
     - `invar.shell.commands.template_sync.sync_templates`
   - Covers: mainline migration, idempotent repeated migration, stale/new-state precedence, missing optional files, interrupted partial migration recovery, clear-null overwrite semantics, relative-vs-absolute template-path behavior, and explicit failure-path leak detection.

## Fixture Set (Locked)

Fixture inventory source (frozen reference):
- `tests/fixtures/dx91_migration/fixture_inventory.yaml`

Fixture root (frozen reference):
- `tests/fixtures/dx91_migration/`

Locked fixture IDs:
- `mainline-v1-to-v2`
- `relative-vs-absolute-template-path`
- `missing-file-fallback-partial-repo`
- `clear-null-overwrite-removed-managed`
- `stale-legacy-vs-new-state-precedence`
- `interrupted-partial-migration-recovery`
- `repeated-migration-idempotent-v1-source`

## Freeze Rule

No code changes are allowed after this snapshot until the subsequent phase gate (`dx91-init-runtime.gate`) is reviewed and opened.
