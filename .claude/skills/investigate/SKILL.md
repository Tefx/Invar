---
name: investigate
description: Exploration and understanding phase. Use when task is vague, needs analysis, or requires understanding before action. Triggers on "why", "what is", "how does", "explain", "understand", "analyze", "investigate", "explore". NO CODE CHANGES in this phase.
_invar:
  version: "5.0"
  managed: skill
---
<!--invar:skill-->

# Investigation Mode

> **Purpose:** Understand before acting. Gather information, analyze code, report findings.

## Scope Boundaries

**This skill IS for:**
- Understanding vague or unclear tasks
- Analyzing existing code and architecture
- Researching before implementation
- Answering "why", "what", "how does" questions

**This skill is NOT for:**
- Writing or modifying code → switch to `/develop`
- Making design decisions → switch to `/propose`
- Reviewing code quality → switch to `/review`

**Drift detection:** If you find yourself wanting to edit files → STOP, exit to `/develop`.

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
| View document structure | `invar doc toc <file>` |
| Read document section | `invar doc read <file> <section>` |
| Search document sections | `invar doc find <pattern> <file>` |

## Long Document Handling (>500 lines)

When understanding long documents (PRD, Spec, Design docs):

### 1. Structure First

```bash
invar doc toc spec.md --format text
```

See the table of contents before reading content. Understand the document's organization.

### 2. Read On-Demand

```bash
invar doc read spec.md "requirements/auth"
```

Only read sections relevant to your task. Avoid full-document reads.

### 3. Track with TodoWrite

Create a todo item for each section you need to read:

```
□ Read: Introduction (context)
□ Read: Requirements/Auth (main task)
□ Read: API Design (reference)
□ Read: Security (constraints)
```

Mark each as completed after reading.

### 4. Maintain Running Summary

After reading each section, update a mental summary:

```
Key Points:
- Auth: JWT + refresh token (spec:48)
- Rate limit: 100 req/min (spec:120)
- Must support OAuth2 (spec:85)
```

Include line references for traceability.

### 5. Verify Coverage

Before concluding, check the TOC against your todos:
- Did you read all relevant sections?
- Any section titles suggest missed requirements?

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
