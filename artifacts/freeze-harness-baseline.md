# Freeze Harness Baseline Snapshot

## Freeze Capture

- Freeze step: `freeze-harness-snapshot`
- Freeze timestamp (UTC): 2026-03-12
- Freeze worktree: `.vectl/worktrees/freeze-harness-snapshot`
- Freeze branch: `vectl/step-freeze-harness-snapshot`
- Baseline commit (captured with clean tree): `0b462c40662e4c2fd9686800922511d2ddf51662`

## Environment Declaration

- Repository root (worktree): `/Users/tefx/Projects/Invar/.vectl/worktrees/freeze-harness-snapshot`
- Platform: `darwin`

## Protected Baseline Scope

### Fixture Roots (Protected)

- `tests/fixtures/dx91_migration/`
- `tests/fixtures/dx91_migration/mainline-v1-to-v2/`
- `tests/fixtures/dx91_migration/repeated-migration-idempotent-v1-source/`
- `tests/fixtures/dx91_migration/stale-legacy-vs-new-state-precedence/`
- `tests/fixtures/dx91_migration/missing-file-fallback-partial-repo/`
- `tests/fixtures/dx91_migration/interrupted-partial-migration-recovery/`
- `tests/fixtures/dx91_migration/clear-null-overwrite-removed-managed/`

### Test Entrypoints (Protected)

- `uv run pytest -v tests/integration/test_dx91_destructive_regression_harness.py`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_happy_path_mainline_fixture_migrates_end_to_end`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_edge_case_repeated_migration_is_idempotent`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_edge_and_error_fixtures_enforce_expected_state[stale-legacy-vs-new-state-precedence]`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_edge_and_error_fixtures_enforce_expected_state[missing-file-fallback-partial-repo]`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_edge_and_error_fixtures_enforce_expected_state[interrupted-partial-migration-recovery]`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_edge_and_error_fixtures_enforce_expected_state[clear-null-overwrite-removed-managed]`
- `tests/integration/test_dx91_destructive_regression_harness.py::test_failure_path_harness_detects_broken_preservation_deletion_rule`

## Freeze Guard Declaration

No code changes are allowed between this freeze snapshot and the phase gate review for the harness baseline. Any source, fixture, or harness entrypoint drift invalidates this freeze and requires a re-issued snapshot.

## Spec Link

- `docs/proposals/DX-91-freeze-spec-baseline.md` (Freeze Guards)
- `DX-91-REGRESSION-SURFACES.md` (Sections 7.1 and 7.2)

## Gate Readiness

Harness baseline is frozen and ready for gate review and downstream reuse.
