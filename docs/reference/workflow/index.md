# Workflow Mechanisms

Invar's development workflow for agent sessions.

## Quick Reference

| Document | Purpose |
|----------|---------|
| [USBV](./usbv.md) | The four-phase development workflow |
| [Session Start](./session-start.md) | Check-In and Final protocols |

## Core Concept

Every task follows USBV:

```
U - Understand : Intent, Inspect (invar sig/map), Constraints
S - Specify    : @pre/@post, Design decomposition, Doctests
B - Build      : Implement leaves first, Compose
V - Validate   : invar guard, reflect → iterate → validate
```

## Session Bookends

```
Session Start:
  ✓ Check-In: MyProject | main | clean

... USBV workflow (guard runs in VALIDATE phase) ...

Session End:
  ✓ Final: guard PASS | 0 errors, 0 warnings
```

**Both required.** Missing either = incomplete task.

## Key Principle

> **"Inspect before Contract. Depth varies naturally. Iterate when needed."**

## See Also

- [Contract Mechanisms](../contracts/README.md) - Writing contracts
- [Verification Overview](../verification/README.md) - How verification works
