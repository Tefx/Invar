# DX-42: Workflow Auto-Routing and Autonomous Orchestration

> **"Let the task choose the workflow, not the user."**

**Status:** Draft
**Created:** 2025-12-25
**Updated:** 2025-12-25
**Origin:** Extracted from DX-35 Phase 4, expanded with orchestration
**Effort:** Medium-High
**Risk:** Medium (misrouting risk)

## Problem Statement

### Problem 1: Users Cannot Invoke Skills Directly

**Critical Discovery:** Skills cannot be manually invoked by users.

```
User: /develop
System: "This slash command can only be invoked by Claude, not directly
        by users. Ask Claude to run /develop for you."
```

**Implication:** Agent accuracy in understanding user intent is CRITICAL. If the agent doesn't invoke the right workflow, the user has no direct recourse.

### Problem 2: Agent Routing Accuracy

Current state: Agent must infer which workflow to use from natural language.

| Scenario | Agent Behavior | Problem |
|----------|---------------|---------|
| "Add validation to X" | Often starts coding directly | Skips /develop workflow |
| "Make X faster" | Mixed - sometimes investigates | Inconsistent |
| "Should we use A or B?" | Usually proposes | ✅ Works |
| Complex multi-step task | No orchestration | User must guide each step |

### Problem 3: Simple Task Overhead

For simple tasks (3-5 minute implementation):

```
Current flow:
User: "Add input validation to parse_source"
Agent: [investigation] → "Recommend /develop" → wait
User: "proceed"  ← unnecessary
Agent: [development] → "Recommend /review" → wait
User: "proceed"  ← unnecessary
Agent: [review] → done

Ideal flow:
User: "Add input validation to parse_source"
Agent: [auto-orchestrate: investigate → develop → review] → done
```

## Proposed Solutions

### Part 1: Routing Heuristics

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
```

### Part 2: Mandatory Routing Announcement

Since users cannot invoke skills directly, the agent MUST announce its routing decision:

```
User: "Make the parser faster"

Agent: "📍 Routing: /investigate (task is vague)

        I'll first investigate to:
        1. Profile current performance
        2. Identify bottlenecks
        3. Report findings

        Type 'stop' to pause, or I'll proceed..."

        [Enters /investigate workflow]
```

**Key:** Always show routing decision before proceeding.

### Part 3: Complexity Assessment

```python
def assess_complexity(task: str, context: ProjectContext) -> Complexity:
    """
    Assess task complexity to determine orchestration level.

    Returns: Complexity.SIMPLE | Complexity.MODERATE | Complexity.COMPLEX
    """
    signals = {
        "simple": [
            len(estimated_files) <= 2,
            estimated_changes < 50,  # lines
            single_function_scope,
            no_architectural_decision,
        ],
        "complex": [
            len(estimated_files) > 5,
            requires_new_module,
            affects_public_api,
            security_sensitive,
            estimated_changes > 200,
        ]
    }

    if all(signals["simple"]):
        return Complexity.SIMPLE
    elif any(signals["complex"]):
        return Complexity.COMPLEX
    else:
        return Complexity.MODERATE
```

### Part 4: Autonomous Orchestration (Simple Tasks)

For SIMPLE complexity tasks, auto-orchestrate the full cycle:

```
📍 Routing: /develop (clear target: add validation to parse_source)
📊 Complexity: SIMPLE (1 file, ~20 lines)

🔄 Auto-orchestrating: investigate → develop → review

[Phase 1/3: Quick Investigation]
✓ Found parse_source at src/invar/core/parser.py:45
✓ Current: accepts any string
✓ Need: reject whitespace-only strings

[Phase 2/3: Development]
✓ Check-In: guard PASS
✓ Added @pre(lambda source: len(source.strip()) > 0)
✓ Added doctest for empty string
✓ Final: guard PASS

[Phase 3/3: Quick Review]
✓ Contract quality: meaningful constraint
✓ No issues found

📋 Summary:
- Modified: src/invar/core/parser.py
- Changes: +5 lines (contract, doctest)
- Status: Ready for commit
```

### Part 5: User Override Mechanisms

Since users can't invoke skills directly, provide explicit overrides:

| User Input | Effect |
|------------|--------|
| `!develop` | Force /develop workflow, skip routing |
| `!investigate` | Force /investigate |
| `!propose` | Force /propose |
| `stop` | Pause current workflow |
| `manual` | Disable auto-orchestration, ask at each step |

```
User: "!develop Add validation"

Agent: "📍 Override: /develop (user requested)
        Skipping routing heuristics..."
```

### Part 6: Orchestration Configuration

```toml
[tool.invar.workflow]
# Auto-routing
auto_route = true           # Enable routing heuristics
announce_routing = true     # Always show routing decision

# Auto-orchestration
auto_orchestrate = "simple" # "simple" | "all" | "none"
complexity_threshold = 3    # Max files for SIMPLE classification

# User control
allow_override = true       # Enable !develop, !investigate overrides
pause_between_phases = false # Ask before each phase transition
```

## Implementation Plan

| Phase | Feature | Effort | Priority |
|-------|---------|--------|----------|
| 1 | Routing heuristics + announcement | Medium | **High** |
| 2 | User override commands (!develop) | Low | **High** |
| 3 | Complexity assessment | Medium | Medium |
| 4 | Auto-orchestration for simple tasks | Medium | Medium |
| 5 | Configuration options | Low | Low |

### Phase 1: Core Routing (Priority)

Add to all skill entry points:

```markdown
## Entry (Updated for DX-42)

Before any workflow action:

1. **Announce routing decision:**
   ```
   📍 Routing: /[workflow] ([reason])
   ```

2. **Check for override:**
   - If user said `!develop`, skip routing
   - If user said `stop`, pause and ask

3. **Proceed with workflow**
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Misrouting loses user trust | Always announce, allow override |
| Auto-orchestration does wrong thing | Only for SIMPLE tasks, user can say 'stop' |
| Override syntax confusing | Clear documentation, consistent `!` prefix |
| Complex tasks misclassified as simple | Conservative thresholds, default to ask |

## Success Criteria

- [ ] 90%+ tasks routed correctly
- [ ] Clear routing announcements before every workflow
- [ ] Override mechanism (`!develop`) works
- [ ] Simple tasks auto-orchestrate without extra user input
- [ ] User can say 'stop' at any time

## Open Questions

1. Should `!develop` be the syntax, or something else like `force develop`?
2. Should auto-orchestration default to on or off?
3. How to handle mid-workflow complexity escalation?

## Related

- DX-35: Workflow-based Phase Separation (Phase 4 origin)
- DX-39: Workflow Efficiency (complementary improvements)
- DX-41: Automatic Review Orchestration (review-specific automation)
- Workflow skills: `.claude/skills/`
