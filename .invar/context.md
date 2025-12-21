# Invar Project Context

*Last updated: 2025-12-21*

## Current State

- **PyPI:** `python-invar` v0.4.1
- **Protocol:** v3.23 (Three-Level Verification, Agent-Native JSON, research-validated)
- **GitHub Pages:** https://tefx.github.io/Invar/
- **Status:** Feature complete, research foundation documented
- **Blockers:** None

## Documentation Structure (DX-11)

| File | Owner | Edit? |
|------|-------|-------|
| INVAR.md | **Source** | Yes (this IS the source) |
| CLAUDE.md | User | Yes |
| .invar/context.md | User | Yes (this file) |
| .invar/examples/ | Sync | `invar update --force` |

**Note:** This is the Invar project. INVAR.md is the **source**, not a copy.
- Do NOT use `invar update` on INVAR.md here!
- Examples can be synced with `invar update --force`

**Decision rule:** Is this Invar protocol or project-specific?
- Protocol content → Already in INVAR.md, don't duplicate
- Project-specific → Add to CLAUDE.md or here

---

## Session 2025-12-21 Evening: DX-11 & Enforcement Reflection

### Completed Work

| Item | Description | Commits |
|------|-------------|---------|
| DX-11 Implementation | Multi-agent documentation restructure | 59bbe87 |
| `invar update` command | Self-update managed files (INVAR.md, examples/) | 4c7a28e |
| Workflow compliance fix | `detect_agent_configs` returns `Result[T, E]` | 1539a63 |
| Enforcement attempt | PreToolUse hooks → removed after reflection | 0fc318e → 6ee06b3 |

### DX-11: Multi-Agent Support

Implemented documentation restructure for multiple AI agents:

```
.claude/
├── commands/          # Slash commands (review, attack)
└── settings.local.json  # Personal permissions (not committed)

Templates added:
├── AGENT_CONFIGS      # Claude, Cursor, Aider detection
├── detect_agent_configs()  # Status: configured/found/not_found
├── add_invar_reference()   # Safe config modification
└── copy_examples_directory()  # Reference examples
```

Pre-commit protection:
```yaml
- id: invar-md-protected
  entry: bash -c 'if git diff --cached --name-only | grep -q "^INVAR.md$"; then echo "Warning..."; exit 1; fi'
```

### `invar update` Command

New command to update Invar-managed files:

```bash
invar update           # Update if newer version available
invar update --check   # Check without applying
invar update --force   # Update even if same version
```

Safely updates:
- ✅ INVAR.md (overwrites)
- ✅ .invar/examples/ (replaces)

Never touches:
- ❌ CLAUDE.md (user-managed)
- ❌ .invar/context.md (user-managed)
- ❌ pyproject.toml [tool.invar] (user config)

### Key Insight: Enforcement Timing

**Attempted:** PreToolUse hook to warn when `Read` used on `.py` files

**Result:** Removed after reflection. Ineffective because:

```
Decision timeline:
1. Agent decides to use Read     ← Decision made HERE
2. Agent calls Read tool
3. Hook triggers                 ← Warning comes HERE (too late!)
4. Agent clicks "confirm"        ← Just bypasses
```

**Effective enforcement points:**

| Point | Mechanism | Strength |
|-------|-----------|----------|
| Before work starts | Session context (claude-mem) | Soft guide |
| During decisions | CLAUDE.md tool table | Reference |
| Before commit | Pre-commit hook | **Hard block** |
| After action | PreToolUse hook | ❌ Too late |

**Lesson #19:** 干预时机决定效果。提交前阻止 = 有效。操作后提醒 = 噪音。

### Workflow Compliance Issue Found

During ICIDIV review, found `detect_agent_configs` didn't return `Result[T, E]`:

```python
# Before (violated Shell convention)
def detect_agent_configs(path: Path) -> dict[str, str]:

# After (compliant)
def detect_agent_configs(path: Path) -> Result[dict[str, str], str]:
```

Also fixed: `init_cmd.py` to properly unwrap the Result.

### Self-Reflection: Tool Usage

During this session, I:
- ❌ Didn't use `invar sig` before reading files
- ❌ Used `Read` instead of Serena `find_symbol`
- ❌ Ran `python3 -m doctest` directly instead of `invar guard`

**Root cause:** Habit over methodology. Tools exist but weren't used.

**Fix approach:** Not more hooks (wrong timing), but better session-start context.

---

## v3.23 Changes (2025-12-21)

### Three-Level Verification System

Simplified from 4 levels to 3 (removed unimplemented THOROUGH):

