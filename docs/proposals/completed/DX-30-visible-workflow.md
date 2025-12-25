# DX-30: Visible Workflow Enforcement

> **"Make workflow compliance visible and verifiable, not assumed."**

**Status:** ✅ Complete (Phase 1-2 implemented, Phase 3 merged into DX-31)
**Created:** 2024-12-24
**Updated:** 2025-12-25
**Relates to:** DX-17 (Workflow Enforcement), DX-27 (System Prompt Protocol), DX-31 (Adversarial Reviewer)

## Problem

### The Invisible Workflow

Current ICIDIV workflow relies on agent self-compliance:

```
Expected: Intent → Contract → Inspect → Design → Implement → Verify
Actual:   Intent → [skip] → [skip] → [skip] → Implement → Verify (fail) → fix
```

**Root cause:** No visibility into whether agent followed workflow. User sees only the output.

### Why This Matters

| Violation | Impact | Detection |
|-----------|--------|-----------|
| Skip Contract | Wrong implementation, rework | Late (at Verify) |
| Skip Inspect | Miss existing code, duplicate | Late (code review) |
| Skip Design | Spaghetti code, poor decomposition | Late (maintenance) |

**Key insight:** The most violated step is **Contract before Implement**. This is also the most impactful.

### Quantitative Evidence

From DX-17 analysis:

| Expected | Actual | Gap |
|----------|--------|-----|
| Read .invar/examples/ | Skipped | 100% miss |
| Run invar guard --changed | Skipped | 100% miss |
| Contract BEFORE code | Simultaneous | Order violation |

## Design Principles

### Agent-Native Requirements

| Principle | Application |
|-----------|-------------|
| Automatic > Opt-in | Enforcement via tools, not reminders |
| Default ON | New behavior is default, opt-out if needed |
| Zero Config | Works without pyproject.toml changes |
| Visible Progress | User sees workflow state |

### Non-Goals

- ❌ Force ICIDIV for trivial tasks (1-line fixes)
- ❌ Block agent from working (only warn/inform)
- ❌ Require complex state tracking infrastructure
- ❌ Create ceremony without enforcement (tools that can be skipped add no value)

## Proposed Solution

### Two-Layer Enforcement

```
┌─────────────────────────────────────────────────────────────┐
│                    Two-Layer Defense                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: [HARD]   Guard Rules                               │
│           contract_quality_ratio WARNING                     │
│           Core files must have 80%+ contract coverage        │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: [SOFT]   Phase TodoList + Contract Convention      │
│           Visible workflow in TodoWrite                      │
│           Contracts shown before implementation              │
└─────────────────────────────────────────────────────────────┘
```

**Design rationale:** We evaluated a third layer (MCP checkpoint tool) but rejected it because:
- Agent can skip the tool with no consequence
- No enforcement mechanism possible without complex state tracking
- Adds complexity without adding value
- Phase 1 conventions achieve the same visibility

---

## Layer 1: Phase TodoList + Contract Convention (Soft Enforcement)

### 1.1 Phase TodoList Format

**Mechanism:** Convention for complex tasks - show ICIDIV phases in TodoList.

```python
# Agent creates TodoList with phase markers
todos = [
    {"content": "[Intent] Add user authentication, Shell layer", "status": "completed"},
    {"content": "[Contract] Define authenticate() → Result[User, AuthError]", "status": "in_progress"},
    {"content": "[Inspect] Review existing auth code in shell/auth.py", "status": "pending"},
    {"content": "[Design] Split into validate_token() + fetch_user()", "status": "pending"},
    {"content": "[Implement] Write code for each function", "status": "pending"},
    {"content": "[Verify] Run invar guard, fix violations", "status": "pending"},
]
```

**Phase markers:** `[Intent]`, `[Contract]`, `[Inspect]`, `[Design]`, `[Implement]`, `[Verify]`

**When to use:**
- ✅ New features (3+ functions)
- ✅ Architectural changes
- ✅ Core module modifications
- ❌ Single-line fixes
- ❌ Documentation-only changes

### 1.2 Contract Declaration Convention

**Mechanism:** Show contracts in message before writing code.

```python
# Agent shows contracts in message before code
"""
[Contract] validate_token function:

@pre(lambda token: isinstance(token, str) and len(token) > 0)
@post(lambda result: isinstance(result, dict) and 'sub' in result)
def validate_token(token: str) -> dict:
    '''Validate JWT token and return payload.'''

Edge cases:
- Empty token → InvalidToken
- Malformed token → InvalidToken
- Expired token → TokenExpired
"""

# Then implement
# [Implement] Now writing the code...
```

**Contract completeness check:**
> "Given only @pre/@post and doctests, could someone else write the exact same function?"

If no → contracts need more detail.

### 1.3 Benefits

- User sees plan before execution
- Agent self-documents workflow compliance
- Natural checkpoint for feedback
- Contracts visible before implementation
- No code changes required

**Implementation:** Zero code changes. Documentation + convention only.

**Difficulty:** ⭐ (trivial)

---

