# Wiring Integrity Gate-1 Fix Evidence

Spec source: `plan.yaml` step `gate-1-fix` (blockers from `wiring-integrity-1.gate-1`).

## 1) Rule Registration Landed (Committed State)

- File: `src/invar/core/rule_meta.py`
- Requirement addressed: `dead_param`, `stub_body`, and `wiring_gap` entries are in repository commit history (not staged-only).

Verification command:

```bash
uv run invar guard src/invar/core/rule_meta.py --all
```

Outcome:

- Status `passed`
- `files_checked=1`, `errors=0`, `warnings=0`, `infos=0`

## 2) Explicit Non-Doctest wiring_gap Coverage + Guard Integration Artifact

Added tests (non-doctest):

- `tests/core/test_wiring_gap.py`
  - Positive detection for omitted optional param wiring.
  - Negative when parameter is explicitly passed.
  - Verbose mode message context assertion.
- `tests/integration/test_wiring_gap_guard_integration.py`
  - End-to-end guard invocation on a fixture project, asserting `wiring_gap` appears in JSON output.

Artifact path (guard integration evidence):

- `docs/testing/artifacts/wiring-gap-guard-integration.json`

Combined test run:

```bash
uv run python -m pytest -q \
  tests/core/test_dead_param.py \
  tests/core/test_stub_body.py \
  tests/core/test_wiring_gap.py \
  tests/integration/test_wiring_gap_guard_integration.py
```

Outcome:

- `20 passed`, `0 failed` (plus 1 non-blocking Hypothesis plugin warning)

## 3) Reproducible Self-Validation (Clean Command Set)

Deterministic re-run commands for this step scope:

```bash
uv run invar guard src/invar/core/rule_meta.py --all
uv run invar guard src/invar/core/wiring_gap.py --all
uv run invar guard src/invar/shell/commands/guard.py --all --static
```

Observed outcomes:

- All three commands returned status `passed`
- Each command reported `errors=0`, `warnings=0`

Note (scope transparency):

- `uv run invar guard src/invar --all` currently resolves to project root scanning, which can include non-target directories (for example `.venv*`) and is not a deterministic retest surface for this step.
- Gate retest should use the explicit file-scoped command set above.

## 4) Cross-Project Precision/Recall Documentation

Cross-project run command (anima):

```bash
uvx invar-tools guard --all --static
```

Observed summary:

- `files_checked=72`, `errors=0`, `warnings=78`, `infos=11`
- Wave-1 rule counts in output (`dead_param`, `stub_body`, `wiring_gap`): `0`, `0`, `0`

Precision/recall interpretation for blocker closure:

- **Precision (observed)**: no positives for these three rules on anima static run, so no observed false positives in that corpus for this wave.
- **Recall (demonstrated)**:
  - `wiring_gap`: seeded fixture triggers exactly one `wiring_gap` finding (see `docs/testing/artifacts/wiring-gap-guard-integration.json`).
  - `dead_param` and `stub_body`: covered by targeted rule tests in this repo (`tests/core/test_dead_param.py`, `tests/core/test_stub_body.py`) with both positive and negative cases.

## 5) Freeze / Evidence Quality Requirements

For independent retest (`gate-1-retest`), evidence must include:

1. Freeze stamp before validation:
   - `git rev-parse HEAD`
   - `git status --short`
2. Exact commands executed (copy/paste, no paraphrase).
3. Raw outputs captured (or artifact file path if JSON output is long).
4. Statement of workspace policy:
   - acceptable: clean tree, or dirty tree with unrelated files explicitly listed
   - not acceptable: staged-only implementation claims without committed hash

Guard integration artifact to reference in retest:

- `docs/testing/artifacts/wiring-gap-guard-integration.json`
