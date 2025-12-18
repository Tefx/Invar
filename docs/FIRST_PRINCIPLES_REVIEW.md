# First-Principles Review: Invar Framework v3.9

*Review Date: 2024-12-19*

---

## 1. Core Premise Analysis

### The Fundamental Claim

> "Separate what CAN fail (I/O) from what SHOULD NOT fail (logic)"

**Verdict: SOUND but needs refinement**

This aligns with established patterns:
- Functional programming's pure/impure distinction
- Hexagonal architecture's ports and adapters
- "Functional core, imperative shell" pattern

### Philosophical Tension

The protocol uses two different contract mechanisms:

| Zone | Contract Type | Behavior |
|------|--------------|----------|
| Core | `@pre`/`@post` | Runtime assertions (fail if violated) |
| Shell | `Result[T, E]` | Type-level contracts (explicit error handling) |

This is actually **good design** - different zones have different needs. But the protocol doesn't clearly articulate WHY beyond "Shell handles chaos".

**Deeper rationale:**
- Core: Deterministic, so violations are programmer errors → assertions appropriate
- Shell: Non-deterministic, so failures are expected → explicit return type appropriate

### The "Can Fail" Criterion

Current question: "Can this fail for reasons outside my control?"

**Problem:** This is ambiguous. What about:
- Division by zero? (inside control, but can fail)
- Integer overflow? (inside control, but can fail)
- Infinite recursion? (inside control, but can fail)

**Better framing:** The distinction is really **deterministic vs non-deterministic**, not "can fail vs cannot fail".

---

## 2. Protocol Structure Analysis

### What's Good

| Section | Strength |
|---------|----------|
| Section 0 (Quick Start) | Excellent - minimum viable knowledge |
| The Four Laws | Clear, memorable, actionable |
| ICIDV workflow | Well-structured checkpoints |
| Section 11 (Deep Dive) | Good rationale explanations |
| Section 12 (Governance) | Thoughtful evolution controls |

### Critical Issues Found

#### Issue 1: Section 7 is FACTUALLY WRONG

**Current text (lines 486-496):**
```
**Invar CANNOT detect (current):**
- Dynamic imports (`__import__`, `importlib`)
- Function-internal imports
- Impure function calls (`datetime.now()`, `random.random()`)
...

**Planned improvements (Phase 5):**
- Function-internal import detection
- Common impure call detection
```

**Reality:** Phase 3 ALREADY IMPLEMENTED these features!
- `check_internal_imports()` in purity.py
- `check_impure_calls()` in purity.py
- `--strict-pure` CLI flag

**Impact:** High - misleads users about actual capabilities

#### Issue 2: ICIV references remain

| Location | Text |
|----------|------|
| Section 8 (line 504) | "One ICIV cycle = one commit" |
| Section 9 (line 521) | "Follow ICIV, build features" |

Should say **ICIDV**.

#### Issue 3: Law 3 references non-existent feature

**Current text (line 196):**
```
| 1 | `invar map` output | First, to understand structure |
```

**Reality:** `invar map` command doesn't exist! This is Phase 4 work.

#### Issue 4: INVAR.md meta-violation

- INVAR.md is **1094 lines**
- Protocol says files should be < 300 lines
- (Arguably protocol docs are different from code, but worth noting)

---

## 3. Implementation Analysis

### What's Good

| Component | Strength |
|-----------|----------|
| models.py | Clean Pydantic models |
| parser.py | Robust AST handling |
| purity.py | Well-extracted, focused |
| config.py | Multiple sources, good priority |
| cli.py | Clean Typer implementation |

### Issues Found

#### Issue 5: Wrapper functions without contracts

```python
# rules.py lines 249-256
def check_internal_imports(file_info: FileInfo, config: RuleConfig) -> list[Violation]:
    """Delegate to purity.check_internal_imports."""
    return _check_internal_imports(file_info, config.strict_pure)
```

- These violate "Core functions need @pre/@post" rule
- Guard correctly warns about this (2 warnings)
- Root cause: signature mismatch between rule system and purity functions

#### Issue 6: Inconsistent rule signatures

| Module | Signature |
|--------|-----------|
| rules.py | `(file_info: FileInfo, config: RuleConfig) -> list[Violation]` |
| purity.py | `(file_info: FileInfo, strict_pure: bool) -> list[Violation]` |

This inconsistency required wrapper functions.