## Layer 2: Guard Rule (Hard Enforcement)

### 2.1 New Rule: `contract_quality_ratio`

**Mechanism:** New rule checks contract coverage ratio in Core files.

```python
# In src/invar/core/rules.py

def check_contract_quality_ratio(file_info: FileInfo) -> list[Violation]:
    """
    Ensure sufficient contract coverage in Core files.

    WARNING if < 80% of public functions have @pre or @post.

    Examples:
        >>> # 10 functions, 7 with contracts = 70% → WARNING
        >>> # 10 functions, 8 with contracts = 80% → PASS
    """
    if not file_info.is_core:
        return []

    functions = [s for s in file_info.symbols
                 if s.is_function and not s.name.startswith('_')]
    if not functions:
        return []

    total = len(functions)
    with_contracts = sum(1 for f in functions if f.has_pre or f.has_post)

    ratio = with_contracts / total if total > 0 else 1.0

    if ratio < 0.8:
        return [Violation(
            rule="contract_quality_ratio",
            severity=Severity.WARNING,
            message=f"Contract coverage: {ratio:.0%} ({with_contracts}/{total}). Target: 80%+",
            suggestion="Add @pre/@post to remaining functions"
        )]
    return []
```

### 2.2 Guard Output Example

```
$ invar guard

src/myapp/core/auth.py
  ⚠ contract_quality_ratio: Contract coverage: 60% (3/5). Target: 80%+
    → Add @pre/@post to remaining functions

Summary: 0 errors, 1 warning
Code Health: 94% ████████████████████░
```

### 2.3 Rule Metadata

```python
# In src/invar/core/rule_meta.py

RULE_META["contract_quality_ratio"] = RuleMeta(
    severity=Severity.WARNING,
    description="Core files should have 80%+ contract coverage",
    rationale="Contracts enable verification and documentation",
    fix_hint="Add @pre/@post decorators to public functions",
)
```

**Difficulty:** ⭐⭐ (moderate - follows existing rule pattern)

---

## Integration with DX-31 (Adversarial Reviewer)

### Trigger Architecture

DX-30 provides visibility; DX-31 adds verification. They complement each other:

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVIEW TRIGGER LAYERS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 3: Task Completion Gate (Agent Protocol)                  │
│  ├─ Before marking task "complete", evaluate: need review?       │
│  ├─ If Guard suggested review → spawn sub-agent                  │
│  └─ Incorporate findings into completion report                  │
│                                                                  │
│  Layer 2: Guard Suggestions (INFO/WARNING)                       │
│  ├─ review_suggested: "New Core file, consider review"           │
│  ├─ review_suggested: "3+ escape hatches, review recommended"    │
│  └─ contract_quality_ratio: Low coverage triggers review         │
│                                                                  │
│  Layer 1: ICIDIV Workflow Integration (DX-30)                    │
│  ├─ VERIFY phase: Guard check + conditional review               │
│  └─ Phase TodoList makes workflow visible                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Guard → Review Connection

When `contract_quality_ratio` fires, it can trigger `review_suggested`:

```python
# Combined check
if ratio < 0.8:
    violations.append(Violation(
        rule="contract_quality_ratio",
        severity=Severity.WARNING,
        message=f"Contract coverage: {ratio:.0%}. Target: 80%+",
    ))

if ratio < 0.5:  # Very low coverage
    violations.append(Violation(
        rule="review_suggested",
        severity=Severity.INFO,
        message="Low contract coverage - independent review recommended",
    ))
```

---

## Rejected Alternatives

### MCP Contract Tool (Rejected)

We considered a `declare_contracts` MCP tool but rejected it:

```
Problem: If agent skips the tool, nothing different happens
- No enforcement mechanism
- Just ceremony without value
- Adds complexity without benefit

Conclusion: Convention (Layer 1) achieves same visibility without tool overhead
```

### Edit Tool Integration (Rejected)

We considered adding contract checks to the Edit tool:

```
Problem: Requires complex conversation state tracking
- How to know if contracts were "shown" before Edit?
- Cross-turn state management is hard
- Too intrusive to normal workflow

Conclusion: Post-hoc Guard check is simpler and equally effective
```

### Blocking Enforcement (Rejected)

We considered making `contract_quality_ratio` an ERROR:

```
Problem: Would block legitimate incremental development
- Sometimes you write code first to understand the problem
- Contracts can be refined iteratively
- Blocking is hostile to exploration

Conclusion: WARNING is sufficient - visible but not blocking
```

---

## Implementation Plan

### Phase 1: Documentation (Immediate)

| Task | File | Effort |
|------|------|--------|
| Add Phase TodoList convention | INVAR.md | 30 min |
| Add Contract Declaration convention | INVAR.md | 30 min |
| Add workflow example | .invar/examples/workflow.md | 30 min |
| Update CLAUDE.md template | src/invar/templates/ | 15 min |

**Total:** ~2 hours
**Difficulty:** ⭐

### Phase 2: Guard Rule (Short-term)

