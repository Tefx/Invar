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
> **Mindset:** OPTIONS, not decisions — human chooses.

## Scope Boundaries

**This skill IS for:**
- Presenting design choices with trade-offs
- Facilitating architectural decisions
- Comparing approaches (A vs B)
- Creating formal proposals for complex decisions

**This skill is NOT for:**
- Implementing the chosen option → switch to `/develop`
- Researching to understand the problem → switch to `/investigate`
- Reviewing existing code → switch to `/review`

**Drift detection:** If you find yourself writing implementation code → STOP, wait for user choice, then exit to `/develop`.

## Constraints

**FORBIDDEN in this phase:**
- Writing implementation code (beyond examples)
- Making decisions for the user
- Creating files other than proposals
- Committing changes

**ALLOWED:**
- Read, Glob, Grep (research for options)
- invar_sig, invar_map (understand current state)
- Creating proposal documents in `docs/proposals/`

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
