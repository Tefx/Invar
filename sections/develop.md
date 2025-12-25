# Development Workflow

> **Purpose:** Implement solutions following USBV workflow with verification.

## When to Use

- Clear, actionable tasks
- "Add", "implement", "create", "fix", "update", "build", "write"
- After /investigate or /propose has clarified the approach

## Entry Actions (REQUIRED)

### Check-In

```python
invar_guard(changed=true)
invar_map(top=10)
```

**Display:**
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

**No visible Check-In = Development not started.**

## USBV Workflow

```
UNDERSTAND → SPECIFY → BUILD → VALIDATE
     │           │        │        │
  [depth]    [depth]  [depth]  [depth]
     └───────────┴────────┴────────┘
           Depth varies naturally
```

### 1. UNDERSTAND

- **Intent:** What exactly needs to be done?
- **Inspect:** Use `invar sig` to see existing contracts
- **Context:** Read relevant code, understand patterns
- **Constraints:** What must NOT change?

### 2. SPECIFY

- **Contracts FIRST:** Write `@pre`/`@post` before implementation
- **Doctests:** Add examples for expected behavior
- **Design:** Decompose complex tasks into sub-functions

```python
# SPECIFY before BUILD:
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    >>> calculate(10)
    100
    """
    ...  # Implementation comes in BUILD
```

### 3. BUILD

**For complex tasks:** Enter Plan Mode first, get user approval.

**Implementation rules:**
- Follow the contracts written in SPECIFY
- Run `invar_guard(changed=true)` frequently
- Commit after each logical unit

**Commit format:**
```bash
git add . && git commit -m "feat: [description]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 4. VALIDATE

- Run `invar_guard()` (full verification)
- All TodoWrite items complete
- Integration works (if applicable)

**Iteration Paths:**
- Logic error → Return to BUILD
- Missing edge case → Return to SPECIFY (add doctest)
- Misunderstood requirement → Return to UNDERSTAND
- Review Gate triggered → Invoke /review

## Visible Workflow

For complex tasks (3+ functions), show checkpoints:

```
□ [UNDERSTAND] Task description, context, constraints
□ [SPECIFY] Contracts before implementation
□ [VALIDATE] Guard results, integration status
```

**BUILD is internal work** — not shown in TodoList.

## Task Batching

For multiple tasks:
1. Create TodoWrite with all items upfront
2. Execute sequentially (not parallel)
3. After each task:
   - Commit changes
   - Run `invar_guard(changed=true)`
   - Update TodoWrite
4. **Limits:** Max 5 tasks OR 4 hours OR Guard failure

## Failure Handling

| Guard Result | Action |
|--------------|--------|
| Static fixable (missing contract) | Auto-fix, retry (max 2) |
| Test failure | Report to user, ask for guidance |
| Contract violation | Report, suggest /investigate |
| Repeated failure | Stop, ask user |

## Exit Actions (REQUIRED)

### Final

```python
invar_guard()
```

**Display:**
```
✓ Final: guard [PASS/FAIL] | [errors] errors, [warnings] warnings
```

**If Guard reports `review_suggested`:**
```
⚠ Review suggested. Run /review for quality check.
```

## Task Completion Checklist

- [ ] Check-In displayed
- [ ] Intent explicitly stated
- [ ] Contracts written before implementation
- [ ] Final displayed with guard results
- [ ] User requirement satisfied