| Task | File | Effort |
|------|------|--------|
| Implement `contract_quality_ratio` | src/invar/core/rules.py | 1 hour |
| Add rule metadata | src/invar/core/rule_meta.py | 15 min |
| Add tests | tests/core/test_rules.py | 1 hour |
| Update docs | docs/mechanisms/rules/README.md | 30 min |

**Total:** ~3 hours
**Difficulty:** ⭐⭐

### Phase 3: DX-31 Integration ✅ Merged

> **Merged into DX-31:** The low contract coverage trigger has been incorporated into DX-31's `review_suggested` rule. See DX-31 "Trigger Conditions" table.

| Task | Status |
|------|--------|
| Add `review_suggested` trigger | ✅ Merged into DX-31 |
| Connect to low coverage (<50%) | ✅ Merged into DX-31 |
| Document integration | Pending with DX-31 |

**No separate implementation needed.** DX-31 Phase 1 will implement all trigger conditions including low contract coverage.

---

## INVAR.md Addition (Draft)

```markdown
## Visible Workflow (DX-30)

For complex tasks, show ICIDIV phases in your TodoList:

```
□ [Intent] Task description, Core/Shell classification
□ [Contract] Function signatures with @pre/@post
□ [Inspect] Files and symbols to review
□ [Design] Decomposition plan
□ [Implement] Write code
□ [Verify] Guard results
```

**Contract before Implement:** Show contracts in your message before writing code.

```python
[Contract] calculate_discount:
@pre(lambda price, rate: price > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_discount(price: float, rate: float) -> float:
    ...

Edge cases:
- price = 0 → Invalid (rejected by @pre)
- rate = 0 → Full price
- rate = 1 → Zero (free)

[Implement] Now coding...
```

**When to use Phase TodoList:**
- New features (3+ functions)
- Architectural changes
- Core module modifications

**When to skip:**
- Single-line fixes
- Documentation changes
- Trivial refactoring

This makes compliance visible and catches mistakes early.
```

---

## Evaluation Matrix

| Approach | Agent-Native | Visibility | Enforcement | Difficulty | Status |
|----------|--------------|------------|-------------|------------|--------|
| Phase TodoList | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ✅ Phase 1 |
| Contract Convention | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ✅ Phase 1 |
| Guard Rule | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ✅ Phase 2 |
| DX-31 Integration | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | 📋 Phase 3 |
| Contract Tool | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ❌ Rejected |
| Edit Integration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ Rejected |

---

## Example: Full Workflow

### Before DX-30

```
User: Add authentication to the API

Agent: I'll add authentication.
[writes code without showing contracts]
[runs guard]
[guard fails: missing_contract]
[adds contracts after the fact]
```

### After DX-30

```
User: Add authentication to the API

Agent: I'll add authentication. Let me plan this with ICIDIV.

[TodoList]
□ [Intent] Add JWT authentication, Shell layer (entry point) + Core (validation)
□ [Contract] Define validate_token() and authenticate() contracts
□ [Inspect] Check existing auth patterns in shell/
□ [Design] Split: validate_token (Core) → authenticate (Shell)
□ [Implement] Write functions
□ [Verify] Run guard

[Contract]
Core function: validate_token
@pre: token matches JWT format (xxx.yyy.zzz)
@post: returns decoded payload dict or raises InvalidToken

Shell function: authenticate
@pre: token is non-empty string
@post: returns Result[User, AuthError]

Edge cases:
- Empty token → AuthError.InvalidToken
- Malformed → AuthError.InvalidToken
- Expired → AuthError.TokenExpired
- Valid → Success(User)

[Now implementing...]
```

---

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Contract-before-Implement compliance | Unknown | 80%+ visible |
| Guard violations from missing contracts | ~20% of runs | <5% |
| Rework due to wrong implementation | Frequent | Rare |
| Phase TodoList adoption | 0% | 50%+ for complex tasks |

---

## Backward Compatibility

- **Phase TodoList:** Opt-in convention, no breaking changes
- **Contract Convention:** Opt-in convention, no breaking changes
- **Guard rule:** New rule, WARNING severity, configurable via severity_overrides

```toml
# pyproject.toml - if you want to disable
[tool.invar.guard]
severity_overrides = { contract_quality_ratio = "off" }
```

---

## Related Work

- **DX-17:** Workflow enforcement via 4-layer defense (Check-In format)
- **DX-27:** System prompt protocol (complementary)
- **DX-28:** Semantic verification (contract quality)
- **DX-31:** Independent adversarial reviewer (review triggers)

---

## Summary

DX-30 addresses the "invisible workflow" problem with a two-layer approach:

1. **Soft enforcement (conventions):** Phase TodoList and Contract Declaration make workflow visible to users without requiring code changes.

2. **Hard enforcement (Guard rule):** `contract_quality_ratio` ensures Core files maintain adequate contract coverage.

The design is deliberately incremental - Phase 1 is pure documentation, Phase 2 adds tooling, Phase 3 integrates with DX-31's review system.

**Key principle:** Visibility enables accountability. When the workflow is visible, both agents and users can verify compliance.
