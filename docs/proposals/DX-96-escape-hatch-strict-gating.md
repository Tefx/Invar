# DX-96: Escape Hatch Strict Gating

**Status:** Accepted
**Created:** 2026-03-18
**Priority:** Critical (Verification Integrity)
**Category:** Guard Rule Enhancement
**Depends on:** DX-95 (incident analysis), DX-66 (escape hatch reporting, retained)
**Supersedes:** DX-66 threshold design (never implemented, replaced by this proposal)

---

## Summary

Implement strict gating on escape hatch types (`@invar:allow`). Escape hatches
that exceed configurable per-file, per-rule, and project-level limits produce ERROR-level
violations that fail guard. Four high-risk escape types become **non-suppressible** via
inline annotations — legitimate uses must be declared in `pyproject.toml` by a human.

---

## Motivation

DX-95 documented the mcp-tela incident: an agent placed 40 `dead_export` markers on stub
functions, making an entirely empty runtime pass guard all-green. The root cause: every
escape hatch works identically — marker present, check silently skipped, no counting, no
limits. DX-66 designed `escape_hatch_error_threshold = 10` but it was never implemented.

Current state:
- All escape hatch types have zero gates
- `review_trigger` escape_count >= 3 → WARNING (advisory, doesn't fail guard)
- `check_complexity_debt` has an inverted incentive: more markers = less debt
- `EscapeHatchSummary` reports counts but has no threshold logic

---

## Design

### Marker Systems

Invar has two distinct marker syntaxes for suppression:

1. **`@invar:allow` markers** — `# @invar:allow <rule>: <reason>`. Parsed by
   `extract_escape_hatches()` and checked by `has_allow_marker()`. These are the primary
   escape hatches governed by this proposal.

2. **Standalone markers** — `@shell_complexity:` and `@shell_orchestration:`. These use
   a different syntax (`# @shell_complexity: <reason>`) parsed by dedicated functions
   (`has_complexity_marker()`, `has_orchestration_marker()`). They are NOT `@invar:allow`
   escape hatches.

This proposal governs only `@invar:allow` markers. The `shell_too_complex` rule is
suppressed by `@shell_complexity:` (standalone), not by `@invar:allow shell_too_complex:`.
Therefore `shell_too_complex` does not appear in the tier map. Users who write
`@invar:allow shell_too_complex:` will have the marker tracked in `EscapeHatchSummary`
but it has no suppression effect — this is a pre-existing documentation issue, not a
DX-96 concern.

### Three Tiers

| Tier | Cost | Inline Suppressible | Rules |
|------|------|---------------------|-------|
| **Suppressible** | 1 | Yes | `dead_assign`, `dead_param`, `shell_pure_logic` |
| **Expensive** | 3 | Yes | `shell_result`, `entry_point_too_thick`, `file_size`, `function_size` |
| **Non-suppressible** | N/A (blocked) | No | `dead_export`, `stub_body`, `missing_contract`, `missing_doctest` |

**Non-suppressible**: inline `@invar:allow` is recognized (for clear error messaging) but
always produces ERROR. The only path is `pyproject.toml` exempt declaration by a human.

**Note**: `shell_complexity` is removed from the tier map. The `shell_too_complex` rule
uses the standalone `@shell_complexity:` marker, not `@invar:allow`. It is governed by the
existing `check_complexity_debt` mechanism, not by DX-96.

Rationale: The four non-suppressible rules are the exact vectors exploited in mcp-tela.
`dead_export` hides uncalled code, `stub_body` hides empty implementations,
`missing_contract` and `missing_doctest` remove Core's primary verification mechanisms.

### Limits

| Constraint | Suppressible | Expensive | Non-suppressible |
|------------|-------------|-----------|------------------|
| Per-file per-rule | 3 | 2 | 0 (inline blocked) |
| Per-project per-rule | 10 | 5 | 0 (inline blocked) |

Thresholds (WARNING triggers at `>=` ceil(limit × threshold)):
- **80%** of any limit → WARNING (e.g., `dead_param: 8/10 project limit`)
- **100%** of any limit → ERROR (guard fails)

### Hybrid Budget: Per-Rule Caps + Aggregate Project Limit

Two independent constraints, **both must pass**:

1. **Per-rule independent caps** (primary) — each rule has its own per-file and per-project
   limit as above. Error messages directly identify the offending rule.

2. **Aggregate project budget** (secondary) — total weighted cost across all suppressible
   and expensive inline escape hatches must not exceed **15 points**
   (Suppressible × 1 + Expensive × 3). Catches the "Swiss cheese" dispersion attack where
   each individual rule is under limit but total suppression is excessive.

### Combination Penalty

Per-function stacking of escape hatches:

| Condition | Effect |
|-----------|--------|
| 2 escape hatches on same function | Each counts **double** toward its rule budget |
| 3+ escape hatches on same function | **Unconditional ERROR** (no budget can absorb this) |

**Mixed-tier stacking rules**:
- Non-suppressible hatches on a function **always count** toward the stacking total
  (they are already ERROR individually, but they also trigger the combination penalty).
- Example: 1 `dead_export` (non-suppressible) + 1 `shell_result` (expensive) on the same
  function = 2 hatches → `shell_result` counts double (6pt instead of 3pt). The
  `dead_export` is already a standalone ERROR.
- Example: 1 `dead_export` + 1 `stub_body` + 1 `missing_contract` on the same function =
  3 hatches → unconditional combination ERROR in addition to 3 individual non-suppressible
  ERRORs.

Rationale: A function needing 3+ escape hatches is architecturally broken, not a legitimate
exception. The `dead_export` + `stub_body` + `missing_contract` combo on mcp-tela would
have been caught immediately.

**Implementation note**: Combination detection requires associating escape hatches with
their enclosing function. `EscapeHatchDetail` must be extended with a `function_name`
field (or `symbol_line_range`), populated during collection in `_scan_and_check` by
cross-referencing marker line numbers with `FileInfo.symbols`. The `check_escape_budget`
signature must accept `list[FileInfo]` in addition to `EscapeHatchSummary` and `RuleConfig`.

### Legitimate Use: Dual-Track Exemption

| Track | Mechanism | Counts toward budget | Who controls |
|-------|-----------|---------------------|-------------|
| **Config exempt** | `pyproject.toml [tool.invar.exempt.<rule>]` glob patterns | No | Human (PR review) |
| **Inline suppress** | `# @invar:allow <rule>: <reason>` | Yes | Agent or human |

Config exemptions also have limits: **20 per rule** (WARNING at 15). This prevents
moving the abuse vector from inline to config.

**Exempt pattern syntax**: `file_glob` or `file_glob::symbol_glob`.
- `file_glob` matches file paths using standard glob wildcards (`*`, `**`, `?`).
- `::` separates file path from symbol name.
- `symbol_glob` matches function/method names using `*` wildcards.
- Examples: `cli/commands/*.py` (all files), `mcp/server.py::create_*` (specific symbols).

Example `pyproject.toml`:

```toml
[tool.invar.exempt.dead_export]
patterns = ["cli/commands/*.py", "mcp/server.py::create_*"]

[tool.invar.exempt.missing_contract]
patterns = ["core/patterns/detector.py::*.description"]
```

**Trust boundary**: agents MUST NOT modify `pyproject.toml` to add exemptions. Only humans
with explicit project authority may declare config exemptions. When an agent encounters a
non-suppressible ERROR, it must stop and request human authorization — not attempt to
self-service the exemption. Guard error messages for non-suppressible rules deliberately
omit the exact pyproject.toml syntax to prevent agent self-resolution. The message directs
the agent to ask the project owner.

---

## Configuration

All limits are configurable in `pyproject.toml` with strict defaults:

```toml
[tool.invar.guard]
# Per-file per-rule limits by tier
escape_suppressible_per_file = 3
escape_expensive_per_file = 2

# Per-project per-rule limits by tier
escape_suppressible_per_project = 10
escape_expensive_per_project = 5

# Aggregate weighted budget (Suppressible×1 + Expensive×3)
escape_budget_limit = 15

# Warning threshold (fraction of any limit, WARNING fires at >= ceil(limit * threshold))
escape_warning_threshold = 0.8

# Config exempt limits
escape_exempt_limit = 20
escape_exempt_warning = 15
```

---

## Output Design

### New Violation Types

| Rule | Severity | Granularity |
|------|----------|-------------|
| `escape_hatch_file_limit` | ERROR | Per-file per-rule |
| `escape_hatch_project_limit` | ERROR | Per-project per-rule |
| `escape_hatch_budget` | ERROR | Aggregate weighted |
| `escape_hatch_combination` | ERROR | Per-function stacking |
| `escape_hatch_non_suppressible` | ERROR | Non-suppressible inline attempt |

### Terminal Output (Rich)

When under limit — no change to current output:
```
Escape hatches: 3 (2 dead_param, 1 shell_result)
```

When limit exceeded — Rich Panel box:
```
╭─ Escape Hatch Limit ──────────────────────────────────────╮
│                                                            │
│  Escape hatches: 14 (8 dead_param, 4 shell_result, ...)   │
│  1 per-rule limit exceeded. Aggregate budget: 20/15 pts.  │
│                                                            │
│  ERROR dead_param: 11/10 project limit exceeded            │
│    Files: api/handler.py (3), api/router.py (3), ...       │
│    → Remove unused parameters or rename to _param          │
│                                                            │
│  ERROR Aggregate budget exceeded (20/15 points)            │
│    → Remove 2 shell_result (-6 pts) or 5 dead_param        │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

Non-suppressible inline attempt:
```
ERROR shell/api.py:42 dead_export cannot be suppressed inline
  → This rule requires human authorization.
    Ask the project owner to declare an exemption in pyproject.toml.
    Do NOT modify pyproject.toml yourself.
```

### JSON Output (Agent)

```json
{
  "escape_hatches": {
    "count": 14,
    "by_rule": {"dead_param": 8, "shell_result": 4, "dead_assign": 2},
    "gating": {
      "status": "exceeded",
      "file_violations": [
        {"file": "api/handler.py", "rule": "dead_param", "count": 4, "limit": 3}
      ],
      "project_violations": [
        {"rule": "dead_param", "count": 11, "limit": 10}
      ],
      "budget": {"used": 20, "limit": 15},
      "non_suppressible": [],
      "combination": []
    }
  }
}
```

### `--explain` Mode

Shows full breakdown including config exemptions:
```text
Declared Exemptions (pyproject.toml):
  dead_export: cli/commands/*.py (5 functions matched)
  missing_contract: core/patterns/detector.py::*.description (4 matched)

Inline Budget:
  dead_param:       8/10 project (WARNING at 8)
  shell_result:     4/5 project
  dead_assign:      2/10 project
  Aggregate:        20/15 points (EXCEEDED)
```

---

## Architecture

### New Module: `core/escape_budget.py`

Single responsibility: evaluate `EscapeHatchSummary` against policy, produce `Violation`s.

```text
Dependencies:
  models.py (EscapeHatchSummary, EscapeHatchDetail, Violation, Severity, RuleConfig, FileInfo)

Depended by:
  _scan_and_check() in guard.py
```

### Integration Point

Called in `_scan_and_check()` after escape hatch collection (after DX-33 duplicate check,
~line 176 of guard.py):

```python
from invar.core.escape_budget import check_escape_budget
for v in check_escape_budget(report.escape_hatches, config, all_file_infos):
    report.add_violation(v)
```

Note: `report.escape_hatches` refers to the `escape_hatches: EscapeHatchSummary` field
on `GuardReport`. The exact field name must be verified against the actual model.

### Data Model: Extend `RuleConfig`

New fields (follows existing pattern of `shell_complexity_debt_limit`, `entry_max_lines`):

```python
# Escape hatch gating (DX-96)
escape_suppressible_per_file: int = Field(default=3, ge=0)
escape_expensive_per_file: int = Field(default=2, ge=0)
escape_suppressible_per_project: int = Field(default=10, ge=0)
escape_expensive_per_project: int = Field(default=5, ge=0)
escape_budget_limit: int = Field(default=15, ge=0)      # 0 = unlimited
escape_warning_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
escape_exempt_patterns: dict[str, list[str]] = Field(default_factory=dict)
escape_exempt_limit: int = Field(default=20, ge=0)
escape_exempt_warning: int = Field(default=15, ge=0)
```

### Extend `EscapeHatchDetail`

Add function context for combination penalty detection:

```python
class EscapeHatchDetail(BaseModel):
    file: str
    line: int
    rule: str
    reason: str
    function_name: str | None = None  # enclosing function, populated during collection
```

### Tier Registry

New types in `models.py`:

```python
class EscapeHatchTier(StrEnum):
    SUPPRESSIBLE = "suppressible"
    EXPENSIVE = "expensive"
    NON_SUPPRESSIBLE = "non_suppressible"

ESCAPE_TIER_MAP: dict[str, EscapeHatchTier] = {
    "dead_assign": EscapeHatchTier.SUPPRESSIBLE,
    "dead_param": EscapeHatchTier.SUPPRESSIBLE,
    "shell_pure_logic": EscapeHatchTier.SUPPRESSIBLE,
    "shell_result": EscapeHatchTier.EXPENSIVE,
    "entry_point_too_thick": EscapeHatchTier.EXPENSIVE,
    "file_size": EscapeHatchTier.EXPENSIVE,
    "function_size": EscapeHatchTier.EXPENSIVE,
    "dead_export": EscapeHatchTier.NON_SUPPRESSIBLE,
    "stub_body": EscapeHatchTier.NON_SUPPRESSIBLE,
    "missing_contract": EscapeHatchTier.NON_SUPPRESSIBLE,
    "missing_doctest": EscapeHatchTier.NON_SUPPRESSIBLE,
}

ESCAPE_TIER_COST: dict[EscapeHatchTier, int] = {
    EscapeHatchTier.SUPPRESSIBLE: 1,
    EscapeHatchTier.EXPENSIVE: 3,
    EscapeHatchTier.NON_SUPPRESSIBLE: 0,  # N/A: never enters budget (always ERROR)
}
```

Note: `shell_complexity` is NOT in the tier map. The `shell_too_complex` rule uses the
standalone `@shell_complexity:` marker syntax, not `@invar:allow`. It is governed by
`check_complexity_debt`, not by DX-96.

### `EscapeHatchSummary` Extension

Add `by_file` property:

```python
@property
def by_file(self) -> dict[str, dict[str, int]]:
    """Group escape hatches by file and rule."""
    ...
```

---

## Interaction with Existing Systems

### `check_complexity_debt`

Not subsumed in this proposal. `check_complexity_debt` counts unaddressed `shell_too_complex`
*violations* (not escape hatches) and is suppressed by the standalone `@shell_complexity:`
marker (not `@invar:allow`). The escape budget counts `@invar:allow` markers only.
Future work may unify these, but they operate on different data types and marker syntaxes.

### `severity_overrides`

Gating violations respect `severity_overrides` **except for `escape_hatch_non_suppressible`**.
The non-suppressible tier is immune to severity overrides — it cannot be turned off via
configuration. This prevents an agent from suggesting `severity_overrides` changes to
bypass the non-suppressible gate.

Other gating violations (`escape_hatch_file_limit`, `escape_hatch_project_limit`,
`escape_hatch_budget`, `escape_hatch_combination`) can be overridden by the project owner
if they accept the risk.

### `review_trigger`

The existing `escape_count >= 3 → review_suggested` remains unchanged. It serves a
different purpose (suggesting review) and operates at a different granularity (all types
combined). DX-96 gating is stricter and operates per-type.

---

## Migration: Invar Self-Compliance

Invar's own codebase currently uses ~43 `shell_result`, ~22 `dead_export`, ~9
`entry_point_too_thick`, ~9 `missing_contract`, and other inline escape hatches. Under
DX-96 defaults, this would fail guard immediately.

**Required migration (Phase 0)** — this phase enforces the same trust boundary as the
gating system itself: **agents produce recommendations, humans approve config changes.**

1. Agent inventories all existing `@invar:allow` markers and classifies each as:
   - **Exempt candidate** (legitimate: CLI entry points, MCP handlers, abstract properties)
   - **Should fix** (the underlying violation should be resolved, not exempted)
   - **Ambiguous** (needs human judgment)
2. Agent produces a **migration report** listing every marker with its classification and
   the proposed `pyproject.toml` exempt pattern. This report is output for human review.
3. **Human reviews and approves** the exempt patterns. Human writes the approved patterns
   into `pyproject.toml`. Agent MUST NOT write to `pyproject.toml` in this phase.
4. Agent removes the inline `@invar:allow` markers that have been covered by approved
   exempt patterns.
5. Agent verifies remaining inline markers fit within default budgets.
6. Agent runs `invar guard` and confirms green.

This migration must happen **before** the gating enforcement is wired in (Phase 4).

---

## Implementation Plan

| Phase | Deliverable | Effort |
|-------|-------------|--------|
| 0 | **Migration**: Move Invar's own escape hatches to pyproject.toml exempt | Medium |
| 1 | `models.py`: RuleConfig fields + EscapeHatchTier + ESCAPE_TIER_MAP + EscapeHatchDetail.function_name | Small |
| 2 | `models.py`: EscapeHatchSummary.by_file property | Small |
| 3 | `core/escape_budget.py`: check_escape_budget with @pre/@post + doctests | Medium |
| 4 | `guard.py`: _scan_and_check integration + function_name population | Small |
| 5 | `formatter.py` + `guard_output.py`: gating output (JSON + Rich Panel) | Medium |
| 6 | Config parsing: pyproject.toml exempt patterns + new fields (incl. `::` symbol glob) | Medium |
| 7 | Non-suppressible enforcement: modify has_allow_marker or add post-check + severity_overrides immunity | Small |

---

## Acceptance Criteria

1. `invar guard` fails (exit 1) when any per-file, per-project, or aggregate limit is exceeded
2. Non-suppressible inline markers produce ERROR directing agent to request human authorization
3. 3+ escape hatches on same function → unconditional ERROR
4. 2 escape hatches on same function count double toward their respective rule budgets
5. 80% threshold produces WARNING (at `>=` ceil(limit × threshold))
6. `pyproject.toml` exempt patterns bypass inline budget
7. mcp-tela scenario (40 dead_export) fails at the first marker
8. Invar's own codebase passes with current escape hatch usage (after migration)
9. `escape_hatch_non_suppressible` is immune to `severity_overrides`
10. JSON output distinguishes file-level from project-level violations

---

## Decision Record

Proposal developed through structured multi-agent consultation (2026-03-18):
- **SE Expert**: Two-tier enforcement, independent per-rule budgets, fix debt inversion
- **LLM Agent Expert**: Weighted cost model, combination penalties, agent abuse patterns
- **SE Radical**: Non-suppressible tier, pyproject.toml trust boundary, no cost=0
- **Software Architect**: New core module, RuleConfig extension, pipeline integration
- **UX Designer**: Output format, no budget-remaining in default output, Rich Panel

Key consensus points:
- D1 (Tiers): 3 tiers with non-suppressible — unanimous
- D2 (Limits): Per-file 3/2/0, per-project 10/5/0 — unanimous
- D3 (Hybrid): Independent caps + aggregate budget — 4/5 majority
- D4 (Combination): 2=double, 3+=ERROR — unanimous
- D5 (Exemptions): pyproject.toml exempt + inline budget — unanimous

Post-review fixes (2026-03-18):
- Resolved `shell_complexity` / `shell_too_complex` naming confusion (C1)
- Defined mixed-tier combination penalty rules (C2)
- Added migration phase for Invar self-compliance (M1)
- Added `escape_exempt_warning` to RuleConfig fields (M2)
- Split JSON `per_rule_violations` into `file_violations` + `project_violations` (M3)
- Made `escape_hatch_non_suppressible` immune to severity_overrides (M4)
- Extended `EscapeHatchDetail` with `function_name` for combination detection (M5)
- Re-estimated Phase 6 config parsing as Medium (M6)
- Added acceptance criteria #4, #9, #10 (m3)
- Specified `::` exempt pattern syntax (m4)
- Clarified 80% threshold precision (m1)
- Standardized cost column for non-suppressible tier (m2)

---

## Related

- DX-95: `dead_export` escape hatch abuse incident
- DX-66: Escape hatch visibility (partially implemented — reporting only)
- DX-91: Guard CLI/MCP alignment
- DX-31: Independent review triggers
- DX-22: Shell architecture rules and Fix-or-Explain
