## Documentation Structure

| File | Owner | Edit? | Purpose |
|------|-------|-------|---------|
| INVAR.md | Invar | No | Protocol (`invar update` to sync) |
| CLAUDE.md | User | Yes | Project customization (this file) |
| .invar/context.md | User | Yes | Project state, lessons learned |
| .invar/project-additions.md | User | Yes | Project rules → injected into CLAUDE.md |
| .invar/examples/ | Invar | No | **Must read:** Core/Shell patterns, workflow |

> **Before writing code:** Check Task Router in `.invar/context.md`

## Visible Workflow (DX-30)

For complex tasks (3+ functions), show 3 checkpoints in TodoList:

```
□ [UNDERSTAND] Task description, codebase context, constraints
□ [SPECIFY] Contracts and design decomposition
□ [VALIDATE] Guard results, Review Gate status, integration status
```

**BUILD is internal work** — not shown in TodoList.

**Show contracts before code.** See `.invar/examples/workflow.md` for full example.

## Phase Visibility (DX-51)

Each USBV phase transition requires a visible header:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Three-layer visibility:**
- **Skill** (`/develop`) — Routing announcement
- **Phase** (`SPECIFY 2/4`) — Phase header (this section)
- **Tasks** — TodoWrite items

Phase headers are SEPARATE from TodoWrite. Phase = where you are; TodoWrite = what to do.

---

## Context Management (DX-54)

Re-read `.invar/context.md` when:
1. Entering any workflow (/develop, /review, etc.)
2. Completing a TodoWrite task (before moving to next)
3. Conversation exceeds ~15-20 exchanges
4. Unsure about project rules or patterns

**Refresh is transparent** — do not announce "I'm refreshing context."
Only show routing announcements when entering workflows.
