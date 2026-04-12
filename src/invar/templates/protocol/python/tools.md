## Commands (Python)

```bash
invar guard              # Check git-modified files (fast, default)
invar guard --all        # Check entire project (CI, release)
invar guard --static     # Static only (quick debug, ~0.5s)
invar guard --coverage   # Collect branch coverage
invar guard -c           # Contract coverage only (DX-63)
invar guard --mutation   # Enable mutation testing (DX-97)
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
invar rules              # List all rules with detection/hints (JSON)
```

**Default behavior**: Checks git-modified files for fast feedback during development.
Use `--all` for comprehensive checks before release.

## Configuration (Python)

```toml
# pyproject.toml
[tool.invar.guard]
core_paths = ["src/myapp/core"]    # Default: ["src/core", "core"]
shell_paths = ["src/myapp/shell"]  # Default: ["src/shell", "shell"]
max_file_lines = 500               # Default: 500 (warning at 80%)
max_function_lines = 50            # Default: 50
timeout_doctest = 60                 # Default: 60s
timeout_crosshair = 300              # Default: 300s
timeout_hypothesis = 300             # Default: 300s
# Doctest lines are excluded from size calculations

# DX-97: Mutation testing configuration
mutation_enabled = false             # Default: false (enable via --mutation flag)
mutation_timeout = 60                # Default: 60s (per-mutant timeout, 1-600)
```

```toml
# invar.toml
[guard]
core_paths = ["src/myapp/core"]
shell_paths = ["src/myapp/shell"]
```

`.invar/config.toml` is deprecated and no longer loaded.

## Mutation Testing (DX-97)

Mutation testing runs after all standard verification phases pass. It measures
test effectiveness by introducing small code mutations and verifying that tests
catch them.

### Activation

Mutation testing is **disabled by default**. Enable via:

1. **CLI flag** (one-time): `invar guard --mutation`
2. **Config** (persistent): Set `mutation_enabled = true` in pyproject.toml

### Full-Scan Mutation

`invar guard --all --mutation` runs mutation testing across the entire project.
Large full scans may return a deferred handle (`status: deferred`) for
async completion via `invar_guard_status`/`invar_guard_wait`.

### Output Semantics

Mutation output includes additive fields in agent JSON:

```json
{
  "mutation": {
    "total": 10,
    "killed": 8,
    "survived": 1,
    "timeout": 0,
    "error": 1,
    "score": 80.0,
    "passed": true,
    "eligible_files": 3,
    "ineligible_files": 1,
    "files_with_zero_sites": 1,
    "survivor_evidence": ["src/core/calc.py:42:Add"]
  }
}
```

**Fail-closed semantics:**
- `timeout > 0`: Fails regardless of score (test took too long)
- `error > 0`: Fails regardless of score (internal error occurred)
- `survived > threshold`: Fails if score < 80%

**File classification:**
- `eligible_files`: Files with mutation sites that were tested
- `ineligible_files`: Files skipped due to parse/import errors
- `files_with_zero_sites`: Files that parsed OK but had no mutation candidates

**Note:** There is no standalone `invar mutate` command. Mutation is an
optional phase of `invar guard`, activated via `--mutation` flag or config.