| Level | Flag | Content | Use When |
|-------|------|---------|----------|
| STATIC | `--quick` | Rules only | Debugging static analysis |
| STANDARD | (default) | Rules + doctests | Normal development |
| PROVE | `--prove` | Rules + doctests + CrossHair | Contract changes, releases |

### Agent JSON Output Enhancement

Agent JSON now includes `"verification_level"` for transparency:
```json
{
  "status": "passed",
  "verification_level": "standard",
  "doctest": {"passed": true}
}
```

### DX Proposals Completed

| Proposal | Description |
|----------|-------------|
| DX-01 ✅ | Lambda fix templates for param_mismatch errors |
| DX-02 ✅ | Doctest best practices documentation |
| DX-03 ✅ | exclude_doctest_lines configuration |
| DX-05 ✅ | Contract templates library (NonEmpty, Sorted, InRange...) |
| DX-06 ✅ | Smart Guard (static + doctests by default) |
| DX-07 ✅ | Integration tests for CLI flags |
| DX-09 ✅ | Self-violation prevention (verification_level in JSON) |
| DX-11 ✅ | Documentation restructure for multi-agent support |
| DX-12 ✅ | Hypothesis as CrossHair fallback (898b357) |

**DX-12 Implementation (2025-12-21):**
- `src/invar/core/hypothesis_strategies.py`: Type→strategy, timeout inference, @pre extraction
- `src/invar/shell/prove.py`: CrossHair + Hypothesis fallback logic
- CrossHair runs first (5s for numpy, 10s for pure Python)
- On skip/timeout, Hypothesis auto-triggers with inferred strategies

### Key Insight: Self-Violation Prevention

During development, the agent designed "zero-decision" tools but used `--quick` habitually. This violated Agent-Native principles. Fix: Make verification level visible in output, explicit guidance in CLAUDE.md.

## Recent Changes (v0.3.0)

### Breaking Changes
| Rule | Before | After |
|------|--------|-------|
| `missing_contract` | WARNING | **ERROR** |
| `impure_call` | WARNING | **ERROR** |
| `empty_contract` | WARNING | **ERROR** |

### New Features
- **Code Health Display** - Percentage + progress bar in Guard output
- **Warning Policy** - "You touched it, you own it" in CLAUDE.md
- **Tool Selection Guide** - Task-based with Serena fallbacks
- **Technical Debt Section** - In context.md template
- **GitHub Pages** - Project landing page

## Recent Changes (Development - Ultrathink Proposals)

### TTY Auto-Detection (Immediate) ✅
- All commands now auto-detect agent mode based on TTY status
- Pipe/redirect → JSON output, Terminal → human-readable
- `--agent`/`--json` flags are now optional
- File changed: `src/invar/shell/cli.py`

### A1/A2: Test & Verify Commands ✅
- `invar test <file>` - Run doctests + Hypothesis property tests
- `invar verify <file>` - Symbolic verification via CrossHair
- Files added: `src/invar/shell/testing.py`, `src/invar/shell/init_cmd.py`
- Extracted init command to separate module to manage file size

### C2: @must_use Decorator ✅
- `@must_use("reason")` marks functions whose return values must be used
- Guard rule `must_use_ignored` warns when return value is discarded
- Files added: `src/invar/decorators.py`, `src/invar/core/must_use.py`
- Export: `from invar import must_use`

### B4: Multi-Layer Purity Detection ✅
- Heuristic analysis: name patterns, signature, docstring keywords
- User configuration: `purity_pure` and `purity_impure` in config
- Files added: `src/invar/core/purity_heuristics.py`
- Files modified: `src/invar/core/purity.py`, `src/invar/core/models.py`, `src/invar/core/utils.py`

### C1: @invariant Decorator ✅
- `invariant(condition, message)` for loop invariants, inspired by Dafny
- Runtime checking with `INVAR_CHECK=1` (default ON), `INVAR_CHECK=0` disables
- Raises `InvariantViolation` on failure
- File added: `src/invar/invariant.py`
- Export: `from invar import invariant, InvariantViolation`

### C3: Contract Composition ✅
- `Contract` class with `&`, `|`, `~` operators for composing predicates
- `pre()` and `post()` decorators accepting Contract objects (works with deal)
- Standard library: NonEmpty, Sorted, Unique, Positive, NonNegative, Percentage, etc.
- File added: `src/invar/contracts.py`
- Export: `from invar import Contract, pre, post, NonEmpty, Sorted, ...`

