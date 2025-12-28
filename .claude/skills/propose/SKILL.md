---
name: propose
description: Decision facilitation phase. Use when design decision is needed, multiple approaches are valid, or user asks "should we", "how should", "which", "compare", "design", "architect". Presents options with trade-offs for human choice.
_invar:
  version: "5.0"
  managed: skill
---
<!--invar:skill-->

# Proposal Mode

> **Purpose:** Facilitate human decision-making with clear options and trade-offs.

## Entry Actions

### Context Refresh (DX-54)

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules section)
2. Display routing announcement

### Routing Announcement

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
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Project-specific proposal templates
     - Decision criteria or checklists
     - Stakeholder notification rules
     - Architecture decision record (ADR) formats
     ======================================================================== -->
<!--/invar:extensions-->
