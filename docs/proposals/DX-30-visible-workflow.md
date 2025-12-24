# DX-30: Visible Workflow Enforcement

> **"Make ICIDIV compliance visible and verifiable, not assumed."**

**Status:** Proposed
**Created:** 2024-12-24
**Relates to:** DX-17 (Workflow Enforcement), DX-27 (System Prompt Protocol)

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
Layer 2: [HARD]   Guard Rules        - contract_quality_ratio WARNING
Layer 1: [SOFT]   Phase TodoList     - Visible workflow in TodoWrite
```

**Design rationale:** We evaluated a third layer (MCP checkpoint tool) but rejected it because:
- Agent can skip the tool with no consequence
- No enforcement mechanism possible without complex state tracking
- Adds complexity without adding value
- Phase 1 conventions achieve the same visibility

### Layer 1: Phase TodoList + Contract Convention (Soft Enforcement)

**Mechanism:** Convention for complex tasks - show ICIDIV phases in TodoList and contracts before code.

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

**Contract Declaration Convention:**

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

**Benefits:**
- User sees plan before execution
- Agent self-documents workflow compliance
- Natural checkpoint for feedback
- Contracts visible before implementation

**Implementation:** Zero code changes. Documentation + convention only.

**Difficulty:** ⭐ (trivial)

### Layer 2: Guard Rule (Hard Enforcement)

**Mechanism:** New rule checks contract coverage ratio in Core files.

#### New Rule: `contract_quality_ratio`

```python
# In rules.py
def check_contract_quality_ratio(file_info: FileInfo) -> list[Violation]:
    """
    Ensure sufficient contract coverage in Core files.

    WARNING if < 80% of functions have @pre or @post.

    Examples:
        >>> # 10 functions, 7 with contracts = 70% → WARNING
        >>> # 10 functions, 8 with contracts = 80% → PASS
    """
    if not file_info.is_core:
        return []

    functions = [s for s in file_info.symbols if s.is_function and not s.name.startswith('_')]
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

**Guard output:**

```
$ invar guard

src/myapp/core/auth.py
  ⚠ contract_quality_ratio: Contract coverage: 60% (3/5). Target: 80%+
    → Add @pre/@post to remaining functions

Summary: 0 errors, 1 warning
```

**Difficulty:** ⭐⭐ (moderate - follows existing rule pattern)

## Rejected Alternatives

### MCP Contract Tool (Rejected)

We considered a `declare_contracts` MCP tool but rejected it:

```
Problem: If agent skips the tool, nothing different happens
- No enforcement mechanism
- Just ceremony without value
- Adds complexity without benefit

Conclusion: Convention (Phase 1) achieves same visibility without tool overhead
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

## Implementation Plan

### Phase 1: Documentation (Immediate)

- [ ] Add Phase TodoList convention to INVAR.md
- [ ] Add Contract Declaration convention to INVAR.md
- [ ] Add examples to .invar/examples/

**Difficulty:** ⭐
**Effort:** 1 hour

### Phase 2: Guard Rule (Short-term)

- [ ] Implement `contract_quality_ratio` rule in rules.py
- [ ] Add to rule_meta.py with WARNING severity
- [ ] Add tests
- [ ] Update docs/mechanisms/rules/README.md

**Difficulty:** ⭐⭐
**Effort:** 2-3 hours

## Evaluation Matrix

| Approach | Agent-Native | Visibility | Enforcement | Difficulty | Status |
|----------|--------------|------------|-------------|------------|--------|
| Phase TodoList | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ✅ Phase 1 |
| Contract Convention | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ✅ Phase 1 |
| Guard Rule | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ✅ Phase 2 |
| Contract Tool | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ❌ Rejected |
| Edit Integration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ Rejected |

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

[Now implementing...]
```

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Contract-before-Implement compliance | Unknown | 80%+ visible |
| Guard violations from missing contracts | ~20% of runs | <5% |
| Rework due to wrong implementation | Frequent | Rare |

## Backward Compatibility

- Phase TodoList: Opt-in convention, no breaking changes
- Guard rule: New rule, WARNING severity, configurable via severity_overrides

## Related Work

- DX-17: Workflow enforcement via 4-layer defense
- DX-27: System prompt protocol (complementary)
- DX-28: Semantic verification (contract quality)

## Appendix: INVAR.md Addition

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

[Implement] Now coding...
```

This makes compliance visible and catches mistakes early.
```
