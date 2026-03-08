## Visible Workflow

For complex tasks (3+ functions), show 3 checkpoints in TodoList:

```
□ [UNDERSTAND] Task description, codebase context, constraints
□ [SPECIFY] Contracts and design decomposition
□ [VALIDATE] Verification results, Review Gate if triggered, integration status
```

**BUILD is internal work** — not shown in TodoList.

**Show contracts before code.** Example:

```
[SPECIFY] calculate_discount:
PRECONDITION: price > 0 AND 0 <= rate <= 1
POSTCONDITION: result >= 0
FUNCTION calculate_discount(price, rate): ...

[BUILD] Now coding...
```

**When to use:** New features (3+ functions), architectural changes, Core modifications.
**Skip for:** Single-line fixes, documentation, trivial refactoring.
