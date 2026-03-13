# Workflow Mechanisms

> **DX-91:** The USBV four-phase workflow is now **archived**. Current guidance: write `@pre/@post` contracts BEFORE implementation. Guard enforces outcomes, not ceremony.

## Current Workflow (DX-91)

### The ONE Mandatory Rule

**Write `@pre/@post` contracts BEFORE implementation.**

Guard rejects uncontracted Core functions. This is not optional.

### Session Pattern

```
1. Understand → 2. Specify (contracts first) → 3. Build → 4. Validate
```

**Depth varies naturally.** Some tasks need deep inspection; others need minimal. Let resistance guide you.

## Quick Reference

| Document | Purpose |
|----------|---------|
| [Session Start](./session-start.md) | DX-91 session guidance + archive classification |
| ~~[USBV](./usbv.md)~~ | **Archive** — Historical four-phase documentation |

## Key Principle

> **"Inspect before Contract. Depth varies naturally. Iterate when needed."**

## See Also

- [Contract Mechanisms](../contracts/index.md) - Writing contracts
- [Verification Overview](../verification/index.md) - How verification works
- [DX-91 Proposal](../../proposals/DX-91-simplification.md) - Workflow simplification rationale
