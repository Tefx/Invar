# Agent-Native Improvements Roadmap

*Created: 2025-12-19*
*Updated: 2025-12-20*
*Status: Phase 9 Complete*

## Background

These proposals emerged from reflecting on Invar from an AI agent's perspective after implementing Phases 1-8. The goal is to reduce friction, improve signal-to-noise ratio, and make Invar genuinely useful for agents rather than just "formally compliant."

## Completion Summary

**Phase 9 (v0.1.0):** Proposals P1-P6, P8, P11, P12, P14 implemented and released.

---

## Proposals

### P1: Relaxed Limits + Config-Level Exclusions (Revised)

**Status:** Complete (v0.1.0)
**Priority:** P0 (High impact, Low effort)
**Affects:** Config, Guard

**Problem:**
Original P1 proposed inline suppression comments, but after reflection:
- Per-function suppression encourages laziness over improvement
- Agents can generate plausible-sounding reasons without real justification
- Adds cognitive load: remember syntax, know rule names, judge when to suppress
- Creates new "formal compliance" loopholes

**Revised Solution:**
Instead of inline suppression, we:

1. **Raise default limits** (less friction, no escape hatch needed)
2. **Config-level exclusions** (centralized, auditable)
3. **File-level skip only** (for genuinely special files)

**Part 1: Relaxed Limits**
```toml
[tool.invar.guard]
max_file_lines = 500      # Was 300, now 500
max_function_lines = 50   # Keep at 50 (forces good design)
```

Rationale:
- File size 300→500: Allows room for growth without constant refactoring
- Function size stays 50: Functions should be small; limit drives improvement

**Part 2: Config-Level Exclusions**
```toml
[tool.invar.guard]
rule_exclusions = [
    { pattern = "**/generated/**", rules = ["*"] },
    { pattern = "**/data/**", rules = ["file_size"] },
]
```

- Centralized management, easy to audit
- Agent doesn't make per-violation decisions
- No "write a reason" burden

**Part 3: File-Level Skip (Minimal)**
```python
# invar-config: skip file_size -- data definitions only
```

- Only for truly special files that don't fit patterns
- File-level only, no function-level
- Reported as INFO for audit trail

**Implementation:**
1. `core/models.py`: Update `RuleConfig` default `max_file_lines = 500`
2. `core/models.py`: Add `rule_exclusions: list[RuleExclusion]`
3. `shell/config.py`: Parse `rule_exclusions` from config
4. `core/rules.py`: Apply exclusions before checking rules
5. `core/parser.py`: Extract `# invar-config:` comments (file-level only)

**Decision Log:**
- 2025-12-19: Original P1 (inline suppression) rejected as too complex
- 2025-12-19: Simplified to config-level exclusions + raised limits

---

### P2: Severity Configuration

**Status:** Complete (v0.1.0)
**Priority:** P0 (High impact, Low effort)
**Affects:** Config, Guard output

**Problem:**
28 INFO-level `redundant_type_contract` warnings cluttered output during Phase 8.

**Root Cause Analysis:**
```
Invar requires @pre/@post on Core functions
    ↓
Agent can't find meaningful constraints for some functions
    ↓
Agent writes isinstance() checks to comply
    ↓
Guard flags as redundant_type_contract
    ↓
Noise accumulates
```

This is NOT agent misbehavior - it's the system working as designed. When a function
like `double(x: int) -> int` truly has no constraints beyond types, `isinstance` is
the only thing an agent CAN write.

**Decision:** Accept that some contracts are "trivial" - this is inherent cost of
forcing contracts. The value of forcing contracts (making agents think) outweighs
the noise, but we should manage the noise better.

**Solution:**

1. **Default `redundant_type_contract` to off** - Accept this as expected behavior
2. **Per-rule severity override in config** - Let projects tune signal-to-noise
3. **Add `--pedantic` flag** - Show all violations including normally-off ones

**Note:** `invar rules` command moved to P3 (Rule Metadata System) for unified implementation.

**Part 1: New Default**
```python
# redundant_type_contract is now off by default
# empty_contract remains WARNING (lambda: True is still unacceptable)
```

**Part 2: Config Override**
```toml
[tool.invar.guard]
severity_overrides = {
    redundant_type_contract = "info",  # Re-enable if desired
    empty_contract = "error",          # Upgrade to error
    missing_doctest = "off",           # Disable
}
```

**Severity Options:**
- `"off"`: Don't report
- `"info"`: Report as INFO
- `"warning"`: Report as WARNING
- `"error"`: Report as ERROR (affects exit code)

**Part 3: --pedantic Flag**
```bash
invar guard --pedantic  # Shows ALL violations including off-by-default
```

**Implementation:**
1. `core/models.py`: Add `severity_overrides: dict[str, str]` to RuleConfig
2. `core/rules.py`: Change `redundant_type_contract` default severity to OFF
3. `core/rules.py`: Apply overrides in `check_all_rules()`
4. `shell/cli.py`: Add `--pedantic` flag

**Decision Log:**
- 2025-12-19: Root cause identified - forcing contracts creates trivial contracts
- 2025-12-19: `redundant_type_contract` default changed to OFF
- 2025-12-19: Keep requiring contracts (forces thinking) but manage noise

