# Investigation Workflow

> **Purpose:** Understand before acting. No code changes in this phase.

## When to Use

- Vague or unclear tasks ("make it faster", "improve X")
- Questions: "why", "what is", "how does", "explain"
- Unfamiliar codebase or module
- Need to understand before proposing solutions

## Entry Actions

1. Announce: `Entering /investigate for: [topic]`
2. Run `invar_map --top 10` for orientation
3. Read `.invar/context.md` if relevant

## Allowed Tools

| Tool | Usage |
|------|-------|
| `invar sig <file>` | See contracts without reading implementation |
| `invar map --top N` | Find entry points by reference count |
| Read | Understand implementation when needed |
| Grep/Glob | Search for patterns |
| WebSearch | Research external topics |
| Task(Explore) | Deep codebase exploration |

## Constraints

**FORBIDDEN in this phase:**
- Edit, Write (no code changes)
- git commit (nothing to commit)
- Creating new files

**Focus:** Understanding, not solving.

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
- [ ] /propose - Design decision needed
- [ ] /develop - Ready to implement [specific task]
- [ ] More investigation - [what's still unclear]

**Next step?**
```

## Example

```
User: "Why is the parser slow?"

Agent: "Entering /investigate for: parser performance

[uses invar_map, invar_sig, reads relevant code]

### Investigation Complete

**Topic:** Parser performance analysis

**Findings:**
1. O(n^2) loop in parse_tokens (parser.py:145)
2. Redundant AST traversal in extract_symbols
3. No caching for repeated imports

**Recommendation:**
- [x] /propose - Multiple optimization strategies possible

**Next step?**"
```
