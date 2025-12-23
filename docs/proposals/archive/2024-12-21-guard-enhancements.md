# Protocol Change Proposal: Guard Enhancements & New Tools

> New features inspired by research synthesis: reflection prompts, contract quality tiers, consistency checking, recovery context, and more.

---

## Metadata

- **Date:** 2024-12-21
- **Author:** Agent (based on research synthesis)
- **Status:** Draft
- **Layer:** L2 (Tool) + L1 (Protocol)
- **Depends On:** [2024-12-21-test-first-enhancement.md](./2024-12-21-test-first-enhancement.md)
- **References:**
  - All 6 papers from the test-first proposal
  - Invar Five Laws (enhanced from Four Laws)

---

## Context

This proposal extends the test-first enhancement proposal with concrete tool improvements. While the test-first proposal focuses on workflow and philosophy changes, this proposal focuses on **tooling implementation**.

### Research Foundation Summary

| Paper | Key Insight | Tool Application |
|-------|-------------|------------------|
| AlphaCodium | Test-first doubles accuracy | Contract scaffolding |
| Pel | Contracts enable auto-recovery | Recovery context generation |
| Parsel | Decomposition +75% | Decomposition assistant |
| SWE-bench | Clear specs = solvable | Solvability score |
| Reflexion | Reflection improves fixes | Reflection prompts |
| Clover | Contract completeness | Quality tiers, consistency check |

---

## Proposed Features

### Feature 1: Reflection Prompts

**Priority:** High | **Complexity:** Low | **Version:** v0.5.0

When Guard finds violations, provide reflection questions instead of just fix suggestions.

**Current Output:**
```
ERROR: missing_contract at calculate() in pricing.py:15
  Hint: Add @pre/@post decorator
```

**Enhanced Output:**
```
ERROR: missing_contract at calculate() in pricing.py:15

  Hint: Add @pre/@post decorator

  Reflection questions:
  - What inputs would make this function fail or behave unexpectedly?
  - What does this function guarantee to its callers?
  - Can you write 3 doctests: normal case, boundary, edge case?

  Example:
    @pre(lambda x, y: x > 0 and y > 0)
    @post(lambda result: result >= 0)
    def calculate(x: int, y: int) -> int:
        """
        >>> calculate(2, 3)
        5
        """
```

**Implementation:**
- Add `reflection_prompts` field to `RULE_META`
- Modify `core/formatter.py` to display prompts
- Prompts tailored per violation type

**Rule-Specific Prompts:**

| Violation | Reflection Prompts |
|-----------|-------------------|
| `missing_contract` | What inputs are invalid? What does output guarantee? |
| `empty_contract` | What constraint does this function actually need? |
| `function_size` | What sub-tasks can be extracted? Which are reusable? |
| `impure_call` | Can this value be passed as parameter instead? |
| `missing_doctest` | What are 3 examples: normal, boundary, error case? |

---

### Feature 2: Contract Quality Tiers

**Priority:** High | **Complexity:** Medium | **Version:** v0.5.0

Replace binary `missing_contract` with a tiered quality system.

**Tiers:**

| Level | Name | Criteria | Severity |
|-------|------|----------|----------|
| 0 | None | No @pre or @post | ERROR |
| 1 | Partial | Has @pre OR @post (not both) | WARNING |
| 2 | Complete | Has @pre AND @post | OK |
| 3 | Verified | Complete + doctests cover all conditions | IDEAL |

**New Rules:**

```python
# Replace missing_contract with:
"contract_level_0": {
    "severity": "error",
    "message": "No contract on Core function",
    "hint": "Add both @pre and @post for complete specification"
}

"contract_level_1": {
    "severity": "warning",
    "message": "Incomplete contract (has {has} but missing {missing})",
    "hint": "Complete contracts uniquely determine implementation"
}
```

**Guard Output:**

```
Contract Quality Report:
  Level 3 (Verified):  12 functions  ████████████ 40%
  Level 2 (Complete):  10 functions  ██████████   33%
  Level 1 (Partial):    5 functions  █████        17%
  Level 0 (None):       3 functions  ███          10%

  Contract Completeness: 73%
```

