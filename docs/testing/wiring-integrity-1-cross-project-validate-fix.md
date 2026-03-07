# Wiring Integrity Cross-Project Validate Fix (Wave-1)

Spec source: `plan.yaml` step `wiring-integrity-1.cross-project-validate-fix`.

Baseline source: `plan.yaml` evidence for `wiring-integrity-1.cross-project-validate`
reported high false-positive rate and identified two priority buckets:

- `dead_param` closure-capture and framework-signature false positives
- `stub_body` click-entrypoint false positives

## Rule Adjustments

### 1) `dead_param` precision tuning

Files:

- `src/invar/core/dead_param.py`
- `tests/core/test_dead_param.py`

Changes:

- Count closure captures as usage when outer parameters are read in nested function bodies.
- Suppress framework callback signatures when function is registered via callback-style calls
  (for example `signal.signal(..., handler)`).
- Suppress entry-point functions using existing entry-point detection.
- Support explicit suppressions with `# @invar:allow dead_param: <reason>`.

Regression coverage added:

- nested closure capture usage
- signal callback registration signature handling
- click entry-point signature handling
- explicit allow-marker suppression
- negative guardrail: non-registrar callback still reports dead param

### 2) `stub_body` precision tuning

Files:

- `src/invar/core/stub_body.py`
- `tests/core/test_stub_body.py`

Changes:

- Suppress placeholder-body findings for framework entry points.
- Support explicit suppressions with `# @invar:allow stub_body: <reason>`.

Regression coverage added:

- click group entry-point stub exemption
- explicit allow-marker suppression

## Verification Evidence

Targeted rule tests and doctests:

```bash
uv run python -m pytest -q \
  tests/core/test_dead_param.py \
  tests/core/test_stub_body.py \
  --doctest-modules src/invar/core/dead_param.py src/invar/core/stub_body.py
```

Observed:

- `29 passed`, `0 failed`

Cross-project comparison artifact (same command shape as baseline run):

- `docs/testing/artifacts/wiring-cross-project-validate-fix-wave1.json`
- Wave-1 counts moved from `25` findings (`dead_param=24`, `stub_body=1`) to `7`
  findings (`dead_param=7`, `stub_body=0`, `wiring_gap=0`).

## Scope Note

This document is a fix-step artifact only. Independent precision/FP categorization
for gate criteria is deferred to `wiring-integrity-1.cross-project-validate-retest`.