**Fix:** Unify signatures to `(file_info: FileInfo, config: RuleConfig)`.

#### Issue 7: RuleConfig is dataclass, not Pydantic

```python
# rules.py
@dataclass
class RuleConfig:
    ...
```

All other models use Pydantic. Inconsistent.

#### Issue 8: Missing Shell contract validation

**Protocol says:** Shell must return `Result[T, E]`

**Guard checks:** Nothing! Only checks Core contracts.

This is a significant gap - Shell's primary contract requirement is not enforced.

---

## 4. Document Inconsistencies

### Version References Need Sync

| Location | Current |
|----------|---------|
| Section 12.3 example | `protocol_version = "3.7"` (should be 3.9) |
| Section 12.6 example | `protocol_version = "3.8"` (should be 3.9) |

### Redundancy

| Content | Appears In |
|---------|------------|
| ICIDV workflow | INVAR.md Section 2, CLAUDE.md |
| Core vs Shell decision | INVAR.md Section 0, 1, 11.2 |
| Four Pillars | VISION.md, INVAR.md |

This creates maintenance burden - changes must be synced across multiple files.

---

## 5. Simplification Opportunities

### Config Profiles

Current: Many individual options
```toml
strict_pure = true
use_code_lines = false
require_contracts = true
require_doctests = true
```

Better: Profiles
```toml
profile = "strict"  # or "standard", "relaxed"
```

### Documentation Consolidation

Proposal:
- Keep INVAR.md as authoritative protocol
- CLAUDE.md references INVAR.md, doesn't duplicate
- VISION.md for philosophy only (no implementation details)

### Version Single-Sourcing

Current: Version in 4+ places
- INVAR.md header
- pyproject.toml
- context.md
- docs/DESIGN.md

Could: Generate from single source during build.

---

## 6. Priority Matrix

### Critical (Fix Now)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 1 | Section 7 wrong capabilities | High | Low |
| 2 | ICIV → ICIDV in Sections 8, 9 | Medium | Low |

### Important (Fix Soon)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 3 | Law 3 references non-existent `invar map` | Medium | Low |
| 5 | Unify rule signatures | Medium | Medium |
| 8 | Add Shell Result validation | High | Medium |

### Nice to Have (Future)

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 4 | Split INVAR.md | Low | High |
| 7 | RuleConfig to Pydantic | Low | Low |
| - | Config profiles | Medium | Medium |
| - | Documentation consolidation | Medium | High |

---

## 7. Recommendations

### Immediate Actions (This Session)

1. **Fix Section 7** - Update "CAN detect" and "CANNOT detect" lists
2. **Fix ICIV references** - Change to ICIDV in Sections 8, 9
3. **Fix Law 3** - Note that `invar map` is "planned" not available
4. **Fix version examples** - Update to 3.9 in Section 12

### Short-term Actions (Next Phase)

5. **Unify rule signatures** - Make purity checks use `RuleConfig`
6. **Add Shell validation** - Check for Result return types
7. **Convert RuleConfig** - Use Pydantic for consistency

### Long-term Considerations

8. **Config profiles** - Simplify configuration
9. **Split INVAR.md** - Extract sections to separate docs
10. **Single-source versioning** - Automate version sync

---

## 8. First-Principles Summary

### What Invar Gets Right

1. **Core separation principle** - Sound architecture
2. **Contracts as enforcement** - Not just prompts
3. **Incremental adoption** - Protocol → Guard → Map
4. **Honest limitations** - (once fixed) Transparent about what Guard can't do
5. **Governance framework** - Controlled evolution

### What Could Be Better

1. **Precision of "can fail"** - Should be "deterministic vs non-deterministic"
2. **Protocol/implementation sync** - Capabilities must match docs
3. **Contract consistency** - All zones should have enforceable contracts
4. **Documentation structure** - Less redundancy, better modularity

### The Fundamental Question

> Is Invar's complexity justified by its benefits?

**Analysis:**
- Investment: ~15-20% overhead (contracts, separation, verification)
- Return: Fewer bugs, clearer architecture, AI-friendly codebase
- Break-even: Projects > 2-3 modules with significant logic

**Verdict:** Yes, for projects that benefit from structure. Not for small scripts or prototypes.

---

*This review was conducted using first-principles analysis: questioning every assumption and evaluating alignment between stated goals, protocol text, and actual implementation.*
