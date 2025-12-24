# Workflow Mechanisms

Invar's development workflow for agent sessions.

## Quick Reference

| Document | Purpose |
|----------|---------|
| [ICIDIV](./icidiv.md) | The six-step development workflow |
| [Session Start](./session-start.md) | Check-In and Final protocols |

## Core Concept

Every task follows ICIDIV:

```
I - Intent    : What? Core or Shell? Edge cases?
C - Contract  : @pre/@post + doctests BEFORE code
I - Inspect   : invar sig, invar map --top 10
D - Design    : Decompose, leaves first
I - Implement : Write code to pass doctests
V - Verify    : invar guard, reflect → fix → verify
```

## Session Bookends

```
Session Start:
  ✓ Check-In: guard PASS | top: main, cli

... ICIDIV workflow ...

Session End:
  ✓ Final: guard PASS | 0 errors, 0 warnings
```

**Both required.** Missing either = incomplete task.

## Key Principle

> **"Contract before Implement. Verify after every change. No exceptions."**

## See Also

- [Contract Mechanisms](../contracts/README.md) - Writing contracts
- [Verification Overview](../verification/README.md) - How verification works