---

### P3: Rule Metadata System (Revised)

**Status:** Complete (v0.1.0)
**Priority:** P1 (High impact, Medium effort)
**Affects:** Guard output, --agent mode, P5 hints, P6 compression
**Dependencies:** Enhances P5, P11; Enables P6

**Original Problem:**
Every Guard capability addition requires manual INVAR.md Section 7 update.

**Deeper Problem (from discussion):**
- Agent won't proactively run `invar rules` to learn about rules
- Agent won't read Section 7 documentation
- Rule information must be surfaced automatically, not through documentation

**Agent-Native Principle Applied:**
> Don't force agent to read - show them automatically.

**Solution: Centralized RULE_META + Auto-Embed in Output**

Instead of generating documentation that agents won't read, embed rule metadata
directly in Guard output.

**Part 1: Centralized Rule Metadata**

```python
# core/rule_meta.py (NEW)
from dataclasses import dataclass

@dataclass
class RuleMeta:
    """Metadata for a Guard rule."""
    name: str
    severity: Severity
    category: str  # "size", "contracts", "purity", "shell"
    detects: str  # What this rule checks
    cannot_detect: list[str]  # Limitations
    hint: str  # Brief actionable guidance (used by P5)

RULE_META: dict[str, RuleMeta] = {
    "file_size": RuleMeta(
        name="file_size",
        severity=Severity.ERROR,
        category="size",
        detects="File exceeds max_file_lines limit",
        cannot_detect=["Code complexity", "Logical cohesion"],
        hint="Split into smaller modules by responsibility",
    ),
    "param_mismatch": RuleMeta(
        name="param_mismatch",
        severity=Severity.ERROR,
        category="contracts",
        detects="@pre lambda parameter count != function signature",
        cannot_detect=["Runtime type errors", "*args/**kwargs patterns", "Default argument handling"],
        hint="Lambda must include ALL function parameters",
    ),
    "missing_contract": RuleMeta(
        name="missing_contract",
        severity=Severity.WARNING,
        category="contracts",
        detects="Core function without @pre or @post decorator",
        cannot_detect=["Contract semantic correctness", "Logic errors"],
        hint="Ask: what inputs are invalid? what does output guarantee?",
    ),
    # ... all 11 rules
}
```

**Part 2: Auto-Embed in --agent Output**

```json
{
  "files_checked": 5,
  "rules_checked": ["file_size", "function_size", "missing_contract", ...],
  "limitations": "Static analysis only. Runtime behavior, dynamic imports not checked.",
  "violations": [
    {
      "rule": "param_mismatch",
      "rule_meta": {
        "severity": "error",
        "category": "contracts",
        "detects": "@pre lambda parameter count != function signature",
        "cannot_detect": ["Runtime type errors", "*args/**kwargs patterns"],
        "hint": "Lambda must include ALL function parameters"
      },
      "file": "src/core/calc.py",
      "line": 45,
      "message": "Function 'compute' @pre has 1 param but function has 2",
      "fix": { ... }
    }
  ]
}
```

Agent automatically receives:
- What rules were checked
- What each violated rule detects/cannot detect
- Actionable hint for fixing

**Part 3: Auto-Show in --changed Mode**

```
$ invar guard --changed

Checking 2 modified files...

── Rules Applied ──
Core files: file_size, function_size, missing_contract, empty_contract,
            param_mismatch, forbidden_import, internal_import, impure_call
Shell files: file_size, function_size, shell_result

── src/core/calc.py (Core, modified) ──
INSPECT: ...

── Violations ──
...

Note: Static analysis only. Runtime behavior not checked.
```

**Part 4: invar rules Command (Fallback)**

Still exists for explicit queries, but not primary discovery mechanism.

```bash
$ invar rules
Rule                      Severity  Category   Detects
─────────────────────────────────────────────────────────────
file_size                 ERROR     size       File exceeds line limit
function_size             WARNING   size       Function exceeds line limit
missing_contract          WARNING   contracts  Core function without contract
...

$ invar rules param_mismatch
Rule: param_mismatch
Severity: ERROR
Category: contracts
Detects: @pre lambda parameter count != function signature
Cannot detect:
  - Runtime type errors
  - *args/**kwargs patterns
  - Default argument handling
Hint: Lambda must include ALL function parameters
```

When INVAR_MODE=agent (P11), outputs JSON automatically.

**Part 5: Section 7 → docs/LIMITATIONS.md**

- Remove Section 7 from INVAR.md (P6 compression)
- Generate docs/LIMITATIONS.md from RULE_META (for humans)
- Command: `invar docs generate` (optional, for maintainers)

**Implementation Steps:**

1. `core/rule_meta.py`: Define RuleMeta dataclass and RULE_META dict
2. `core/rules.py`: Import hints from RULE_META (connect to P5)
3. `core/formatter.py`: Include rule_meta in --agent output
4. `shell/cli.py`:
   - Add "Rules Applied" section to --changed output
   - Add `invar rules` command
   - Respect INVAR_MODE for output format
5. `core/models.py`: Add `rule_meta` field to Violation (optional)
6. Generate docs/LIMITATIONS.md from RULE_META

**Estimated effort:** ~200 lines, 2-3 hours

