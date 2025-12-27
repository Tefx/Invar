<!--invar:skill version="5.0"-->
<!-- ========================================================================
     SKILL REGION - DO NOT EDIT
     This section is managed by Invar and will be overwritten on update.
     To add project-specific extensions, use the "extensions" region below.
     ======================================================================== -->
---
name: investigate
description: Exploration and understanding phase. Use when task is vague, needs analysis, or requires understanding before action. Triggers on "why", "what is", "how does", "explain", "understand", "analyze", "investigate", "explore". NO CODE CHANGES in this phase.
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
- invar_sig, invar_map (perception)
- WebSearch, WebFetch (research)

## Entry Actions

### Context Refresh (DX-54)

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules section)
2. Display routing announcement

### Routing Announcement

```
📍 Routing: /investigate — [reason, e.g. "task is vague", "trigger 'why'"]
   Task: [user's request summary]
```

### Entry Steps

1. Display routing announcement (above)
2. Run `invar_map(top=10)` for codebase orientation
3. Explore relevant code and documentation

## Tool Selection

| I want to... | Use |
|--------------|-----|
| See function contracts | `invar_sig(target="<file>")` |
| Find entry points | `invar_map(top=10)` |
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
<!--/invar:skill--><!--invar:extensions-->
<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
<!-- Merge date: 2025-12-27 -->
<!-- ======================================== -->

## Claude Analysis (Preserved)

<!--invar:skill version="5.0"-->
<!-- ========================================================================
     SKILL REGION - DO NOT EDIT
     This section is managed by Invar and will be overwritten on update.
     To add project-specific extensions, use the "extensions" region below.
     ======================================================================== -->
---
name: investigate
description: Exploration and understanding phase. Use when task is vague, needs analysis, or requires understanding before action. Triggers on "why", "what is", "how does", "explain", "understand", "analyze", "investigate", "explore". NO CODE CHANGES in this phase.
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
- invar_sig, invar_map (perception)
- WebSearch, WebFetch (research)

## Entry Actions

### Context Refresh (DX-54)

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules section)
2. Display routing announcement

### Routing Announcement

```
📍 Routing: /investigate — [reason, e.g. "task is vague", "trigger 'why'"]
   Task: [user's request summary]
```

### Entry Steps

1. Display routing announcement (above)
2. Run `invar_map(top=10)` for codebase orientation
3. Explore relevant code and documentation

## Tool Selection

| I want to... | Use |
|--------------|-----|
| See function contracts | `invar_sig(target="<file>")` |
| Find entry points | `invar_map(top=10)` |
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
<!--/invar:skill-->

<!--invar:extensions-->
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Project-specific investigation checklists
     - Custom analysis tools or scripts
     - Domain-specific research sources
     - Team documentation references
     ======================================================================== -->
<!--/invar:extensions-->


<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->
<!--/invar:extensions-->
