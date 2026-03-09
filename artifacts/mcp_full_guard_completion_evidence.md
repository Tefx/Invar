## Evidence Correction Report

**Corrected artifact**: /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance/artifacts/mcp_full_guard_completion_evidence.md
**Target context**: /Users/tefx/Projects/Invar
**Incorrect path(s) removed**: /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.capture-completed-large-repo-mcp-full-guard-evidence/artifacts/mcp_full_guard_completion_evidence.md

### Raw command outputs
- Command: `git worktree list --porcelain`
  - Target context: `/Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance`
  - Raw output:
    ```
    worktree /Users/tefx/Projects/Invar
    HEAD 14d2b07bbdcc5e38295ccda801f4994e40372797
    branch refs/heads/Main

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/da-while-field.fix-anima-environment-runtime-parity
    HEAD 14d2b07bbdcc5e38295ccda801f4994e40372797
    branch refs/heads/vectl/step-da-while-field.fix-anima-environment-runtime-parity

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/da-while-field.retest-anima-guard-loop-carried-state
    HEAD 0f6f86e863fc311db972b708cb9c1ff9ece184c7
    branch refs/heads/vectl/step-da-while-field.retest-anima-guard-loop-carried-state

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/da-while-repro.da-while-repro-fix-snapshot-reproduction-anchoring
    HEAD 14d2b07bbdcc5e38295ccda801f4994e40372797
    branch refs/heads/vectl/step-da-while-repro.da-while-repro-fix-snapshot-reproduction-anchoring

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/da-while-repro.da-while-repro-retest-pre-fix-repros
    HEAD 0f6f86e863fc311db972b708cb9c1ff9ece184c7
    branch refs/heads/vectl/step-da-while-repro.da-while-repro-retest-pre-fix-repros

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-design.gate-fix-blockers
    HEAD 14d2b07bbdcc5e38295ccda801f4994e40372797
    branch refs/heads/vectl/step-mcp-full-guard-design.gate-fix-blockers

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance
    HEAD 14d2b07bbdcc5e38295ccda801f4994e40372797
    branch refs/heads/vectl/step-mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance

    worktree /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.review-results
    HEAD 0f6f86e863fc311db972b708cb9c1ff9ece184c7
    branch refs/heads/vectl/step-mcp-full-guard-field-verify.review-results
    ```

- Command: `pwd && git rev-parse --show-toplevel`
  - Target context: `/Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance`
  - Raw output:
    ```
    /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance
    /Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance
    ```

- Command: `python3 -c "import os; print(os.path.samefile('/Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance','/Users/tefx/Projects/Invar'))"`
  - Target context: `/Users/tefx/Projects/Invar/.vectl/worktrees/mcp-full-guard-field-verify.correct-completed-large-repo-mcp-full-guard-evidence-provenance`
  - Raw output:
    ```
    False
    ```

### Provenance check
- [x] No worktree-path ambiguity remains
- [x] Every claimed context-proof command has raw output attached
- [x] Artifact references prior evidence history without rewriting it

Prior evidence history reference (unchanged factual record):
- Deferred run id: `grd_241421c8ce244860934b07d0`
- Prior terminal status observation: `invar_invar_guard_status(run_id="grd_241421c8ce244860934b07d0")` returned `status=failed` at `2026-03-09T15:23:59.066487Z`.
