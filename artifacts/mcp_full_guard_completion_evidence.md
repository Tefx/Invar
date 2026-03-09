## Evidence Correction Report

**Corrected artifact**: `artifacts/mcp_full_guard_completion_evidence.md`
**Target context**: repo root (see raw outputs)
**Incorrect path(s) removed**: any worktree-local artifact provenance references (non-verifiable post-merge)

### Raw command outputs
- Command: `pwd && git rev-parse --show-toplevel && git rev-parse HEAD`
  - Raw output:
    ```
    /Users/tefx/Projects/invar
    /Users/tefx/Projects/Invar
    bc823c3b21575642705674e6019a1e851c0a60b2
    ```

- Command: `test -f "artifacts/mcp_full_guard_completion_evidence.md" && ls -l "artifacts/mcp_full_guard_completion_evidence.md"`
  - Raw output:
    ```
    -rw-r--r--@ 1 tefx  staff  4072 10 Mar 00:20 artifacts/mcp_full_guard_completion_evidence.md
    ```

- Command: `python3 -c "import os, subprocess; top=subprocess.check_output(['git','rev-parse','--show-toplevel'], text=True).strip(); print('top=', top); print('samefile(pwd,top)=', os.path.samefile(os.getcwd(), top));"`
  - Raw output:
    ```
    top= /Users/tefx/Projects/Invar
    samefile(pwd,top)= True
    ```

### Provenance check
- [x] No worktree-path ambiguity remains (no worktree-local paths referenced)
- [x] Every claimed context-proof command has raw output attached
- [x] Artifact references prior evidence history without rewriting it

Prior evidence history reference (unchanged factual record):
- Deferred run id: `grd_241421c8ce244860934b07d0`
- Prior terminal status observation: `invar_invar_guard_status(run_id="grd_241421c8ce244860934b07d0")` returned `status=failed` at `2026-03-09T15:23:59.066487Z`.
