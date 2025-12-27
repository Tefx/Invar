# DX-58 Test Scenario: Critical Section Effectiveness

## Test Design

### Simulated Conversation Context

To test if an agent remembers critical rules after a long conversation, we simulate:
- 25 messages of development work
- Accumulated context of ~75,000 tokens
- Agent is now asked to "run tests"

### Token Budget Simulation

```
Messages 1-5 (Understanding):
- User: "Help me understand this codebase" (20 tokens)
- Agent: Explores files, explains structure (2000 tokens)
- Repeat 5x = ~10,000 tokens

Messages 6-15 (Implementation):
- User: "Implement feature X" (50 tokens)
- Agent: Writes code, explains (1500 tokens)
- Tool outputs (500 tokens)
- Repeat 10x = ~20,000 tokens

Messages 16-25 (Debugging/More work):
- User: "Fix this bug" / "Add more features" (30 tokens)
- Agent: Debugs, implements (1500 tokens)
- Tool outputs (500 tokens)
- Repeat 10x = ~20,000 tokens

Total: ~50,000 tokens of conversation history
```

### Test Question

After all this context, user says:
> "Run the tests to make sure everything works"

**Expected behavior:** Agent should use `invar_guard`
**Failure indicator:** Agent uses `pytest` directly

## Test A: Without Critical Section

CLAUDE.md structure (current):
```
# Project Development Guide

## Check-In (DX-54)
[...ceremonial content...]

## Final
[...ceremonial content...]

## Project Structure
[...structure info...]

## Quick Reference
| Zone | Requirements |
|------|-------------|
| Core | @pre/@post + doctests |
| Shell | Result[T, E] |

[...more content...]

## Commands
- invar_guard for verification
[...buried in middle...]
```

## Test B: With Critical Section

CLAUDE.md structure (proposed DX-58):
```
<!--invar:critical-->
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | `invar_guard` — NOT pytest |
| **Core** | @pre/@post + doctests, NO I/O |
| **Shell** | Result[T, E] |
| **Flow** | Specify → Build → Validate |

<!--/invar:critical-->

# Project Development Guide
[...rest of content...]
```

## Test C: With Hook Injection

At message 25, hook injects:
```
<system-reminder>
Session refresh (25 messages):
• Verify: invar_guard (NOT pytest)
• Core: @pre/@post + doctests, NO I/O
• Shell: Result[T, E] return type
• Flow: Specify → Build → Validate
</system-reminder>
```

## Measurement

For each test, record:
1. Does agent mention `invar_guard`?
2. Does agent attempt to use `pytest`?
3. Does agent acknowledge the tool preference?

---

## Test Results (2025-12-27)

### Phase 1: Pre-Compaction Tests (A-F)

| Test | Condition | Result | Notes |
|------|-----------|--------|-------|
| A | Current CLAUDE.md (buried rules) | ✅ Pass | Agent searched and found rules |
| B | Critical section at top | ✅ Pass | Agent used critical section |
| C | Hook injection only | ✅ Pass | System reminder effective |
| D | No Invar instructions | ⚠️ Pass* | Context leakage from MCP tools |
| E | Rules buried in noise | ✅ Pass | Agent still found rules |
| F | Critical + noise | ✅ Pass | Critical section prioritized |

**Test D Issue:** Agent mentioned `invar_guard` even without instructions because:
- Subagent inherits parent's MCP server config (Invar tools visible)
- Actual project context (.invar/ directory) exists
- This is **context leakage**, not true rule retention

### Phase 2: Post-Compaction Tests (G-I)

After conversation was compacted (summarized), additional tests:

| Test | Condition | Result | Notes |
|------|-----------|--------|-------|
| G | Minimal critical section only | ✅ Pass | Correctly chose `invar_guard` |
| H | Uncertainty simulation | ✅ Pass | Ran guard, showed workflow |
| I | Context decay simulation | ✅ Pass | Acknowledged DX-54 refresh mechanism |

**Key Insight from Test I:** Agent demonstrated awareness of uncertainty handling:
> "In a real extended conversation where context had decayed, the right approach is to:
> 1. Admit uncertainty
> 2. Re-check authoritative sources (CLAUDE.md, context.md)
> 3. Ask the user if still unclear rather than defaulting to pytest"

### Limitations Identified

1. **Simulated ≠ Real**: Describing "25 messages" doesn't create actual token pressure
2. **Subagents start fresh**: No accumulated context decay
3. **MCP tool visibility**: Test environment leaks project context

### Conclusions

1. **Critical section works**: When present, agents consistently use it
2. **Hook injection works**: `<system-reminder>` effectively refreshes rules
3. **Real-world validation needed**: Subagent tests cannot simulate true context decay
4. **Recommended validation method**: A/B deployment in actual long sessions

### Recommended Next Steps

1. Deploy DX-58 critical section to CLAUDE.md template
2. Implement DX-57 UserPromptSubmit hook for periodic refresh
3. Monitor real-world sessions for tool selection drift
4. Consider adding `invar_guard` reminder to compaction summary
