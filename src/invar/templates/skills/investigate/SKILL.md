---
name: investigate
description: Exploration and understanding phase. Use when task is vague, needs analysis, or requires understanding before action. Triggers on "why", "what is", "how does", "explain", "understand", "analyze". NO CODE CHANGES in this phase.
---

# Investigation Mode

> **Purpose:** Understand before acting. Gather information, analyze code, report findings.

## Constraints

**FORBIDDEN in this phase:**
- Edit, Write (no code changes)
- git commit (nothing to commit)
- Creating new files

**ALLOWED:**
- Read, Glob, Grep (exploration)
- invar sig, invar map (perception)
- WebSearch, WebFetch (research)

## Entry Actions

1. Announce: `Entering /investigate for: [topic]`
2. Run `invar map --top 10` for codebase orientation
3. Read `.invar/context.md` if relevant to topic

## Tool Selection

| I want to... | Use |
|--------------|-----|
| See function contracts | `invar sig <file>` |
| Find entry points | `invar map --top 10` |
| Search code patterns | Grep with regex |
| Explore codebase | Task(Explore) agent |

## Exit Format

```markdown
### Investigation Complete

**Topic:** [what was investigated]

**Findings:**
1. [Key finding 1]
2. [Key finding 2]
3. [Key finding 3]

**Details:**
[Detailed explanation with file:line references]

**Recommendation:**
- [ ] /propose — Design decision needed
- [ ] /develop — Ready to implement [specific task]
- [ ] More investigation — [what's still unclear]

**Next step?**
```
