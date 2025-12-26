# Contract Mechanisms

Invar's contract system for defining and verifying function behavior.

## Quick Reference

| Document | Purpose |
|----------|---------|
| [Pre/Post Contracts](./pre-post.md) | `@pre`/`@post` syntax and patterns |
| [Doctests](./doctests.md) | Executable examples as specification |
| [Contract Completeness](./completeness.md) | When contracts are "complete" |
| [Advanced Features](./advanced.md) | `@must_use`, `invariant()`, `@must_close` |

## Core Concept

Contracts define WHAT a function does, not HOW:

```python
from deal import pre, post

@pre(lambda x: x >= 0)           # Input constraint
@post(lambda result: result >= 0)  # Output guarantee
def sqrt(x: float) -> float:
    """
    >>> sqrt(4.0)
    2.0
    """
    return x ** 0.5
```

## Three-Way Consistency

```
        Code
       /    \
@pre/@post ↔ Doctests
```

All three must align. Any conflict is a bug.

## Verification Pipeline

```
invar guard
├─ Static analysis (checks contract syntax)
├─ Doctests (runs examples)
├─ CrossHair (proves contracts symbolically)
└─ Hypothesis (property testing)
```

## See Also

- [USBV Workflow](../workflow/usbv.md) - Contract-first development
- [Verification Overview](../verification/README.md) - How contracts are verified
