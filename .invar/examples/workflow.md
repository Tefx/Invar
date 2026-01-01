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
from invar_runtime import pre, post

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
from invar_runtime import pre, post

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

## Interleaved SPECIFY/BUILD (DX-63)

For multi-function tasks, use **interleaved** pattern instead of batch creation.

### ❌ Wrong: Batch Creation

```
# Creates 5 files at once, then fills implementations
1. Create file1.py, file2.py, file3.py, file4.py, file5.py (skeletons)
2. Implement all functions
3. Run guard → 40 missing_contract errors
4. Retrofit contracts (descriptive, not prescriptive)
```

### ✅ Correct: Interleaved Pattern

```
TodoList:
□ [SPECIFY] Write contracts for parser.py
□ [BUILD] Implement parser.py
□ [SPECIFY] Write contracts for validator.py
□ [BUILD] Implement validator.py
□ [SPECIFY] Write contracts for formatter.py
□ [BUILD] Implement formatter.py
```

### Function-Level Gates

For each file:

```python
# Step 1: Create file with contracts only (body = ...)
@pre(lambda text: len(text) > 0)
@post(lambda result: all(isinstance(t, Token) for t in result))
def tokenize(text: str) -> list[Token]:
    """Tokenize input text."""
    ...

@pre(lambda tokens: len(tokens) > 0)
@post(lambda result: isinstance(result, AST))
def parse(tokens: list[Token]) -> AST:
    """Parse tokens into AST."""
    ...
```

```bash
# Step 2: Verify contract coverage
$ invar guard -c src/core/parser.py
Contract Coverage Check
========================================
Files: 1 | Functions: 2

Coverage: 2/2 (100%) ✓
Trivial:  0/2 (0%)   ✓

Ready for BUILD phase.
```

```python
# Step 3: Implement (only after coverage check passes)
@pre(lambda text: len(text) > 0)
@post(lambda result: all(isinstance(t, Token) for t in result))
def tokenize(text: str) -> list[Token]:
    """
    Tokenize input text.

    >>> tokenize("hello world")
    [Token('hello'), Token('world')]
    """
    return [Token(word) for word in text.split()]
```

```bash
# Step 4: Full verification
$ invar guard --changed
Guard passed.

# Step 5: Proceed to next file
```

### Violation Self-Check

Before writing ANY implementation code, ask:

1. "Have I written the contract for THIS function?"
2. "Have I shown it in my response?"
3. "Have I run `invar guard -c`?"

If any NO → Stop. Write contract first.

### Benefits

| Without DX-63 | With DX-63 |
|---------------|------------|
| 81 errors at end | 0 errors |
| 4+ guard cycles | 1 cycle |
| ~7000 tokens | ~4000 tokens |
| Descriptive contracts | Prescriptive contracts |

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
