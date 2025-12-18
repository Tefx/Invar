# Phase 3 Implementation Review: Agent Perspective

> A retrospective analysis of the Phase 3 Guard Enhancement implementation,
> examining methodology, protocol, and tooling from an AI agent's perspective.

---

## 1. Development Timeline Reconstruction

### What Happened

```
1. Read context.md → Understood task scope (4 items)
2. Explored existing code → parser.py, rules.py, models.py
3. Designed approach → Add fields to models, extraction in parser, rules
4. Implemented sequentially:
   - models.py: Added 3 new fields (+4 lines)
   - parser.py: Added extraction logic (+163 lines → 352 total, OVER LIMIT)
   - rules.py: Added 2 new rules (+74 lines → 374 total, OVER LIMIT)
   - config.py: Added config parsing (+7 lines)
   - cli.py: Added --strict-pure option (+12 lines)
5. Guard caught file size violation → Emergency refactoring
6. Created purity.py → Extracted ~170 lines from parser.py and rules.py
7. Fixed doctest order issue (set() non-determinism)
8. Tests passed, Guard passed
9. Review discovered bug: CLI arg used instead of config value
10. Fixed bug, updated documentation
```

### Time Distribution (Estimated)

| Phase | Effort | Notes |
|-------|--------|-------|
| Understanding task | 5% | context.md was clear |
| Exploring code | 10% | Good existing patterns |
| Initial implementation | 35% | Straightforward |
| **Refactoring (unexpected)** | **25%** | File size forced extraction |
| Fixing issues | 10% | Doctest, bug |
| Documentation | 15% | context.md, CLAUDE.md |

**Key observation:** 25% of effort spent on unplanned refactoring.

---

## 2. Friction Points Analysis

### 2.1 File Size Limit Surprise

**What happened:**
- Added ~240 lines of new code across parser.py and rules.py
- Both files exceeded 300-line limit
- Had to create new module mid-implementation

**Root cause:** No estimation step before implementation.

**Impact:**
- Wrapper functions needed for signature adaptation
- Wrapper functions triggered "missing contract" warnings
- Additional complexity

**Lesson:** Estimate code size BEFORE implementing. If existing file is >200 lines and you're adding >50 lines, plan for extraction.

### 2.2 Signature Inconsistency

**What happened:**
- Existing rules: `(file_info: FileInfo, config: RuleConfig) -> list[Violation]`
- New rules: `(file_info: FileInfo, strict_pure: bool) -> list[Violation]`
- Needed wrapper functions to adapt

**Root cause:** Extracted rules to purity.py which doesn't depend on RuleConfig.

**Better approach:** Keep signature consistent, pass RuleConfig even if only one field is used.

### 2.3 Configuration vs CLI Bug

**What happened:**
```python
# Bug: Uses CLI arg, not config value
_output_rich(report, strict_pure)

# Fixed: Uses config value
_output_rich(report, config.strict_pure)
```

**Root cause:** No integration test for "config file enables feature" scenario.

**Why not caught:**
- Doctest tests individual functions
- No test for: "When config has strict_pure=true, output shows indicator"

### 2.4 Set Ordering Non-determinism

**What happened:**
```python
# Doctest expected:
['os', 'pathlib']
# Got:
['pathlib', 'os']
```

**Root cause:** Used `list(set(...))` for deduplication, set has no order guarantee.

**Fix:** Use `sorted()` in doctest.

**Lesson:** Always use sorted() when testing unordered collections.

### 2.5 Class Methods Not Checked

**What happened:** Parser only extracts top-level functions, not class methods.

**Root cause:** Design decision made in Phase 1, not reconsidered for Phase 3.

**Impact:** Methods inside classes don't get purity checks.

---

## 3. Methodology Critique

### 3.1 ICIV Workflow Gaps

The current ICIV workflow:
```
Intent → Contract → Implementation → Verify
```

**Gap 1: No Design Phase**

Between Contract and Implementation, there should be:
- File size estimation
- Signature consistency check
- Module boundary decisions
- Edge case identification (class methods, nested functions)

**Gap 2: Verify is Too Narrow**

Current "Verify" = run pytest --doctest-modules

Missing:
- Integration scenarios (config + CLI combinations)
- Regression testing (existing features still work)
- Self-check (run Guard on the changes)

### 3.2 Proposed ICIDV Workflow

```
Intent → Contract → Inspect → Design → Implement → Verify
                      ↑
              (New step)
```

**Inspect phase:**
- Check existing file sizes
- Identify signature patterns
- Note edge cases to handle

**Design phase:**
- Estimate code size
- Plan module structure
- Design consistent signatures
- Document decisions

