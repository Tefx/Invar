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

1. Announce: `Entering /investigate for: [topic]`
2. Run `invar_map(top=10)` for codebase orientation
3. Read `.invar/context.md` if relevant to topic

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
- Task(Explore) (deep exploration)

## Entry Actions

1. Announce: `Entering /investigate for: [topic]`
2. Run `invar_map(top=10)` for codebase orientation
3. Read `.invar/context.md` if relevant to topic

## Investigation Process

1. **Scope** — What exactly needs to be understood?
2. **Explore** — Use perception tools (sig, map) before reading full files
3. **Analyze** — Look for patterns, dependencies, edge cases
4. **Synthesize** — Connect findings into coherent understanding

## Tool Selection

| I want to... | Use |
|--------------|-----|
| See function contracts | `invar_sig <file>` |
| Find entry points | `invar_map --top 10` |
| Find symbol definition | Serena `find_symbol` |
| Find references | Serena `find_referencing_symbols` |
| Search code patterns | `Grep` with regex |
| Explore codebase | `Task(Explore)` |

## Exit Format

When investigation is complete, report:

```
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

## Examples

**Vague request → Investigation:**
```
User: "Make the parser faster"

Agent: "Entering /investigate for: parser performance

This task is vague. I'll investigate to understand:
1. Current parser performance characteristics
2. Where time is spent
3. Potential optimization opportunities

[uses invar_map, invar_sig, reads relevant code]

### Investigation Complete

**Topic:** Parser performance analysis

**Findings:**
1. parse_source has O(n²) complexity in token handling
2. No caching for repeated imports
3. AST traversal happens twice in extract_symbols

**Recommendation:**
- [x] /propose — Multiple optimization strategies possible

**Next step?**"
```

<!--/invar:extensions-->
