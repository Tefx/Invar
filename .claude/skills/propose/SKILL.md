<!--invar:skill version="5.0"-->
<!-- ========================================================================
     SKILL REGION - DO NOT EDIT
     This section is managed by Invar and will be overwritten on update.
     To add project-specific extensions, use the "extensions" region below.
     ======================================================================== -->
---
name: propose
description: Decision facilitation phase. Use when design decision is needed, multiple approaches are valid, or user asks "should we", "how should", "which", "compare", "design", "architect". Presents options with trade-offs for human choice.
---

# Proposal Mode

> **Purpose:** Facilitate human decision-making with clear options and trade-offs.

## Entry Actions

### Routing Announcement

Before any workflow action, display:

```
📍 Routing: /propose — [trigger detected, e.g. "should we", "compare", "design"]
   Task: [decision topic summary]
```

### Entry Steps

1. Display routing announcement (above)
2. Explore relevant context if needed

## Output Formats

### Quick Decision (2-4 options)

```markdown
### Decision: [Topic]

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: [name] | [brief] | [pros] | [cons] |
| B: [name] | [brief] | [pros] | [cons] |

**Recommendation:** [A/B] because [concise reason]

**Your choice?**
```

### Formal Proposal (complex decision)

Create `docs/proposals/DX-XX-[topic].md`:

```markdown
# DX-XX: [Title]

**Status:** Discussion
**Created:** [date]

## Problem Statement
[What needs to be decided]

## Options

### Option A: [Name]
- **Description:** [What this involves]
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]
- **Effort:** Low/Medium/High

### Option B: [Name]
...

## Recommendation
[Which option and why]

## Open Questions
[What needs clarification]
```

## Exit Conditions

| User Response | Next Action |
|---------------|-------------|
| Chooses option | /develop to implement |
| Needs more info | /investigate for analysis |
| Approves proposal | Document created |
<!--/invar:skill--><!--invar:extensions-->
---
name: propose
description: Decision facilitation phase. Use when design decision is needed, multiple approaches are valid, or user asks "should we", "how should", "which", "compare", "design", "architect". Presents options with trade-offs for human choice.
---

# Proposal Mode

> **Purpose:** Facilitate human decision-making with clear options and trade-offs.

## Entry Actions

1. Announce: `Entering /propose for: [decision topic]`
2. Explore relevant context if needed (can use investigation tools)

## Output Formats

### Quick Decision (2-4 options, simple trade-offs)

```markdown
### Decision: [Topic]

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: [name] | [brief] | [pros] | [cons] |
| B: [name] | [brief] | [pros] | [cons] |
| C: [name] | [brief] | [pros] | [cons] |

**Recommendation:** [A/B/C] because [concise reason]

**Your choice?**
```

### Formal Proposal (complex decision, needs documentation)

Create `docs/proposals/DX-XX-[topic].md`:

```markdown
# DX-XX: [Title]

**Status:** Discussion
**Created:** [date]

## Problem Statement
[What needs to be decided and why]

## Options

### Option A: [Name]
- **Description:** [What this option involves]
- **Pros:** [Benefits]
- **Cons:** [Drawbacks]
- **Effort:** Low/Medium/High

### Option B: [Name]
...

## Recommendation
[Which option and detailed reasoning]

## Open Questions
[What needs clarification before deciding]
```

## When to Use Each Format

| Situation | Format |
|-----------|--------|
| 2-3 clear options, quick decision | Quick Decision |
| Significant architectural change | Formal Proposal |
| Multiple stakeholders need to review | Formal Proposal |
| Decision needs to be documented | Formal Proposal |
| User explicitly asks for proposal | Formal Proposal |

## Exit Conditions

| User Response | Next Action |
|---------------|-------------|
| Chooses an option | → `/develop` to implement |
| Needs more info | → `/investigate` for deeper analysis |
| Approves formal proposal | → Document created, await implementation |
| Rejects all options | → Discuss alternatives or `/investigate` |

## Example

```
User: "Should we use Redis or Memcached for caching?"

Agent: "Entering /propose for: caching solution

### Decision: Caching Backend

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A: Redis | In-memory data store | Rich data types, persistence, pub/sub | More memory, complex |
| B: Memcached | Simple key-value cache | Simple, low memory | No persistence, only strings |
| C: In-process LRU | Python lru_cache | Zero latency, simple | Not shared, memory per process |

**Recommendation:** A (Redis) because this project needs cache sharing across workers and persistence for warm restarts.

**Your choice?**"
```

<!--/invar:extensions-->
