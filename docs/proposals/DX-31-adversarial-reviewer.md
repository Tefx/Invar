# DX-31: Independent Adversarial Reviewer

> **"Fresh eyes find what invested minds miss."**

**Status:** Proposed
**Created:** 2024-12-24
**Relates to:** DX-30 (Visible Workflow), existing /review and /attack skills

## Problem

### The Self-Review Trap

When the same agent writes and reviews code:

```
Implementation Agent:
  "I'll handle edge case X this way..."
  "This contract covers the important cases..."
  "This escape hatch is justified because..."

Same Agent Reviewing:
  "Edge case X? I remember handling that." (didn't actually check)
  "Contract looks good." (wrote it, of course it looks good)
  "Escape hatch is fine." (I wrote the justification)
```

**Result:** Confirmation bias, author blindness, self-rationalization.

### Two Core Problems

| Problem | Description | Human Analogy |
|---------|-------------|---------------|
| **Collusion** | Same agent writes and reviews, unconsciously "forgives" own mistakes | Developer reviewing own PR |
| **Author Blindness** | Memory of implementation prevents seeing actual bugs | "I know what I meant" syndrome |

### Why Existing /review Doesn't Solve This

Current `/review` skill:
- Runs in same conversation context
- Has access to all prior discussion
- Knows the user's original intent
- Remembers implementation decisions

**This is like asking the author to review their own code with a different hat on.**

## Proposed Solution

### Independent Adversarial Reviewer

```
┌─────────────────────────────────────────────────────────────┐
│                     CONTEXT ISOLATION                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Implementation Agent          │    Review Agent            │
│  (Main Conversation)           │    (Fresh Context)         │
│                                │                            │
│  ✓ User's request              │    ✗ No user request       │
│  ✓ Design discussion           │    ✗ No discussion history │
│  ✓ Implementation rationale    │    ✗ No rationale          │
│  ✓ "Why I did it this way"     │    ✗ No justifications     │
│                                │                            │
│         Writes Code ──────────────→ Receives Code Only      │
│                                │                            │
│                                │    ✓ Code + Contracts      │
│                                │    ✓ Doctests              │
│                                │    ✓ Review Checklist      │
│                                │    ✓ Adversarial Mindset   │
│                                │                            │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

#### 1. Context Isolation

The reviewer must NOT see:
- Original user request (prevents "oh they wanted X, this does X, LGTM")
- Conversation history (prevents inheriting assumptions)
- Implementation explanations (prevents rationalization)
- Why decisions were made (forces fresh evaluation)

The reviewer ONLY sees:
- The code itself
- The contracts (@pre/@post)
- The doctests
- The INVAR protocol rules
- A structured review checklist

#### 2. Adversarial Framing

```python
REVIEWER_SYSTEM_PROMPT = """
You are an adversarial code reviewer. Your job is to FIND PROBLEMS.

Assume:
- The code has bugs until proven otherwise
- The contracts may be meaningless ceremony
- The implementer may have rationalized poor decisions
- Escape hatches may be abused

You are NOT here to:
- Validate that code works
- Confirm the implementer did a good job
- Be nice or diplomatic

You ARE here to:
- Find bugs, logic errors, edge cases
- Challenge whether contracts have semantic value
- Identify code smells and duplication
- Question every escape hatch
- Check if code matches contracts (not if code "seems right")

Your success is measured by problems found, not code approved.
"""
```

#### 3. Structured Review Checklist

```markdown
## Review Checklist

### A. Contract Semantic Value
□ Does @pre actually constrain inputs beyond type checking?
  - Bad: @pre(lambda x: isinstance(x, int))
  - Good: @pre(lambda x: x > 0 and x < MAX_VALUE)
□ Does @post verify meaningful output properties?
  - Bad: @post(lambda result: result is not None)
  - Good: @post(lambda result: len(result) == len(input))
□ Could someone implement correctly from contracts alone?
□ Are boundary conditions explicit in contracts?

### B. Doctest Coverage
□ Do doctests cover normal cases?
□ Do doctests cover boundary cases?
□ Do doctests cover error cases?
□ Are doctests testing behavior, not just syntax?

### C. Code Quality
□ Is there duplicated code that should be extracted?
□ Are there magic numbers/strings that should be constants?
□ Is naming consistent and clear?
□ Is complexity justified or should code be simplified?

### D. Escape Hatch Audit
□ For each @invar:allow:
  - Is the justification valid?
  - Could refactoring eliminate the need?
  - Is this a pattern (multiple similar escapes)?
□ Total escape count reasonable? (<3 per file)

### E. Logic Verification
□ Do contracts and code actually agree?
□ Are there paths that bypass contract checks?
□ Are there implicit assumptions not in contracts?
□ What happens with unexpected inputs?