### C4: Strategy Inference ✅
- `infer_from_lambda()` parses @pre lambda source to extract Hypothesis strategy constraints
- Pattern matching for: numeric comparisons (`x > 5`), ranges (`0 < x < 100`), length constraints (`len(x) > 0`)
- `StrategyHint` dataclass with constraints dict compatible with Hypothesis
- File added: `src/invar/core/strategies.py`
- Programmatic API for building custom test harnesses

### C5: @must_close Decorator ✅
- `@must_close` marks classes requiring explicit cleanup (inspired by Move language)
- Automatically adds context manager protocol (`__enter__`, `__exit__`)
- `is_must_close(obj)` for checking if resource needs cleanup
- File added: `src/invar/resource.py`
- Export: `from invar import must_close, is_must_close, MustCloseViolation`

### DX-06: Smart Guard ✅
- `invar guard` now automatically runs doctests after static analysis passes
- Zero decisions needed - Agent-Native design principle
- Three levels: STATIC (`--quick`) → STANDARD (default) → PROVE (`--prove`)
- Agent JSON includes `verification_level` for transparency
- Files modified: `src/invar/shell/cli.py`, `src/invar/shell/testing.py`, `pyproject.toml`
- Protocol updated to v3.23

### Development Experience Observation
**Issue**: `cli.py` at 474 lines (94% limit) after extracting init
**Solution**: Modular command structure - new commands in separate modules, cli.py imports and registers them

## Development Experience Findings (2025-12-21)

### What Worked Well

1. **ICIDIV Natural Flow** - Intent→Contract→Inspect→Design→Implement→Verify was naturally followed
2. **Guard as Feedback Loop** - Caught 5 errors immediately (missing contracts, param mismatches)
3. **Doctest-First Development** - Writing tests before code caught edge cases early
4. **Core/Shell Separation Clarity** - Easy to decide where new modules belong
5. **Warning Policy Effectiveness** - "You touched it, you own it" prevented debt accumulation

### Pain Points Identified

| Issue | Frequency | Impact | Proposal |
|-------|-----------|--------|----------|
| @pre lambda param count errors | 3x | Medium | DX-01 |
| Dict ordering in doctests | 2x | Low | DX-02 |
| `exclude_doctest_lines` undiscoverable | 1x | Low | DX-03 |
| Function size limit vs comprehensive doctests | 3x | Medium | DX-03 |
| `invar test`/`verify` not adopted | Critical | High | DX-06 |

### Specific Friction: @pre Lambda Parameters

Every function with default parameters triggered this error:
```python
@pre(lambda x, y: ...)  # 2 params
def func(x, y, z=None):  # 3 params → ERROR
```

**Required fix pattern** (non-obvious):
```python
@pre(lambda x, y, z=None: ...)  # Must include defaults
```

### Critical Finding: Tool Adoption Failure

`invar test` and `invar verify` (A1/A2) were implemented but never used during the session:

| Command | Runs |
|---------|------|
| `invar guard` | ~15 |
| `pytest --doctest-modules` | ~5 |
| `invar test` | 0 |
| `invar verify` | 0 |

**Lesson:** New tools must integrate into primary workflow (`invar guard`) to achieve adoption. Separate commands create friction.

### Quantitative Summary

| Metric | Value |
|--------|-------|
| Features implemented | 9 |
| Guard runs | ~15 |
| Errors caught by Guard | 5 |
| Zero-issue first attempts | 4/9 (44%) |
| Time on contract fixes | ~10% |
| New command adoption | 0% (DX-06) |

### CRUXEval Quick Validation (2025-12-21)

Completed self-experiment validating contracts improve code understanding.
See `docs/research/cruxeval-quick-validation.md`.

**Key insight:** Contracts don't make you "guess right" — they make you "know you're right."

### Recommendations Generated

See `docs/proposals/2025-12-21-dx-improvements.md` for detailed proposals:
- **DX-01**: Improve @pre lambda error messages with fix templates
- **DX-02**: Document dict comparison patterns for doctests
- **DX-03**: Document `exclude_doctest_lines` config option
- **DX-04**: Add `invar fix --auto` for common issues
- **DX-06**: Smart Guard (Agent-Native) ✅ **Implemented**
  - `invar guard` auto-runs doctests (no flags needed)
  - Context auto-detection (CI/pre-commit/local) determines depth
  - Agent runs one command, zero decisions

## Core Principle

> **"Agent-Native Execution, Human-Directed Purpose"**

```
Human (Commander) ──directs──→ Agent (Executor) ──uses──→ Invar (Protocol + Tools)
```

## Implementation Summary

