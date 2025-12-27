# Visible Workflow Example (DX-30)

This example shows how to use the 3-checkpoint TodoList for complex tasks.

## Check-In First (DX-54)

Every session starts with Check-In:

```
✓ Check-In: MyProject | feature-branch | clean
```

**Do NOT run guard/map at Check-In.** Guard is for VALIDATE phase and Final only.

## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

For complex tasks, show 3 checkpoints (BUILD is internal work):

```python
# TodoList with USBV checkpoints
todos = [
    {"content": "[UNDERSTAND] Add user authentication, Shell layer", "status": "completed"},
    {"content": "[SPECIFY] Define authenticate() → Result[User, AuthError]", "status": "in_progress"},
    {"content": "[VALIDATE] Run invar guard, fix violations", "status": "pending"},
]
```

## Contract Declaration Convention

Show contracts in your message BEFORE writing code:

```python
# [SPECIFY] validate_token function:

@pre(lambda token: isinstance(token, str) and len(token) > 0)
@post(lambda result: isinstance(result, dict) and 'sub' in result)
def validate_token(token: str) -> dict:
    '''Validate JWT token and return payload.'''
    ...

# Edge cases:
# - Empty token → InvalidToken
# - Malformed token → InvalidToken
# - Expired token → TokenExpired
```

Then implement (BUILD phase is internal, not shown in TodoList):

```python
# [BUILD] Now writing the code...

import jwt
from deal import pre, post

@pre(lambda token: isinstance(token, str) and len(token) > 0)
@post(lambda result: isinstance(result, dict) and 'sub' in result)
def validate_token(token: str) -> dict:
    '''
    Validate JWT token and return payload.

    >>> validate_token("eyJ...")  # doctest: +SKIP
    {'sub': 'user123', 'exp': 1234567890}
    '''
    return jwt.decode(token, options={"verify_signature": False})
```

## Complete Workflow Example

### Task: Add discount calculation to Core

```
[TodoList - 3 Checkpoints]
□ [UNDERSTAND] Add calculate_discount to core/pricing.py
  - Intent: Pure calculation, Core module
  - Context: Existing pricing functions in pricing.py
  - Constraints: price > 0, rate in [0,1]

□ [SPECIFY] Define @pre/@post for calculate_discount
  - Contract: @pre price > 0, rate in [0,1]; @post result >= 0
  - Design: Single function, no decomposition needed
  - Doctests: normal, zero discount, full discount

□ [VALIDATE] Run guard, confirm correctness
```

### [SPECIFY] Checkpoint

```python
[SPECIFY] calculate_discount:
@pre(lambda price, rate: price > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_discount(price: float, rate: float) -> float:
    '''Apply discount rate to price.'''

Edge cases:
- price = 0 → Rejected by @pre (price must be > 0)
- rate = 0 → Full price (no discount)
- rate = 1 → Zero (100% discount)
- rate > 1 → Rejected by @pre
```

### BUILD (Internal - Not Shown in TodoList)

```python
from deal import pre, post

@pre(lambda price, rate: price > 0 and 0 <= rate <= 1)
@post(lambda result: result >= 0)
def calculate_discount(price: float, rate: float) -> float:
    '''
    Apply discount rate to price.

    >>> calculate_discount(100.0, 0.2)
    80.0
    >>> calculate_discount(100.0, 0)
    100.0
    >>> calculate_discount(100.0, 1)
    0.0
    '''
    return price * (1 - rate)
```

### [VALIDATE] Checkpoint

```bash
$ invar guard --changed
src/myapp/core/pricing.py
  ✓ All checks passed

Summary: 0 errors, 0 warnings
Code Health: 100%

# Review Gate: Not triggered (no escape hatches, good coverage)
# If triggered: invoke /review sub-agent before completion
```

## When to Use Visible Workflow

Use for:
- New features (3+ functions)
- Architectural changes
- Core module modifications

Skip for:
- Single-line fixes
- Documentation changes
- Trivial refactoring

## Key Principles

1. **Visibility enables accountability** — When the workflow is visible, both agents and users can verify compliance.

2. **BUILD is internal** — No user decision needed during implementation. Show UNDERSTAND, SPECIFY, VALIDATE only.

3. **Inspect before Contract** — UNDERSTAND phase includes examining existing code before writing contracts.

4. **Review Gate (DX-31)** — When Guard triggers `review_suggested` (escape hatches ≥3, coverage <50%, security paths), invoke `/review` sub-agent before task completion.