**Configuration:**

```toml
[tool.invar.guard]
# Minimum contract level required (0-3)
min_contract_level = 2  # Require at least @pre AND @post
```

---

### Feature 3: Consistency Checker

**Priority:** Medium | **Complexity:** Medium | **Version:** v0.6.0

New command to check three-way consistency: Code ↔ Contracts ↔ Doctests.

**Command:**

```bash
invar consistency [path]
invar consistency src/core/pricing.py
invar consistency src/core/pricing.py::calculate_total
```

**Checks Performed:**

| Check | Description | Example Issue |
|-------|-------------|---------------|
| `doctest_pre_coverage` | Doctests exercise @pre conditions | @pre has 3 conditions, doctests only test 2 |
| `doctest_post_coverage` | Doctests verify @post guarantees | @post says result > 0, no doctest checks this |
| `docstring_contract_match` | Docstring describes same constraints | Docstring says "positive" but @pre allows 0 |
| `code_post_satisfaction` | Code paths satisfy @post | Some code path returns value not matching @post |

**Output:**

```
$ invar consistency src/core/pricing.py

Consistency Report: src/core/pricing.py
========================================

calculate_total():
  ✓ @pre conditions covered by doctests (3/3)
  ✓ @post guarantees verified by doctests (2/2)
  ⚠ Docstring mentions "non-empty" but @pre doesn't check len(items) > 0
  ✓ All code paths satisfy @post

apply_discount():
  ⚠ @pre has condition "rate <= 1" but no doctest tests boundary (rate=1)
  ✓ @post guarantees verified
  ✓ Docstring matches contracts

Summary: 2 warnings, 0 errors
Consistency Score: 85%
```

**Implementation:**

- New `core/consistency.py` module
- AST analysis for code path → @post satisfaction
- Pattern matching for docstring ↔ contract correlation
- New `shell/cli.py` command

---

### Feature 4: Recovery Context Generation

**Priority:** High | **Complexity:** Low | **Version:** v0.5.0

When `--agent` mode reports violations, include rich recovery context.

**Current `--agent` Output:**

```json
{
  "violations": [
    {
      "rule": "missing_contract",
      "file": "pricing.py",
      "line": 15,
      "symbol": "calculate_total",
      "hint": "Add @pre/@post decorator"
    }
  ]
}
```

**Enhanced Output:**

```json
{
  "violations": [
    {
      "rule": "missing_contract",
      "file": "pricing.py",
      "line": 15,
      "symbol": "calculate_total",
      "hint": "Add @pre/@post decorator",

      "recovery_context": {
        "function_signature": "def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal",
        "parameters": [
          {"name": "items", "type": "list[Item]", "suggested_pre": "len(items) > 0"},
          {"name": "tax_rate", "type": "Decimal", "suggested_pre": "0 <= tax_rate <= 1"}
        ],
        "return_type": "Decimal",
        "suggested_post": "result >= 0",

        "similar_functions": [
          {"name": "calculate_subtotal", "file": "pricing.py", "has_contract": true},
          {"name": "apply_discount", "file": "pricing.py", "has_contract": true}
        ],

        "call_sites": [
          {"file": "orders.py", "line": 45, "context": "total = calculate_total(cart.items, config.tax_rate)"},
          {"file": "api.py", "line": 123, "context": "return calculate_total(items, Decimal('0.1'))"}
        ],

        "reflection_prompts": [
          "What constraints do items and tax_rate have?",
          "What does the return value guarantee?",
          "What edge cases should doctests cover?"
        ],

        "suggested_contract": "@pre(lambda items, tax_rate: len(items) > 0 and 0 <= tax_rate <= 1)\n@post(lambda result: result >= 0)"
      }
    }
  ]
}
```

**Implementation:**

- Enhance `core/suggestions.py` with recovery context
- Add `--recovery-context` flag (or include by default in `--agent`)
- Cross-file analysis for similar functions and call sites

---

### Feature 5: Health Trend Tracking

**Priority:** Medium | **Complexity:** Low | **Version:** v0.5.0

Track Code Health history over time.

**Storage:**