| Phase | Status | Key Features |
|-------|--------|--------------|
| 1-8 | Complete | Guard, Perception (map/sig), Agent-Native defaults |
| 9 | Complete | PyPI release, RULE_META, Protocol compression |
| 10 | Complete | Tautology detection (P7), Import alternatives (P17) |
| 11 | Complete | Coverage stats (P24), Extraction analysis (P25), Pattern alternatives (P27), Partial contract detection (P28) |
| 12 | Complete | Stricter enforcement, Code Health, GitHub Pages |

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0 | 2025-12 | Initial PyPI release |
| 0.2.0 | 2025-12 | README rewrite, pre-commit hooks |
| 0.2.1 | 2025-12 | Hooks default ON |
| 0.2.2 | 2025-12 | Auto-install hooks, universal venv support |
| 0.3.0 | 2025-12 | Stricter enforcement, Code Health, GitHub Pages |
| 0.3.1 | 2025-12 | Smart Guard, Ruff pre-commit, CI fixes |
| 0.4.0 | 2025-12 | ICIDIV workflow, README rewrite, Four Laws, GitHub Pages refresh |
| 0.4.1 | 2025-12 | GitHub Pages fix, PyPI trusted publisher |
| 0.5.0 | 2025-12 | Six Laws (research-validated), enhanced ICIDIV, foundational influences |

## Tool Priority

| Task | Primary | Fallback |
|------|---------|----------|
| See contracts | `invar sig` | — |
| Find entry points | `invar map --top` | — |
| Find specific symbol | Serena `find_symbol` | `invar map` + grep |
| Find references | Serena `find_referencing_symbols` | `invar map` |
| Edit function | Serena `replace_symbol_body` | Standard edit |
| Verify | `invar guard` | Smart Guard (static + doctests) |

## Key Files

| File | Purpose |
|------|---------|
| INVAR.md | Protocol v3.23 |
| docs/INVAR-GUIDE.md | Why & How |
| docs/VISION.md | Design philosophy |
| CLAUDE.md | Development guide |
| docs/index.html | GitHub Pages |

## Lessons Learned

1. **Agent-Native ≠ Agent-Only** - Design for Agent, measure by Human success
2. **Automatic > Opt-in** - Agents won't use flags they don't know about
3. **Guard/Agent Boundary** - Guard does mechanical analysis, Agent does reasoning
4. **Facts Only** - Report facts, don't judge "strength" or "quality"
5. **Stricter is Better** - Enforce architecture at commit time, not review time
6. **Tool Complementarity** - Invar for contracts/verification, Serena for navigation/editing
7. **Meta-changes Need Meta-verification** - Rule severity changes need full guard, not --changed
8. **Research Validates Practice** - 6 papers validate Invar's core approach (test-first, contracts, decomposition)
9. **Contract Completeness** - A good contract uniquely determines implementation (Clover)
10. **Reflective Verification** - Understand WHY before fixing (Reflexion)
11. **Zero-Decision Tools** - Agent-Native means no flag selection; tool auto-detects context (DX-06)
12. **Flag 存在 ≠ 功能存在** - Each flag path needs independent verification; adding a flag without wiring up execution creates silent failures
13. **Contract 必须具体到可验证** - "Add X" is insufficient; need "@post: output contains Y" level specificity
14. **局部正确性 ≠ 全局正确性** - Function-level contracts don't guarantee feature-level completeness; integration paths need explicit verification
15. **验证的验证** - Verification tools themselves need verification; who verifies the verifier?
16. **Don't Promise Unimplemented** - THOROUGH level was removed because it promised Hypothesis but never ran it (DX-09)
17. **Agent Transparency** - Agent JSON output must include context (verification_level) for Agent to reason about
18. **Dogfooding Catches Self-Violation** - Using --quick habitually while designing "zero-decision" tools exposes habit vs design gap
19. **Enforcement Timing Matters** - Pre-commit blocks are effective; PreToolUse hooks are noise (decision already made)
20. **Tools Exist ≠ Tools Used** - Having the right tools means nothing if habit overrides methodology

## Release Process

**Do NOT use `twine upload` manually.** GitHub Actions handles PyPI publishing.

```bash
# 1. Update version in pyproject.toml
# 2. Commit and push
git add -A && git commit -m "Bump version to X.Y.Z" && git push

# 3. Create release (triggers automatic PyPI publish)
gh release create vX.Y.Z --title "vX.Y.Z - Title" --notes "..."
```

## Technical Debt

*Run `invar guard` to check current status.*

| File | Warning | Priority |
|------|---------|----------|
| cli.py | 495 lines (99%), 4 functions > 50 lines | Low |
| contracts.py | 492 lines (98%) | Low |
| rules.py | 430 lines (86%) | Low |

---

*Update this file when: completing phases, making design decisions, releasing versions.*