**Enhanced Verify:**
- Unit tests (doctest)
- Integration tests (config scenarios)
- Self-check (invar guard)

### 3.3 "File Size Budget" Concept

Each file has a "budget":
```
parser.py: 189 lines → budget: 111 lines before extraction needed
rules.py: 299 lines → budget: 1 line (already at limit!)
```

Before adding code, check budget:
```
If (current_lines + estimated_new_lines) > 280:
    Plan extraction BEFORE implementing
```

---

## 4. Protocol Improvement Proposals

### 4.1 Law 4 Enhancement

**Current:**
> Run tests after every change. No exceptions.

**Proposed:**
> Run tests AND self-check after every change.
> - pytest --doctest-modules (unit)
> - invar guard (architecture)
> - Test config file scenarios (integration)

### 4.2 New Section: Design Checklist

Before implementing any feature:

```markdown
□ File size check: Will any file exceed 280 lines?
□ Signature check: Does new code follow existing patterns?
□ Edge cases: What about methods/nested functions/async?
□ Config impact: Does this add config options? How tested?
□ CLI impact: Does this add CLI options? Does config override work?
```

### 4.3 Quick Reference Addition

Add to "When Confused" section:

```markdown
- **File will be too long?** → Extract module BEFORE implementing
- **Signature differs from existing?** → Match existing pattern
- **Adding config option?** → Test both config and CLI scenarios
```

---

## 5. Tool Improvement Proposals

### 5.1 Guard Enhancements

**Pre-flight check:**
```bash
invar guard --estimate models.py +50  # "Would be 137 lines, OK"
invar guard --estimate parser.py +100  # "Would be 289 lines, WARNING: near limit"
```

**Signature consistency:**
```
WARN: Rule function signatures inconsistent
  - check_file_size(FileInfo, RuleConfig) -> list[Violation]
  - check_impure_calls(FileInfo, bool) -> list[Violation]
  Suggestion: Unify signatures
```

**Method checking option:**
```toml
[tool.invar.guard]
check_class_methods = true  # Also check methods inside classes
```

### 5.2 Context.md Template Enhancement

Add sections:
```markdown
## Current Task
- Task: [description]
- Progress: [X/Y items done]
- Blockers: [any blockers]

## Design Decisions Pending
- [ ] Should class methods be checked?
- [ ] Should signature be unified?
```

### 5.3 Test Scenario Generator

```bash
invar test-scenarios guard
# Outputs:
# Scenario 1: No config, no CLI flags → defaults
# Scenario 2: Config strict_pure=true, no CLI flag → strict_pure enabled
# Scenario 3: Config strict_pure=false, CLI --strict-pure → CLI overrides
# ...
```

---

## 6. Documentation Gaps

### 6.1 CLAUDE.md Missing

**Common Pitfalls section:**
- set() ordering in doctests
- CLI param vs config value
- File size estimation

**Design Patterns section:**
- Rule function standard signature
- Module extraction procedure

### 6.2 INVAR.md Missing

**Section 11.3 Troubleshooting expansion:**
- "File too long after changes" → extraction procedure
- "Signature inconsistent" → adaptation pattern

---

## 7. What Worked Well

1. **context.md** - Clear task definition, easy to understand scope
2. **Existing patterns** - parser.py and rules.py provided templates
3. **Guard self-check** - Caught file size violation immediately
4. **Separation principle** - Clear where new code should go
5. **Doctest** - Quick verification cycle

---

## 8. Recommendations Summary

### Immediate (This Project)

| Priority | Action |
|----------|--------|
| P0 | Add integration test for config+CLI scenarios |
| P0 | Unify rule function signatures |
| P1 | Add class method checking option |
| P1 | Add "Design Checklist" to CLAUDE.md |

### Protocol Evolution

| Change | Impact |
|--------|--------|
| ICIV → ICIDV | More upfront planning |
| Enhanced Verify | Catches integration bugs |
| File size budget | Prevents surprise refactoring |

### Tooling

| Feature | Benefit |
|---------|---------|
| Pre-flight size check | Plan extraction early |
| Signature consistency check | Catch inconsistencies |
| Test scenario generator | Ensure coverage |

---

## 9. Meta-Observation

The Invar framework successfully:
- Caught architecture violations (file size)
- Enforced separation (Core/Shell)
- Required verification (tests)

But missed:
- Design-phase guidance
- Integration testing
- Consistency enforcement

**The framework is good at catching WHAT went wrong, but could help more with HOW to do it right from the start.**

---

*Generated during Phase 3 retrospective, 2024-12-19*