```
.invar/
├── context.md
└── health_history.json
```

**health_history.json:**

```json
{
  "history": [
    {"date": "2024-12-20", "commit": "abc123", "health": 85, "errors": 0, "warnings": 12},
    {"date": "2024-12-21", "commit": "def456", "health": 87, "errors": 0, "warnings": 10},
    {"date": "2024-12-21", "commit": "ghi789", "health": 89, "errors": 0, "warnings": 8}
  ]
}
```

**Commands:**

```bash
# Show health trend
invar health --history

Code Health Trend (last 10 commits):
  85% → 87% → 89%  ↑ Improving

  abc123  85%  ████████████████░░░░
  def456  87%  █████████████████░░░
  ghi789  89%  █████████████████░░░

# Record current health (run after guard)
invar guard --record-health

# Show health delta
invar health --delta
  Health: 89% (+2% from last commit)
  Warnings fixed: 2
  New warnings: 0
```

**Integration:**

- `invar guard --record-health` appends to history
- Pre-commit hook can record automatically
- CI can fail if health decreases

---

### Feature 6: Contract Scaffolding

**Priority:** Medium | **Complexity:** Medium | **Version:** v0.6.0

Generate contract suggestions from function signatures and usage.

**Command:**

```bash
invar scaffold <file>::<function>
invar scaffold src/core/pricing.py::calculate_total
```

**Output:**

```
Suggested contracts for calculate_total():

Based on signature:
  @pre(lambda items, tax_rate: ...)  # items: list[Item], tax_rate: Decimal
  @post(lambda result: ...)          # result: Decimal

Based on parameter types:
  - items: list[Item] → suggest: len(items) > 0 (non-empty list)
  - tax_rate: Decimal → suggest: 0 <= tax_rate <= 1 (percentage)

Based on return type:
  - Decimal → suggest: result >= 0 (non-negative money)

Based on call sites (2 found):
  - orders.py:45 passes: cart.items (always non-empty after validation)
  - api.py:123 passes: Decimal('0.1') (valid tax rate)

Suggested contract:
  @pre(lambda items, tax_rate: len(items) > 0 and 0 <= tax_rate <= 1)
  @post(lambda result: result >= 0)
  def calculate_total(items: list[Item], tax_rate: Decimal) -> Decimal:
      """
      Calculate total with tax.

      >>> calculate_total([Item(price=100)], Decimal('0.1'))
      Decimal('110.0')
      >>> calculate_total([Item(price=50)], Decimal('0'))
      Decimal('50.0')
      >>> calculate_total([Item(price=100)], Decimal('1'))
      Decimal('200.0')
      """
```

**Implementation:**

- New `core/scaffold.py` module
- Type-based heuristics for common patterns
- Call site analysis for usage patterns
- Doctest generation based on signature

---

### Feature 7: Solvability Score

**Priority:** Low | **Complexity:** Medium | **Version:** v0.7.0

Quantify how well-specified a function is.

**Formula:**

```
Solvability = (Contract Completeness × 0.4) +
              (Doctest Coverage × 0.3) +
              (Determinism × 0.3)

Where:
  Contract Completeness = (has_pre × 0.5) + (has_post × 0.5)
  Doctest Coverage = doctests_count / expected_doctests (capped at 1)
  Determinism = 1.0 if Core, 0.5 if Shell, 0.0 if impure
```

**Output:**

```
$ invar solvability src/core/pricing.py

Solvability Report:
==================

calculate_total(): 95% (Highly Solvable)
  Contract: 100% (@pre ✓, @post ✓)
  Doctests: 100% (4/3 expected)
  Determinism: 100% (Core, pure)

apply_discount(): 70% (Moderately Solvable)
  Contract: 50% (@pre ✓, @post ✗)
  Doctests: 67% (2/3 expected)
  Determinism: 100% (Core, pure)

get_current_price(): 40% (Needs Specification)
  Contract: 0% (no contracts)
  Doctests: 33% (1/3 expected)
  Determinism: 100% (Core, pure)

File Average: 68%
```

**Use Case:**

- Identify under-specified functions
- Prioritize which functions need better contracts
- Track specification quality over time

