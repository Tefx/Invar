# DX-26: Guard Command Simplification

**Status:** Draft
**Created:** 2025-12-24
**Principle:** Agent-Native, Zero Backward Compatibility Concerns

## Problem

The `invar guard` command has accumulated complexity:
- 9 CLI parameters with overlapping purposes
- 3 JSON output modes (`--json`, `--agent`, auto-detect)
- Redundant commands (`invar test`, `invar verify`)
- Dead code from removed features (`--prove`, `--thorough`)
- MCP uses wrong output mode (missing verification details)

## Current State

### CLI Parameters (9)
```
path              # Project root
--strict          # Warnings as errors
--no-strict-pure  # Disable purity checks
--pedantic        # Show off-by-default rules
--explain         # Detailed explanations
--changed         # Git-modified files only
--agent           # JSON with fix instructions
--json            # Simple JSON
--static          # Skip runtime tests
```

### MCP Parameters (3)
```
path     # default: "."
changed  # default: True
strict   # default: False
```

### Issues Found

| Issue | Impact |
|-------|--------|
| MCP uses `--json` instead of `--agent` | Missing verification_level, test results, fix instructions |
| `--json` vs `--agent` confusion | When would agent want simple JSON? |
| `--no-strict-pure` double negative | Confusing semantics |
| `--pedantic` rarely used | Agents don't need off-by-default rules |
| `--explain` human-only | Not useful for JSON output |
| `invar test` / `invar verify` redundant | `guard` already runs both |
| `detect_verification_context()` dead code | Always returns STANDARD |
| Docs still reference `--prove` | Removed in DX-19 |

## Proposal

### 1. Unified Output Mode

**Remove:** `--json`, `--agent`

**Add:** `--human` (force human-readable output)

**Behavior:**
```
TTY detected     → Human-readable (Rich)
Non-TTY detected → Full JSON (agent-optimized)
--human flag     → Force human-readable (for testing/debugging)
```

**Rationale:**
- Agents run in non-TTY → auto JSON
- Humans run in terminal → auto Rich
- When developing Invar itself, agent can use `--human` to test human output

```python
# Before (confusing)
if json_output:
    output_json(report)           # Simple JSON
elif agent or _detect_agent_mode():
    output_agent(report, ...)     # Full JSON
else:
    output_rich(report, ...)      # Human

# After (clear)
if human_flag or sys.stdout.isatty():
    output_rich(report, ...)      # Human
else:
    output_agent(report, ...)     # Full JSON (always complete)
```

### 2. Remove Redundant Commands

**Delete:** `invar test`, `invar verify`

**Keep:** `invar guard` (single entry point)

**Rationale:**
- `guard` already runs static + doctests + CrossHair + Hypothesis
- Separate commands violate Agent-Native (zero decisions)
- Usage data: `invar guard` ~100%, `invar test/verify` ~0%

### 3. Simplify Flags

**Before (9):**
```
path, --strict, --no-strict-pure, --pedantic, --explain,
--changed, --agent, --json, --static
```

**After (5):**
```
path        # Project path (positional)
--changed   # Git-modified files only
--strict    # Warnings as errors
--static    # Skip runtime tests (debug mode)
--human     # Force human-readable output (testing)
```

**Removed:**
| Flag | Reason |
|------|--------|
| `--no-strict-pure` | If purity checks wrong, fix the checks |
| `--pedantic` | Agents don't need off-by-default rules |
| `--explain` | Verbosity should be per-output-mode, not flag |
| `--agent` | Replaced by auto-detect |
| `--json` | Replaced by auto-detect |

### 4. Fix MCP

**Before:**
```python
cmd.append("--json")  # Wrong: simple JSON, missing info
```

**After:**
```python
# No output flag needed - non-TTY auto-detects to full JSON
```

MCP output will include:
- `verification_level`
- `doctest` results
- `crosshair` results
- `property_tests` results
- Fix instructions

### 5. Clean Dead Code

**Remove:**
- `detect_verification_context()` - always returns STANDARD
- `VerificationLevel` comments about `--thorough`
- `invar test` command and `test_cmd.py`
- `invar verify` command
- `INVAR_MODE=agent` env check (non-TTY sufficient)
- `_detect_agent_mode()` function (inline the TTY check)

**Update:**
- Documentation references to `--prove` (removed in DX-19)
- MCP instructions to reflect simplified interface

## Resulting Interface

### CLI
```bash
invar guard [path]           # Full verification (default)
invar guard --changed        # Git-modified files only (common)
invar guard --static         # Static only (debug)
invar guard --strict         # Warnings as errors (CI)
invar guard --human          # Force human output (testing)
```

### MCP
```python
invar_guard(
    path=".",
    changed=True,   # Default True (agent's common case)
    strict=False,
)
# Output: Always full JSON with all verification details
```

### Output Modes

| Context | Output |
|---------|--------|
| Terminal (TTY) | Rich human-readable |
| Pipe/redirect (non-TTY) | Full agent JSON |
| `--human` flag | Rich human-readable |

### Agent JSON Schema
```json
{
  "status": "passed",
  "verification_level": "standard",
  "files_checked": 42,
  "errors": 0,
  "warnings": 3,
  "violations": [...],
  "doctest": {"passed": true, "output": ""},
  "crosshair": {"status": "verified", "verified": [...]},
  "property_tests": {"functions_tested": 151, "passed": 151},
  "fix_instructions": [...]
}
```

## Implementation

### Phase 1: Fix MCP Bug (Immediate)
1. Remove `--json` from MCP server
2. Verify non-TTY auto-detection works

### Phase 2: Simplify CLI
1. Add `--human` flag
2. Remove `--json`, `--agent`, `--pedantic`, `--explain`, `--no-strict-pure`
3. Update help text

### Phase 3: Remove Dead Code
1. Delete `invar test`, `invar verify` commands
2. Delete `detect_verification_context()`
3. Delete `_detect_agent_mode()` (inline TTY check)
4. Clean up `VerificationLevel` comments

### Phase 4: Documentation
1. Update CLAUDE.md
2. Update context.md (remove `--prove` references)
3. Update MCP instructions

## Migration

**Not needed** - this is a breaking change proposal with no backward compatibility.

For projects that might use old flags:
- `--json` → remove (auto-detect)
- `--agent` → remove (auto-detect)
- `--prove` → remove (merged into default)
- `--pedantic` → remove (rarely used)
- `--explain` → remove (use `--human` if needed)
- `--no-strict-pure` → configure in `pyproject.toml` if needed

## Metrics

| Before | After |
|--------|-------|
| 9 CLI flags | 5 CLI flags |
| 3 output modes | 2 output modes (auto) |
| 5 commands | 3 commands |
| ~50 lines output logic | ~20 lines |

## Decision

- [ ] Approved
- [ ] Rejected
- [ ] Needs revision