**Integration with Other Proposals:**

| Proposal | How P3 Helps |
|----------|--------------|
| P5 (hints) | `hint` field in RULE_META is the source |
| P6 (compression) | Section 7 removed from INVAR.md |
| P11 (INVAR_MODE) | `invar rules` auto-JSON in agent mode |
| P14 (inspection) | "Rules Applied" section in --changed |

**What This Replaces:**

- ~~Manual Section 7 updates~~ → Generated from RULE_META
- ~~Expecting agent to run `invar rules`~~ → Auto-embed in output
- ~~Documentation-based rule discovery~~ → Tool-based discovery

**Decision Log:**
- 2025-12-19: Original P3 (generate Section 7 markdown) deemed insufficient
- 2025-12-19: Revised to auto-embed in output (agent won't read docs)
- 2025-12-19: Priority upgraded P3→P1 (enables P5, P6)

---

### P4: Contract Templates (Lambda Skeleton Only)

**Status:** Complete (v0.1.0)
**Priority:** P2 (Medium impact, Low effort)
**Affects:** Suggestions, --agent mode

**Problem:**
When Guard reports "no contract", agent must manually transcribe parameter names
from signature to lambda. This is mechanical work that:
- Adds no reasoning value
- Creates opportunity for transcription errors (typos, missed params)
- Distracts from the semantic question (what condition?)

**Agent Introspection:**
After deep reflection, the agent identified:
- **Mechanical work** (transcribing params) → Tool should do
- **Reasoning work** (deciding conditions) → Agent should do
- Template skeleton eliminates mechanical errors
- Example conditions might harm reasoning (encourage copy-paste without thinking)

**Solution:**
Generate lambda skeleton ONLY, no example conditions.

**Output:**
```
WARNING ... Function 'process_batch' has no @pre or @post contract
  → Ask: what inputs are invalid? what does output guarantee?
  → Add: @pre(lambda items, config, max_retries: <condition>)
         or @post(lambda result: <condition>)
```

**What P4 does:**
- Extract parameter names from signature
- Generate `@pre(lambda param1, param2, ...: <condition>)`
- Generate `@post(lambda result: <condition>)` as alternative

**What P4 does NOT do:**
- ~~Generate example conditions~~ (might cause mindless copy-paste)
- ~~Type-based suggestions~~ (adds complexity, little value)
- ~~Multiple template options~~ (keep simple)

**Implementation:**
```python
# core/suggestions.py
def _suggest_contract(symbol: Symbol) -> str:
    """Generate contract template from signature."""
    from invar.core.contracts import _extract_func_param_names
    params = _extract_func_param_names(symbol.signature) or []

    if not params:
        return "Add @pre or @post decorator"

    param_str = ", ".join(params)
    return (f"Add: @pre(lambda {param_str}: <condition>)\n"
            f"     or @post(lambda result: <condition>)")
```

**Implementation Steps:**
1. `core/suggestions.py`: Modify `format_suggestion_for_violation()` to call `_suggest_contract()`
2. Reuse `_extract_func_param_names()` from contracts.py
3. Update output formatting in formatter.py

**Estimated effort:** ~35 lines, 20 minutes

**Rationale (from agent introspection):**
- 60% motivation: Avoid transcription errors
- 30% motivation: Focus on reasoning, not mechanical work
- 10% motivation: Faster completion
- Skeleton enables reasoning; example conditions might inhibit it

**Decision Log:**
- 2025-12-19: Skeleton-only design approved after agent introspection
- 2025-12-19: Example conditions explicitly excluded (may cause copy-paste behavior)

---

### P5: Explain Mode (Revised: Always-On Hints)

**Status:** Complete (v0.1.0)
**Priority:** P1 (Medium impact, Medium effort)
**Affects:** CLI, Agent understanding
**Dependencies:** P3 (RULE_META provides hint content)

**Problem:**
When Guard fails, agents mechanically fix violations without understanding WHY.
Original design had `--explain` as opt-in flag, but:
- Agents don't know the flag exists
- Agents won't think to use it
- Opt-in features are useless for agents

**Agent-Native Principle:**
- Automatic > Opt-in
- Default ON > Default OFF
- Integrated > Separate flag

**Revised Solution:**
Two-tier output system:

1. **Brief hint (ALWAYS shown)** - One actionable line with every violation
2. **Detailed explanation (--explain)** - Optional, adds examples and docs
3. **--agent mode** - Always includes full information automatically

**Tier 1: Brief Hints (Always On)**
```
WARNING src/core/calc.py:15 Function 'compute' has no @pre or @post contract
  → Ask: what inputs are invalid? what does output guarantee?
```

The hint is:
- Always displayed (no flag needed)
- Actionable guidance, not abstract philosophy
- Helps agent think in the right direction
- **Source: P3's RULE_META.hint field** (centralized, not duplicated)

**Hint Content:** Defined in P3's RULE_META. P5 handles display logic only.

See P3 for full hint definitions per rule.

**Tier 2: Detailed Explanation (--explain)**
```
WARNING src/core/calc.py:15 Function 'compute' has no @pre or @post contract
  → Ask: what inputs are invalid? what does output guarantee?

  EXAMPLES:
    @pre(lambda x: x > 0)                    # Positive numbers
    @post(lambda result: result is not None) # Non-null output

  DOCS: INVAR.md#contracts
```

**--agent Mode (Full Info Automatic)**
```json
{
  "rule": "missing_contract",
  "message": "Function 'compute' has no @pre or @post contract",
  "hint": "Ask: what inputs are invalid? what does output guarantee?",
  "explanation": {
    "examples": ["@pre(lambda x: x > 0)", "@post(lambda result: ...)"],
    "docs": "INVAR.md#contracts"
  },
  "fix": { ... }
}
```

**Implementation:**
1. `core/formatter.py`: Look up hint from P3's RULE_META when formatting
2. `core/formatter.py`: Display hint in output (always)
3. `core/explanations.py`: Detailed explanations for --explain (examples, docs)
4. `shell/cli.py`: Add --explain flag for tier 2

**Note:** P5 does NOT define hints - it uses P3's RULE_META.hint.
This ensures single source of truth for hint content.

**Estimated effort:** ~100 lines, 45 min (after P3)

**Decision Log:**
- 2025-12-19: Original opt-in design rejected (agents won't use it)
- 2025-12-19: Revised to always-on hints + optional detailed explanation
- 2025-12-19: --agent mode includes full info automatically
- 2025-12-19: Clarified hints come from P3 RULE_META (review fix)

---

### P6: Protocol Compression (Revised)

**Status:** Complete (v0.1.0)
**Priority:** P2 (Medium impact, Low effort)
**Affects:** INVAR.md, Session start
**Dependencies:** P5 (hints), P14 (inspection) - must implement first

**Problem:**
INVAR.md is 800+ lines, consuming significant context tokens.
Less tokens for protocol → more tokens for reasoning/code.

**Key Insight (from discussion):**
Compression is NOT about changing agent behavior (documentation doesn't change behavior).
Compression IS about optimizing token budget by removing redundant information.

Information is redundant if:
1. Enforced by Guard anyway (detailed rules → Guard catches violations)
2. Provided by P5 hints (explanations → hints explain just-in-time)
3. Provided by P14 inspection (patterns → shown automatically)

**What MUST stay in INVAR.md:**
- Core/Shell concept (must know BEFORE coding)
- That contracts are required (concept, not details)
- Size limits (numbers)
- **That tools exist** (Guard, hints, --explain, --changed, inspection)
- **ICIDV checklist** (brief, actionable)

**What can be removed:**
- ~~Detailed contract examples~~ → P4 templates, P5 hints
- ~~Rule explanations~~ → P5 --explain
- ~~Pattern examples~~ → P14 automatic inspection
- ~~Philosophy/rationale~~ → docs/PHILOSOPHY.md
- ~~Edge cases~~ → Guard catches them

**Target Structure (~80 lines):**

```markdown
# Invar Protocol v3.x

## Core/Shell Architecture
Core (src/*/core/): Pure functions, no I/O, requires @pre/@post
Shell (src/*/shell/): I/O operations, returns Result[T, E]
Forbidden in Core: os, sys, subprocess, pathlib, open, requests

## Contracts
Core functions must have @pre or @post. Guard enforces and provides hints.

## Size Limits
Files: 500 lines (warning at 80%)
Functions: 50 lines

## Guard Commands
invar guard              # Check rules, shows hints for violations
invar guard --changed    # Modified files only, shows inspection info
invar guard --explain    # Detailed explanations
invar guard --agent      # JSON output with full context
invar rules              # List all rules and severities

## Before Implementing (ICIDV)
□ Understand the task intent
□ Check existing patterns (shown by --changed)
□ Consider edge cases
□ Run guard after changes

## More Information
- Detailed docs: docs/DESIGN.md
- Philosophy: docs/PHILOSOPHY.md
```

**Implementation:**
1. Rewrite INVAR.md (~80 lines)
2. Move detailed content to docs/
3. Update templates/INVAR.md
4. Verify P5 hints cover removed explanations
5. Verify P14 inspection covers removed patterns

**Estimated effort:** 1-2 hours (after P5, P14 done)

**Why P5 and P14 must be done first:**
- P5 hints replace detailed rule explanations
- P14 inspection replaces pattern documentation
- Without these, compression loses important information

**Decision Log:**
- 2025-12-19: Original goal was behavior change → realized compression doesn't change behavior
- 2025-12-19: Reframed as token optimization, not behavior change
- 2025-12-19: Must tell agent that tools exist (bootstrapping problem)
- 2025-12-19: Depends on P5, P14 to avoid losing information

---

### P7: Semantic Contract Validation

**Status:** Proposed
**Priority:** P3 (Medium impact, High effort)
**Affects:** Contract checking

**Problem:**
Current `is_empty_contract()` only catches `lambda: True` and `lambda x: True`. But equally useless contracts pass:
- `lambda x: x == x` (always true)
- `lambda x: True or x > 0` (short-circuits)
- `lambda x: isinstance(x, object)` (everything is object)

**Solution:**
Expand tautology detection.

**Tautology Patterns:**
```python
TAUTOLOGIES = [
    # Identity comparisons
    "x == x", "x is x",
    # Short-circuit to True
    "True or *", "* or True",
    # Universal type checks
    "isinstance(x, object)",
    # Negation of contradiction
    "not False", "not (x != x)",
]
```

**Implementation:**
1. `core/contracts.py`: Extend `is_empty_contract()` with AST pattern matching
2. Check for: self-equality, `True or`, `isinstance(_, object)`
3. May need symbolic evaluation for complex cases

**Challenges:**
- False positives risk (legitimate `x == x` in rare cases?)
- Complex expressions hard to analyze

**Open Questions:**
- [ ] Use simple pattern matching or symbolic evaluation?
- [ ] Allowlist for false positives?

---

### P8: Size Warnings Before Limit

**Status:** Complete (v0.1.0)
**Priority:** P1 (Medium impact, Low effort)
**Affects:** Guard output

**Problem:**
Agent adds 20 lines, runs Guard, fails at 302 lines (now 502 with P1), must refactor.
No warning before hitting limit - discovery is reactive, not proactive.

**Solution:**
Warning at configurable threshold (default 80%) for FILES only.

```
WARNING src/core/contracts.py File has 410 lines (82% of 500 limit)
```

**Config:**
```toml
[tool.invar.guard]
max_file_lines = 500           # P1: raised from 300
size_warning_threshold = 0.8   # P8: warn at 80% (400 lines)
```

**Design Decisions:**
1. **File-level only** - Function-level deferred to Phase 10
   - File splits are major decisions worth early warning
   - Function refactors are minor, can handle when exceeded
2. **Configurable threshold** - Default 0.8, set to 0 to disable
3. **New rule name** - `file_size_warning` (separate from `file_size`)
   - Allows independent severity control via P2

**Implementation:**
```python
# core/rules.py - add to check_file_size()
elif config.size_warning_threshold > 0:
    threshold_lines = int(config.max_file_lines * config.size_warning_threshold)
    if file_info.lines >= threshold_lines:
        pct = int(file_info.lines / config.max_file_lines * 100)
        violations.append(Violation(
            rule="file_size_warning",
            severity=Severity.WARNING,
            file=file_info.path,
            line=None,
            message=f"File has {file_info.lines} lines ({pct}% of {config.max_file_lines} limit)",
            suggestion="Consider splitting before reaching limit",
        ))
```

**Implementation Steps:**
1. `core/models.py`: Add `size_warning_threshold: float = 0.8` to RuleConfig
2. `core/rules.py`: Add warning logic to `check_file_size()`
3. `shell/config.py`: Parse threshold from config
4. Tests + docs

**Estimated effort:** ~50 lines, 30 minutes

**Deferred to Phase 10:**
- Function-level size warnings
- Integration with `invar map` output

**Decision Log:**
- 2025-12-19: Approved with file-level only (function-level deferred)
- 2025-12-19: Threshold configurable, default 0.8

---

### P9: Context Sync Command

**Status:** Proposed
**Priority:** P3 (Low impact, Low effort)
**Affects:** CLI, Workflow

**Problem:**
Manually updating `.invar/context.md` after each phase is tedious. Easy to forget, leading to stale context.

**Solution:**
Semi-automated context management commands.

```bash
invar context log "Phase 8 complete"     # Adds timestamped entry
invar context show                        # Shows current state
invar context set phase 9                 # Updates phase field
```

**context.md format:**
```markdown
## Current State
- Phase: 9
- Blockers: None

## Log
- 2025-12-19 14:30: Phase 8 complete
- 2025-12-18 10:00: Phase 7 complete
```

**Implementation:**
1. `shell/context.py`: Context file manipulation
2. CLI subcommands: `invar context [log|show|set]`
3. Parse and update markdown structure

**Open Questions:**
- [ ] Structured format (YAML front matter) vs pure markdown?
- [ ] Integration with git commits?

---

### P11: Agent Mode Auto-Detection

**Status:** Complete (v0.1.0)
**Priority:** P0 (High impact, Low effort)
**Affects:** CLI, Environment

**Problem:**
Agent must know to use `--agent` flag to get JSON output. But:
- Agent doesn't know this flag exists
- Agent might parse human-readable output (fragile)
- Every agent invocation requires remembering the flag

**Agent-Native Principle:**
Automatic > Opt-in. The tool should detect it's being used by an agent.

**Solution:**
Environment variable auto-detection for agent mode.

```bash
# Set once in agent environment
export INVAR_MODE=agent

# All subsequent commands auto-use agent output
invar guard  # Outputs JSON with full explanation
```

**Detection Logic:**
```python
def _detect_agent_mode() -> bool:
    """Auto-detect if running in agent context."""
    return any([
        os.getenv("INVAR_MODE") == "agent",
        os.getenv("CLAUDE_CODE") == "1",      # Claude Code
        os.getenv("CI") == "true" and not sys.stdout.isatty(),  # CI pipeline
    ])
```

**Behavior When Detected:**
- Output format: JSON (same as --agent)
- Include hints and explanations automatically
- Include fix instructions

**Affected Commands (ALL):**

| Command | Human Mode | Agent Mode (INVAR_MODE=agent) |
|---------|------------|-------------------------------|
| `invar guard` | Rich text | JSON with rule_meta, hints, fixes |
| `invar rules` | Table | JSON array of RuleMeta |
| `invar map` | Table | JSON with symbols and refs |
| `invar sig` | Text | JSON with signatures |

**All CLI commands respect INVAR_MODE for output format.**

**Implementation:**
1. `shell/cli.py`: Add `_detect_agent_mode()` function
2. `shell/cli.py`: Apply to ALL commands (guard, rules, map, sig)
3. `core/formatter.py`: JSON formatters for each command
4. Documentation: Update CLAUDE.md to mention INVAR_MODE

**Estimated effort:** ~50 lines, 30 minutes

**Backward Compatibility:**
- No environment variable = human mode (unchanged)
- `--agent` flag still works (explicit override)
- `--json` flag still works (explicit override)

**Decision Log:**
- 2025-12-19: Added based on CLI review from agent-native perspective
- 2025-12-19: Extended to ALL commands, not just guard (review fix)

---

### P12: strict_pure Default ON

**Status:** Complete (v0.1.0)
**Priority:** P0 (High impact, Low effort)
**Affects:** Guard defaults

**Problem:**
`--strict-pure` enables valuable purity checks but is off by default:
- `internal_import`: Imports inside functions (should be at top)
- `impure_call`: Calls to datetime.now(), random.*, print(), etc.

Why would an agent NOT want these checks? More checking = better.

**Agent-Native Principle:**
Default ON > Default OFF. Agents benefit from maximum verification.

**Solution:**
Make `strict_pure` default to True.

**Before:**
```bash
invar guard              # No purity checks
invar guard --strict-pure  # With purity checks
```

**After:**
```bash
invar guard              # With purity checks (default)
invar guard --no-strict-pure  # Disable if needed
```

**Config Override:**
```toml
[tool.invar.guard]
strict_pure = false  # Opt-out if needed
```

**Or use P2 severity config for fine-grained control:**
```toml
[tool.invar.guard]
severity_overrides = { internal_import = "off", impure_call = "off" }
```

**Implementation:**
1. `core/models.py`: Change `strict_pure: bool = False` → `strict_pure: bool = True`
2. `shell/cli.py`: Change flag to `--no-strict-pure` (opt-out instead of opt-in)
3. Update documentation

**Estimated effort:** ~10 lines, 10 minutes

**Decision Log:**
- 2025-12-19: Added based on CLI review - more checking is better for agents

---

### P14: Automatic Inspection

**Status:** Complete (v0.1.0)
**Priority:** P1 (High impact, Medium effort)
**Affects:** Guard --changed output, ICIDV enforcement

**Background:**
ICIDV (Intent-Contract-Inspect-Design-Verify) is documented but not followed because:
- It's not enforced
- It requires voluntary action
- Agent optimizes for task completion, skips "optional" steps

The "Inspect" step is particularly valuable but skipped:
- Check similar functions before writing new ones
- Follow existing patterns
- Understand file context

**Problem:**
Agent modifies Core file without looking at existing patterns → writes inconsistent code.

**Solution:**
Make Inspection automatic. When running `invar guard --changed`, automatically show:
1. Similar functions in the file
2. Common contract patterns
3. File status (size, structure)

**Unified Output Format (integrates P3, P5, P14):**

```
$ invar guard --changed

Checking 2 modified files...

┌─ Context ────────────────────────────────────────────────────┐
│ Rules: file_size, function_size, missing_contract,          │  ← P3
│        empty_contract, param_mismatch, forbidden_import     │
│ Mode: strict-pure, changed-only                             │
│ Limits: 500 lines/file, 50 lines/function                   │
└──────────────────────────────────────────────────────────────┘

── src/core/calc.py (Core) ────────────────────────────────────
INSPECT:                                                        ← P14
  Similar: compute() [L45], process() [L89]
  Pattern: @pre(lambda x, y: x > 0 and y > 0)
  Status: 245/500 lines (49%), 8 functions

VIOLATIONS:
  WARNING :120 missing_contract
    Function 'new_func' has no @pre or @post contract
    → Ask: what inputs are invalid? what does output guarantee?  ← P5 hint
    → Add: @pre(lambda a, b: <condition>)                        ← P4 skeleton
    → Similar: compute() uses @pre(lambda x, y: x > 0 and y > 0) ← P14

── src/core/parser.py (Core) ──────────────────────────────────
INSPECT:
  Similar: parse_source() [L12], parse_symbol() [L67]
  Pattern: @pre(lambda source: isinstance(source, str))
  Status: 180/500 lines (36%), 5 functions

  ✓ No violations

────────────────────────────────────────────────────────────────
Files: 2 checked | Errors: 0 | Warnings: 1
Note: Static analysis only. Runtime behavior not checked.
```

**Key Design Decisions:**

1. **Only in --changed mode** - Full project scan doesn't need inspection
2. **Only for Core files** - Shell files don't have contract patterns to follow
3. **Integrated with P3, P5** - Context shows rules, hints in violations
4. **Non-blocking** - Information is shown, not enforced as gate
5. **Unified format** - P3 (rules), P14 (inspect), P5 (hints), P4 (skeleton) all integrated

**What P14 detects:**

| Detection | Method |
|-----------|--------|
| Similar functions | Name similarity (Levenshtein), same file |
| Contract patterns | Most common @pre/@post structure in file |
| File status | Line count, function count |

**Implementation:**

```python
# core/inspection.py (NEW)

@pre(lambda file_info: isinstance(file_info, FileInfo))
def get_inspection_info(file_info: FileInfo) -> InspectionInfo:
    """Extract inspection information for a file."""
    return InspectionInfo(
        similar_functions=_find_similar_functions(file_info),
        contract_pattern=_extract_common_pattern(file_info),
        file_status=_get_file_status(file_info),
    )

def _find_similar_functions(file_info: FileInfo) -> list[tuple[str, int]]:
    """Find functions with similar purposes (by name patterns)."""
    # Group by prefix: get_*, check_*, parse_*, etc.
    ...

def _extract_common_pattern(file_info: FileInfo) -> str | None:
    """Extract the most common contract pattern."""
    # Analyze existing @pre/@post, find common structure
    ...
```

```python
# core/models.py

class InspectionInfo(BaseModel):
    similar_functions: list[tuple[str, int]]  # (name, line)
    contract_pattern: str | None
    line_count: int
    function_count: int
```

**Integration Points:**

1. `shell/cli.py`: In --changed mode, call inspection before showing violations
2. `core/formatter.py`: Format inspection info for output
3. `core/suggestions.py`: Include "Similar:" in hints when available

**Estimated effort:** ~190 lines, 2-3 hours

**Relationship to ICIDV:**

| ICIDV Step | Before P14 | After P14 |
|------------|------------|-----------|
| Intent | Can't enforce | Can't enforce |
| Contract | Guard enforces | Guard enforces |
| Inspect | Documented, skipped | **Automatic** |
| Design | Can't enforce | Can't enforce |
| Verify | Guard is part of V | Guard is part of V |

**Decision Log:**
- 2025-12-19: Created to address ICIDV Inspect step being skipped
- 2025-12-19: Automatic > Opt-in principle applied

---

### P13: Mechanical vs Reasoning Work Audit (NEW)

**Status:** Proposed (Future)
**Priority:** P2 (High impact, Medium effort)
**Affects:** All Invar tools

**Background:**
During P4 discussion, agent introspection revealed a fundamental principle:

| Work Type | Who Should Do | Example |
|-----------|---------------|---------|
| Mechanical (deterministic) | Tool | Transcribing param names |
| Reasoning (semantic) | Agent | Deciding contract conditions |

**Problem:**
Invar may have other places where agents do mechanical work that tools could automate.
This creates:
- Unnecessary error opportunities
- Cognitive distraction from reasoning
- Inefficient use of agent capabilities

**Proposal:**
Systematic audit of all Invar interactions to identify:
1. Where agents currently do mechanical work
2. What could be automated
3. What should remain as reasoning tasks

**Audit Areas:**
- [ ] Guard output → Are there mechanical fix steps?
- [ ] `invar init` → Is setup fully automated?
- [ ] `invar map/sig` → Is output optimized for agent consumption?
- [ ] Error messages → Do they require mechanical interpretation?
- [ ] Config files → Is there boilerplate that could be generated?
- [ ] INVAR.md → Are there rules that could be auto-enforced?

**Guiding Principle:**
> "Agent time is for reasoning. Tool time is for mechanics."

**Output:**
List of specific improvements, each classified as:
- Quick win (< 30 min implementation)
- Medium effort (1-2 hours)
- Major feature (needs design)

**Decision Log:**
- 2025-12-19: Proposal created based on P4 introspection discussion
- To be scheduled after Phase 9 implementation

---

### P10: Contract Inheritance Validation

**Status:** Proposed
**Priority:** P4 (Low impact, High effort)
**Affects:** Class/method checking

**Problem:**
When a derived class overrides a method, contract compatibility (Liskov Substitution) is not checked.

```python
class Base:
    @pre(lambda x: x > 0)  # Accepts positive
    def process(self, x: int) -> int: ...

class Derived(Base):
    @pre(lambda x: x > 10)  # ERROR: Strengthens precondition!
    def process(self, x: int) -> int: ...
```

**Liskov Rules:**
- Derived @pre must be **equal or weaker** (accept same or more)
- Derived @post must be **equal or stronger** (guarantee same or more)

**Implementation:**
1. `core/parser.py`: Track class hierarchy during parsing
2. `core/inheritance.py`: Compare contracts between base and derived
3. New rule: `liskov_violation`

**Challenges:**
- Requires cross-file analysis (base class may be in different file)
- Contract comparison is semantically complex
- Multiple inheritance complications

**Open Questions:**
- [ ] Handle contracts from external libraries?
- [ ] Warning or error severity?

---

## Priority Matrix

| Priority | Proposals | Status |
|----------|-----------|--------|
| P0 | P1, P2, P11, P12 | Complete (v0.1.0) |
| P1 | P3, P5, P8, P14 | Complete (v0.1.0) |
| P2 | P4, P6 | Complete (v0.1.0) |
| P3 | P7, P9, P13 | Future (Phase 10) |
| P4 | P10 | Future (Phase 10) |

**Key Decisions:**
- P1: ~~Inline suppression~~ → Config-level exclusions + `max_file_lines` 500
- P3: ~~Generate Section 7~~ → RULE_META + auto-embed in output (agent won't read docs)
- P4: Lambda skeleton only (no example conditions)
- P5: Always-on hints (automatic > opt-in), uses P3 RULE_META.hint
- P6: Token optimization, depends on P3 + P5 + P14
- P11: INVAR_MODE env var for agent auto-detection
- P12: `strict_pure` default ON (more checking = better)
- P14: Automatic inspection in --changed (ICIDV Inspect step)

---

## Implementation Phases

### Phase 9.1: Friction Reduction + Agent-Native Defaults (Complete)
- [x] P1: Relaxed limits (500 lines) + config-level exclusions
- [x] P2: Severity configuration + `redundant_type_contract` OFF + `--pedantic`
- [x] P8: File size warnings at 80%
- [x] P11: INVAR_MODE env var for agent auto-detection
- [x] P12: `strict_pure` default ON

### Phase 9.2: Agent Experience + ICIDV + Rule Metadata (Complete)
- [x] P3: RULE_META system + auto-embed in output + `invar rules` command
- [x] P5: Always-on hints + optional --explain
- [x] P4: Lambda skeleton templates
- [x] P14: Automatic inspection in --changed mode

### Phase 9.3: Token Optimization (Complete)
- [x] P6: Protocol compression (88 lines)

### Phase 10: Advanced (Future)
- [ ] P7: Semantic contract validation
- [ ] P13: Mechanical vs Reasoning work audit
- [ ] P8b: Function-level size warnings
- [ ] P9: Context sync command
- [ ] P10: Contract inheritance validation

---

## Discussion Log

*Record decisions and changes here*

- 2025-12-19: **Pre-Implementation Review** - Conflict resolution
  - P2/P3 overlap: `invar rules` moved from P2 to P3 (unified implementation)
  - P5 clarified: hints come from P3's RULE_META.hint (single source of truth)
  - P11 extended: affects ALL commands (guard, rules, map, sig), not just guard
  - P14 updated: unified --changed output format integrating P3, P4, P5, P14
  - New principle: "Single source of truth for rule metadata"
- 2025-12-19: **P3 Revised** - Rule Metadata System
  - Original: Generate Section 7 markdown documentation
  - Problem: Agent won't proactively read docs or run `invar rules`
  - Solution: RULE_META centralized definition + auto-embed in guard output
  - --agent mode: includes full rule_meta per violation
  - --changed mode: shows "Rules Applied" section
  - `invar rules` command: fallback for explicit queries (auto-JSON in INVAR_MODE=agent)
  - Section 7: moves to docs/LIMITATIONS.md (generated, for humans only)
  - Priority upgraded: P3→P1 (enables P5 hints, P6 compression)
  - New principle: "Don't force agent to read - show them automatically"
- 2025-12-19: **P14 Created & P6 Revised** - ICIDV enforcement and protocol compression
  - P14: Automatic Inspection in --changed mode (enforces ICIDV Inspect step)
  - Shows: similar functions, contract patterns, file status
  - Key insight: Documentation doesn't change behavior, only automatic enforcement does
  - P6: Reframed as token optimization, not behavior change
  - P6 now depends on P5 (hints replace explanations) and P14 (inspection replaces patterns)
  - Target: INVAR.md ~80 lines (down from 800+)
- 2025-12-19: **P4 Approved & P13 Created** - Agent introspection on mechanical vs reasoning work
  - P4: Lambda skeleton only, NO example conditions
  - Agent motivation: 60% error avoidance, 30% focus on reasoning, 10% speed
  - Example conditions excluded: might inhibit reasoning, encourage copy-paste
  - P13: Future systematic audit of all Invar mechanical work
  - New principle: "Agent time is for reasoning. Tool time is for mechanics."
- 2025-12-19: **P11 & P12 Added** - CLI review from agent-native perspective
  - P11: INVAR_MODE env var for auto-detecting agent context
  - P12: `strict_pure` default ON (more checking = better for agents)
  - Principle: Automatic > Opt-in, Default ON > Default OFF
- 2025-12-19: **P5 Revised & Approved** - Explain mode with always-on hints
  - Original opt-in design rejected: agents won't use flags they don't know about
  - Agent-Native Principle: Automatic > Opt-in, Default ON > Default OFF
  - Solution: Brief hints always shown, --explain adds details, --agent includes all
- 2025-12-19: **P8 Approved** - Size warnings before limit
  - File-level only (function-level deferred to Phase 10)
  - Configurable threshold, default 0.8 (80%)
  - New rule `file_size_warning` for independent severity control
- 2025-12-19: **P2 Approved** - Severity configuration with new defaults
  - Root cause: Forcing contracts → agents write trivial isinstance() checks
  - Decision: This is expected behavior, not misbehavior
  - `redundant_type_contract` default OFF (was INFO)
  - Added `--pedantic` flag and `invar rules` command
- 2025-12-19: **P1 Revised** - Original inline suppression rejected as too complex for agents
  - Problem: Per-function suppression enables "formal compliance without substance"
  - Solution: Relaxed limits (500 lines) + config-level exclusions + minimal file-level skip
  - Function limit stays at 50 (forces good design)
- 2025-12-19: Initial proposals created based on Phase 8 implementation experience

