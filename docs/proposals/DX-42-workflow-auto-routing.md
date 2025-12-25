# DX-42: Workflow Auto-Routing

> **"Let the task choose the workflow, not the user."**

**Status:** Draft
**Created:** 2025-12-25
**Origin:** Extracted from DX-35 Phase 4
**Effort:** Medium
**Risk:** Medium (misrouting risk)

## Problem Statement

Current state: User must explicitly invoke workflows (`/develop`, `/investigate`, etc.)

**Issues:**
1. User may not know which workflow is appropriate
2. Vague tasks get sent to `/develop` when `/investigate` is needed
3. Decision-needed tasks start coding instead of proposing options

## Proposed Solution

Implement routing heuristics that analyze user input and select appropriate workflow.

### Routing Logic

```python
def route_task(user_input: str) -> tuple[str, str]:
    """
    Analyze user input and route to appropriate workflow.

    Returns: (workflow, reasoning)
    """
    input_lower = user_input.lower()

    # Decision patterns → /propose
    if any(p in input_lower for p in [
        "should we", "how should", "which",
        "compare", "vs", "or should",
        "design", "architect", "approach"
    ]):
        return "/propose", "Decision-making task detected"

    # Understanding patterns → /investigate
    if any(p in input_lower for p in [
        "why", "what is", "how does", "explain",
        "understand", "analyze", "investigate", "explore"
    ]):
        return "/investigate", "Understanding task detected"

    # Vague action patterns → /investigate first
    if is_vague_action(user_input):
        return "/investigate", "Task is vague, needs investigation first"

    # Clear action patterns → /develop
    if any(p in input_lower for p in [
        "add", "implement", "create", "fix", "update",
        "build", "write", "modify", "change", "remove"
    ]) and has_specific_target(user_input):
        return "/develop", "Clear actionable task detected"

    # Default to investigation for unclear tasks
    return "/investigate", "Default: investigate before acting"

def is_vague_action(input: str) -> bool:
    """Check if action is too vague for direct implementation."""
    vague_patterns = [
        "improve", "optimize", "make better", "refactor",
        "clean up", "fix issues", "handle errors"
    ]
    return any(p in input.lower() for p in vague_patterns)

def has_specific_target(input: str) -> bool:
    """Check if input mentions specific files, functions, or symbols."""
    # Look for file paths, function names, class names
    import re
    return bool(re.search(r'[\w/]+\.\w+|def \w+|class \w+|\w+\(\)', input))
```

### Routing Table

| Signal in User Input | Route To | Reasoning |
|---------------------|----------|-----------|
| Specific symbol names | /develop | Clear target |
| "Add/implement/fix X" (X specific) | /develop | Actionable |
| "Improve/optimize/refactor" (vague) | /investigate | Needs analysis |
| "Should we...?" "How should...?" | /propose | Decision needed |
| "Why...?" "What is...?" | /investigate | Understanding needed |
| "Compare A vs B" | /propose | Choice needed |

### Agent Announcement

**Critical:** Agent MUST announce routing decision.

```
User: "Make the parser faster"

Agent: "Routing: This task is vague → /investigate

        I'll first investigate to:
        1. Profile current performance
        2. Identify bottlenecks
        3. Report findings

        After investigation, I'll recommend next steps."
```

### Override Mechanism

```
User: "/develop!"    ← Force /develop, skip routing
User: "/investigate" ← Explicit workflow
```

## Implementation Plan

1. **Create routing module** — Implement heuristics
2. **Update skill entry** — Add routing check before workflow start
3. **Add announcements** — Always show routing decision
4. **Test with real tasks** — Validate heuristics

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Misrouting loses user trust | Always announce decision, allow override |
| Heuristics too aggressive | Start conservative, tune based on feedback |
| Complex tasks misclassified | Default to /investigate for unclear cases |

## Success Criteria

- [ ] 90%+ tasks routed correctly
- [ ] Clear routing announcements
- [ ] Override mechanism works
- [ ] Vague tasks go to /investigate

## Related

- DX-35: Workflow-based Phase Separation (Phase 4 origin)
- Workflow skills: `.claude/skills/`
