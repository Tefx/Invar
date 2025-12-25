---
name: develop
description: Implementation phase following USBV workflow. Use when task is clear and actionable - "add", "implement", "create", "fix", "update", "build", "write". Requires Check-In at start and Final at end.
---

# Development Mode

> **Purpose:** Implement solution following USBV workflow with verification.

## Entry Actions (REQUIRED)

### Check-In

```bash
invar guard --changed
invar map --top 10
```

**Display:**
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

**No visible Check-In = Development not started.**

## USBV Workflow

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

- Follow the contracts written in SPECIFY
- Run `invar guard --changed` frequently
- Commit after each logical unit

### 4. VALIDATE

- Run `invar guard` (full verification)
- All todos complete
- Integration works

## Task Batching

For multiple tasks:
1. Create todo list with all items
2. Execute sequentially
3. After each: commit, run guard, update todos
4. **Limits:** Max 5 tasks OR 4 hours OR Guard failure

## Exit Actions (REQUIRED)

### Final

```bash
invar guard
```

**Display:**
```
✓ Final: guard [PASS/FAIL] | [errors] errors, [warnings] warnings
```

**If Guard reports `review_suggested`:**
```
⚠ Review suggested. Run /review for quality check.
```
