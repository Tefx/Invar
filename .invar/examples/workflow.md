# Visible Workflow Example (DX-30)

This example shows how to use Phase TodoList and Contract Declaration for complex tasks.

## Phase TodoList Format

For complex tasks, create a TodoList with ICIDIV phase markers:

```python
# TodoList with phase markers
todos = [
    {"content": "[Intent] Add user authentication, Shell layer", "status": "completed"},
    {"content": "[Contract] Define authenticate() → Result[User, AuthError]", "status": "in_progress"},
    {"content": "[Inspect] Review existing auth code in shell/auth.py", "status": "pending"},
    {"content": "[Design] Split into validate_token() + fetch_user()", "status": "pending"},
    {"content": "[Implement] Write code for each function", "status": "pending"},
    {"content": "[Verify] Run invar guard, fix violations", "status": "pending"},
]
```

## Contract Declaration Convention

Show contracts in your message BEFORE writing code:

```python
# [Contract] validate_token function:

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

Then implement:

```python
# [Implement] Now writing the code...

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
[TodoList]
□ [Intent] Add calculate_discount to core/pricing.py
□ [Contract] Define @pre/@post for price > 0, rate in [0,1]
□ [Inspect] Check existing pricing functions
□ [Design] Single function, no decomposition needed
□ [Implement] Write function
□ [Verify] Run guard
```

### [Contract] Phase

```python
[Contract] calculate_discount:
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

### [Implement] Phase

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

### [Verify] Phase

```bash
$ invar guard --changed
src/myapp/core/pricing.py
  ✓ All checks passed

Summary: 0 errors, 0 warnings
Code Health: 100%
```

## When to Use Phase TodoList

Use for:
- New features (3+ functions)
- Architectural changes
- Core module modifications

Skip for:
- Single-line fixes
- Documentation changes
- Trivial refactoring

## Key Principle

**Visibility enables accountability.** When the workflow is visible, both agents and users can verify compliance.