### F. Architecture Compliance
□ Is Core/Shell separation correct?
□ Do Shell functions return Result?
□ Are entry points thin?
```

## Implementation

### Option A: Enhanced Sub-Agent (Recommended)

```python
# In main conversation, after implementation complete
async def request_independent_review(changed_files: list[str]) -> str:
    """
    Spawn independent reviewer with isolated context.
    """
    # Collect only the code, not the conversation
    code_context = []
    for file_path in changed_files:
        content = read_file(file_path)
        code_context.append(f"### {file_path}\n```python\n{content}\n```")

    review_prompt = f"""
{REVIEWER_SYSTEM_PROMPT}

## Code to Review

{chr(10).join(code_context)}

## Your Task

1. Go through each item in the Review Checklist
2. For each issue found, provide:
   - Location (file:line)
   - Severity (CRITICAL / MAJOR / MINOR / SUGGESTION)
   - Description
   - Suggested fix (if applicable)
3. Be thorough and adversarial
4. Do not assume good intent - verify everything
"""

    # Spawn fresh agent with NO conversation history
    result = await Task(
        prompt=review_prompt,
        subagent_type="general-purpose",
        # Key: This agent has fresh context, no history
    )

    return result
```

### Option B: Skill Enhancement

Enhance existing `/review` skill to:
1. Clear context before review
2. Use adversarial system prompt
3. Follow structured checklist
4. Output standardized report

```python
# .claude/skills/review/SKILL.md updates
"""
## Review Skill (DX-31 Enhanced)

This skill performs INDEPENDENT adversarial review.

### Context Isolation
Before reviewing, this skill:
1. Does NOT reference conversation history
2. Does NOT consider user's original intent
3. ONLY evaluates code against contracts and protocol

### Adversarial Mindset
The reviewer assumes code has problems and must be proven correct.
"""
```

## Agent-Native Triggering

### Design Principle: Review Should Be Automatic

> **"Agent-Native means the review process is NOT user-triggered."**

Traditional approach (rejected):
```
User: "/review"
Agent: Performs review
```

Agent-Native approach:
```
Agent: Completes implementation
Agent: Detects trigger condition → Automatically spawns review sub-agent
Agent: Incorporates findings → Reports to user
```

### Trigger Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVIEW TRIGGER LAYERS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 3: Task Completion Gate (Agent Protocol)                  │
│  ├─ Before marking task "complete", evaluate: need review?       │
│  ├─ If Guard suggested review → spawn sub-agent                  │
│  └─ Incorporate findings into completion report                  │
│                                                                  │
│  Layer 2: Guard Suggestions (INFO/WARNING)                       │
│  ├─ review_suggested: "New Core file, consider review"           │
│  ├─ review_suggested: "3+ escape hatches, review recommended"    │
│  └─ review_suggested: "100+ LOC changed, review recommended"     │
│                                                                  │
│  Layer 1: ICIDIV Workflow Integration                            │
│  ├─ VERIFY phase: Guard check + conditional review               │
│  └─ Complex tasks: review is mandatory part of VERIFY            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Trigger Conditions

| Condition | Level | Rationale |
|-----------|-------|-----------|
| New Core file created | INFO (suggest) | Core logic is critical |
| escape hatch count ≥ 3 | WARNING (strong suggest) | May be bypassing rules |
| Changes ≥ 100 LOC | INFO (suggest) | Large changes error-prone |
| Security-sensitive files | WARNING (strong suggest) | auth, crypto, secrets |
| New public API | INFO (suggest) | Interface design matters |

### Guard Integration

```python
# New rule in rules.py
def check_review_suggested(file_info: FileInfo) -> list[Violation]:
    """
    Suggest independent review when conditions warrant.

    INFO when:
    - New Core file with public functions
    - High escape hatch count (≥3)
    - Large file changes
    """
    suggestions = []

    if file_info.is_new and file_info.is_core:
        suggestions.append(Violation(
            rule="review_suggested",
            severity=Severity.INFO,
            message="New Core file - consider independent review",
            suggestion="Spawn review sub-agent before task completion"
        ))

    if file_info.escape_count >= 3:
        suggestions.append(Violation(
            rule="review_suggested",
            severity=Severity.WARNING,
            message=f"{file_info.escape_count} escape hatches - review recommended",
            suggestion="High escape count may indicate rule circumvention"
        ))

    return suggestions
```

### Agent Protocol (INVAR.md Addition)

```markdown
## Independent Review (DX-31)

When Guard outputs `review_suggested`:
1. Evaluate if review is appropriate for this task
2. If yes, spawn independent review sub-agent via Task tool
3. Pass ONLY the code to reviewer (no conversation history)
4. Incorporate review findings before marking task complete
5. Report both implementation and review results to user

The reviewer operates with adversarial mindset and isolated context.
```

### Workflow Example

```
Agent: Implementation complete. Running Guard...

$ invar guard --changed
src/core/new_auth.py
  ✓ All checks passed
  ℹ review_suggested: New Core file with 5 public functions
    → Consider independent review before completion

Agent: Guard suggests review for new Core file. Spawning independent reviewer...