---

### Feature 8: Progressive Strictness

**Priority:** Medium | **Complexity:** Low | **Version:** v0.6.0

Projects can graduate from lenient to strict mode.

**Configuration:**

```toml
[tool.invar.guard]
# Strictness profiles
strictness = "standard"  # "lenient" | "standard" | "strict" | "paranoid"
```

**Profile Definitions:**

| Profile | contract_level_1 | function_size | missing_doctest |
|---------|------------------|---------------|-----------------|
| lenient | ignore | warning | ignore |
| standard | warning | warning | warning |
| strict | error | error | warning |
| paranoid | error | error | error |

**Graduation Path:**

```bash
# Check if ready for next level
invar graduation

Current: standard
Next level: strict

To graduate to strict:
  ✓ 0 contract_level_0 violations (required: 0)
  ✗ 3 contract_level_1 violations (required: 0)
  ✓ 0 function_size violations (required: 0)

Fix 3 incomplete contracts to graduate.
```

**Auto-Graduation:**

```toml
[tool.invar.guard]
auto_graduate = true  # Automatically upgrade strictness when ready
```

---

## Implementation Phases

### Phase 1: v0.5.0 (Immediate)

| Feature | Complexity | Impact |
|---------|------------|--------|
| Reflection Prompts | Low | High |
| Recovery Context | Low | High |
| Health Trend | Low | Medium |

### Phase 2: v0.6.0 (Short-term)

| Feature | Complexity | Impact |
|---------|------------|--------|
| Contract Quality Tiers | Medium | High |
| Contract Scaffolding | Medium | Medium |
| Progressive Strictness | Low | Medium |

### Phase 3: v0.7.0 (Medium-term)

| Feature | Complexity | Impact |
|---------|------------|--------|
| Consistency Checker | Medium | High |
| Solvability Score | Medium | Medium |

---

## Impact Analysis

- [x] Guard output affected
  - Reflection prompts in violation messages
  - Contract quality tiers in summary
  - Recovery context in --agent mode
- [x] New commands
  - `invar consistency`
  - `invar scaffold`
  - `invar health --history`
  - `invar solvability`
  - `invar graduation`
- [x] New configuration options
  - `min_contract_level`
  - `strictness`
  - `auto_graduate`
- [x] New files
  - `core/consistency.py`
  - `core/scaffold.py`
  - `core/solvability.py`
  - `.invar/health_history.json`

---

## Approval

- [ ] Human has reviewed this proposal
- [ ] Human explicitly approves: _____________ (signature/date)

---

## Implementation Checklist

After approval:

### Phase 1 (v0.5.0)
- [ ] Add reflection prompts to RULE_META
- [ ] Enhance formatter with reflection output
- [ ] Add recovery context to --agent mode
- [ ] Implement health history tracking
- [ ] Add `invar health --history` command

### Phase 2 (v0.6.0)
- [ ] Implement contract quality tiers
- [ ] Add `min_contract_level` config
- [ ] Create `core/scaffold.py`
- [ ] Add `invar scaffold` command
- [ ] Implement strictness profiles
- [ ] Add `invar graduation` command

### Phase 3 (v0.7.0)
- [ ] Create `core/consistency.py`
- [ ] Add `invar consistency` command
- [ ] Create `core/solvability.py`
- [ ] Add `invar solvability` command

---

## Summary

This proposal introduces 8 new features that extend Invar's capabilities based on research insights:

| Feature | Research Source | User Benefit |
|---------|-----------------|--------------|
| Reflection Prompts | Reflexion | Better understanding before fixing |
| Contract Quality Tiers | Clover | Measurable contract improvement |
| Consistency Checker | Clover | Three-way validation |
| Recovery Context | Pel | Faster, smarter fixes |
| Health Trend | - | Progress visibility |
| Contract Scaffolding | AlphaCodium | Easier contract writing |
| Solvability Score | SWE-bench | Specification quality metric |
| Progressive Strictness | - | Gradual adoption path |

**Philosophy:** These tools embody the Five Laws by making it easier to write complete contracts, decompose problems, and reflect on failures.