[Task tool creates sub-agent with isolated context]
[Sub-agent reviews code adversarially]
[Sub-agent returns findings]

Agent: Review complete. Found 2 issues:
  1. MAJOR: Contract on validate_token lacks boundary check
  2. MINOR: Magic number 3600 should be named constant

Fixing issues before completion...
[Agent fixes issues]
[Re-runs Guard]

Agent: All issues addressed. Task complete.
```

## Legacy: User-Triggered Review

The `/review` command remains available for explicit user requests, but is now secondary to automatic triggering.

### Review Report Format

```markdown
# Independent Review Report

**Files Reviewed:** 3
**Issues Found:** 7 (2 CRITICAL, 3 MAJOR, 2 MINOR)

## CRITICAL Issues

### 1. Contract has no semantic value
**File:** src/core/auth.py:45
**Code:**
```python
@pre(lambda token: token is not None)  # Useless - type hint already enforces
def validate_token(token: str) -> dict:
```
**Problem:** Pre-condition only checks None, but parameter is typed as `str` (not `str | None`), so None is already impossible.
**Fix:** Add meaningful constraint: `@pre(lambda token: len(token) > 0 and '.' in token)`

### 2. Doctest doesn't test boundary
**File:** src/core/auth.py:50
**Problem:** Doctest only shows happy path, no test for empty string or malformed token.
**Fix:** Add boundary doctests.

## MAJOR Issues
...

## Summary

| Category | Issues |
|----------|--------|
| Contract Quality | 3 |
| Code Duplication | 1 |
| Escape Hatch | 2 |
| Logic Error | 1 |

**Recommendation:** Address CRITICAL issues before merge.
```

## Comparison with Alternatives

| Approach | Collusion Prevention | Author Blindness | Cost | Automation |
|----------|---------------------|------------------|------|------------|
| Same-agent /review | ❌ No | ❌ No | Low | Easy |
| **Independent sub-agent** | ✅ Yes | ✅ Yes | Medium | Medium |
| Human review | ✅ Yes | ✅ Yes | High | Manual |
| Guard rules only | N/A | N/A | Low | Full |

## Implementation Plan

### Phase 1: Guard Trigger Rule (Immediate)

- [ ] Add `review_suggested` rule to rules.py
- [ ] Trigger on: new Core file, high escape count, large changes
- [ ] Output as INFO (suggest) or WARNING (strong suggest)
- [ ] Add to rule_meta.py

**Effort:** 2-3 hours

### Phase 2: Agent Protocol Documentation (Immediate)

- [ ] Add "Independent Review" section to INVAR.md
- [ ] Document trigger conditions and response protocol
- [ ] Add workflow example to .invar/examples/
- [ ] Update CLAUDE.md with review guidance

**Effort:** 1-2 hours

### Phase 3: Review Sub-Agent Configuration (Short-term)

- [ ] Create adversarial reviewer prompt template
- [ ] Define structured review checklist format
- [ ] Document Task tool usage pattern for review
- [ ] Add report format specification

**Effort:** 2-3 hours

### Phase 4: Legacy Skill Update (Optional)

- [ ] Update /review skill with adversarial prompt
- [ ] Note: This is secondary to automatic triggering
- [ ] Kept for explicit user requests only

**Effort:** 1 hour

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Automatic review triggers | 0% | 80%+ of qualifying tasks |
| Bugs found in review | ~20% of PRs | 50%+ |
| Contract quality issues caught | Unknown | Track |
| False positive rate | N/A | <20% |
| User-triggered vs auto-triggered | 100% manual | <20% manual |

## Appendix: Adversarial vs Collaborative Review

```
Collaborative Review (Current /review):
  "Let me check if this looks good..."
  "The code seems to handle the requirements..."
  "I think this is correct because..."

Adversarial Review (DX-31):
  "Let me try to break this..."
  "What if this input is malformed?"
  "This contract claims X, but does the code actually guarantee X?"
  "Why should I believe this escape hatch is necessary?"
```

The difference is mindset: **verify vs falsify**.

## Related Work

- **DX-30**: Visible workflow - complementary; DX-30 shows ICIDIV phases, DX-31 adds review to VERIFY
- **Existing /review skill**: Legacy manual trigger, retained for explicit user requests
- **Existing /attack skill**: Security-focused adversary, narrower scope than DX-31
- **Guard rules**: Mechanical checks; DX-31 adds semantic review via LLM
- **Task tool**: Claude Code's sub-agent capability, enables context isolation

## Appendix: Agent-Native vs User-Triggered

```
User-Triggered (Traditional):
  - User remembers to invoke review
  - Review is optional extra step
  - Easy to skip when "in a hurry"
  - Knowledge of when to review required

Agent-Native (DX-31):
  - Guard detects conditions automatically
  - Agent evaluates and triggers review
  - Integrated into task completion flow
  - No user action required
  - Consistent quality without user vigilance
```

**Key insight:** The best review is one the user doesn't have to remember to request.
