# DX-31: Independent Adversarial Reviewer

> **"Fresh eyes find what invested minds miss."**

**Status:** ✅ Complete (5/6 phases implemented, Phase 2 extracted to DX-41)
**Created:** 2024-12-24
**Updated:** 2025-12-25
**Relates to:** DX-30 (Visible Workflow), existing /review and /attack skills

## Resolution

| Phase | Description | Resolution |
|-------|-------------|------------|
| Phase 1 | Context isolation design | ✅ Implemented |
| Phase 2 | Auto-trigger from Guard | → Extracted to **DX-41** |
| Phase 3 | Review checklist | ✅ Implemented |
| Phase 4 | Multi-round review cycle | ✅ Implemented |
| Phase 5 | Convergence criteria | ✅ Implemented |
| Phase 6 | /review skill integration | ✅ Implemented |

### ✅ Implemented

- Context isolation design (reviewer sees only code + contracts)
- Review checklist (26-item structured adversarial review)
- Multi-round review cycle (review → fix → re-review)
- Convergence criteria (severity-based exit)
- `/review` skill file in `.claude/skills/`

## Platform Support

| Platform | Feature | Status |
|----------|---------|--------|
| **Claude Code** | Full independent review (Task tool) | ✅ Supported |
| **Other Agents** | Guard `review_suggested` suggestions | ✅ Supported |
| **Other Agents** | Automatic sub-agent review | ⏳ Not yet implemented |

> **Note:** The full independent review feature with context isolation requires Claude Code's Task tool capability. Other AI coding assistants (Cursor, Windsurf, Copilot, etc.) currently only receive Guard suggestions indicating when review is recommended. Users can then manually trigger review or use external review tools.

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

> **Design Principle:** Only include items requiring semantic judgment. Mechanical checks (Guard, linters) are excluded.

```markdown
## Review Checklist (26 items)

### A. Contract Semantic Value
□ Does @pre constrain inputs beyond type checking?
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
□ Is duplicated code worth extracting?
□ Is naming consistent and clear?
□ Is complexity justified?

### D. Escape Hatch Audit
□ Is each @invar:allow justification valid?
□ Could refactoring eliminate the need?
□ Is there a pattern suggesting systematic issues?

### E. Logic Verification
□ Do contracts correctly capture intended behavior?
□ Are there paths that bypass contract checks?
□ Are there implicit assumptions not in contracts?
□ What happens with unexpected inputs?

### F. Security
□ Are inputs validated against security threats (injection, XSS)?
□ No hardcoded secrets (API keys, passwords, tokens)?
□ Are authentication/authorization checks correct?
□ Is sensitive data properly protected?

### G. Error Handling & Observability
□ Are exceptions caught at appropriate level?
□ Are error messages clear without leaking sensitive info?
□ Are critical operations logged for debugging?
□ Is there graceful degradation on failure?
```

**Excluded (covered by tools):**
- Magic numbers → Linters (pylint, ruff)
- Escape hatch count → Guard reports
- Core/Shell separation → Guard (forbidden_import, impure_call)
- Shell returns Result → Guard (shell_result)
- Entry point size → Guard (15-line limit)

## Implementation

### Claude Code: Task Tool Integration

> **Requires:** Claude Code with Task tool capability

```python
# In main conversation, after implementation complete
async def request_independent_review(changed_files: list[str]) -> str:
    """
    Spawn independent reviewer with isolated context.
    Claude Code only - uses Task tool for context isolation.
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

### Other Agents: Guard Suggestions Only

For agents without sub-agent capability (Cursor, Windsurf, Copilot, etc.):

1. **Guard outputs `review_suggested`** when conditions are met
2. **Agent or user sees the suggestion** in Guard output
3. **Manual action required** - user decides whether to:
   - Manually invoke `/review` skill (if available)
   - Use external code review tools
   - Request human review

```
$ invar guard --changed
src/core/new_auth.py
  ✓ All checks passed
  ℹ review_suggested: New Core file with 5 public functions
    → Consider independent review before completion
```

**Future work:** MCP-based review tool or CLI command may be added to support automatic review for other agents.

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
| Contract coverage < 50% | WARNING (strong suggest) | Very low coverage needs review (from DX-30) |

### Guard Integration

```python
# New rule in rules.py
def check_review_suggested(file_info: FileInfo) -> list[Violation]:
    """
    Suggest independent review when conditions warrant.

    INFO when:
    - New Core file with public functions
    - Large file changes

    WARNING when:
    - High escape hatch count (≥3)
    - Very low contract coverage (<50%) - from DX-30 Phase 3
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

    # DX-30 Phase 3: Low contract coverage triggers review
    if file_info.is_core and file_info.contract_ratio < 0.5:
        pct = int(file_info.contract_ratio * 100)
        suggestions.append(Violation(
            rule="review_suggested",
            severity=Severity.WARNING,
            message=f"Contract coverage {pct}% - review recommended",
            suggestion="Very low coverage may indicate incomplete contracts"
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

## Review Enforcement

> **"A review without enforcement is just ceremony."**

### Design Principle: Findings Must Be Addressed

Generating a review report is meaningless if Agent can ignore it. DX-31 requires:
1. Structured output (not prose) for tracking
2. Severity-based enforcement rules
3. Explicit resolution for each finding
4. Task completion blocked by unresolved CRITICAL issues

### Structured Output Format

```python
class ReviewFinding:
    id: int
    severity: Literal["CRITICAL", "MAJOR", "MINOR"]
    location: str  # file:line
    category: str  # contract_quality, code_smell, logic_error, etc.
    description: str
    suggestion: str | None

class ReviewReport:
    findings: list[ReviewFinding]
    files_reviewed: int
    critical_count: int
    major_count: int
    minor_count: int
```

### Severity-Based Enforcement

| Severity | Enforcement | Rule |
|----------|-------------|------|
| **CRITICAL** | Blocking | MUST fix before task completion |
| **MAJOR** | Strong | Fix OR provide written justification |
| **MINOR** | Advisory | Optional, can defer to follow-up |

### Resolution Tracking

Each finding must have explicit resolution:

```python
class IssueResolution:
    finding_id: int
    status: Literal["fixed", "deferred", "disputed"]
    justification: str | None  # Required for deferred/disputed

# Resolution rules:
# - CRITICAL: Cannot be "deferred", only "fixed" or "disputed" (with strong justification)
# - MAJOR: Can be "deferred" with justification
# - MINOR: Can be "deferred" without justification
```

### Task Completion Gate

```python
def can_complete_task(report: ReviewReport, resolutions: list[IssueResolution]) -> bool:
    """Task cannot complete with unresolved CRITICAL issues."""
    for finding in report.findings:
        if finding.severity == "CRITICAL":
            resolution = find_resolution(finding.id, resolutions)
            if not resolution:
                return False  # Unresolved CRITICAL
            if resolution.status == "deferred":
                return False  # CRITICAL cannot be deferred
            if resolution.status == "disputed" and not resolution.justification:
                return False  # Disputed needs justification
    return True
```

### Enforcement Workflow

```
Agent: Review complete. Findings:
  #1 CRITICAL: Contract lacks boundary check (auth.py:45)
  #2 MAJOR: Magic number 3600 (auth.py:78)
  #3 MINOR: Variable naming (auth.py:92)

Agent: Addressing findings...

[Fixes #1 - adds boundary check]
[Fixes #2 - extracts TOKEN_EXPIRY_SECONDS constant]

Agent: Resolution status:
  #1 CRITICAL: ✅ Fixed - boundary check added
  #2 MAJOR: ✅ Fixed - constant extracted
  #3 MINOR: ⏸ Deferred - will address in style cleanup PR

Agent: Checking completion gate...
  - CRITICAL issues: 1 fixed, 0 unresolved ✓
  - Can complete: YES

[Re-runs Guard to verify fixes]

Agent: Task complete.
  - Implementation: ✓
  - Review: ✓ (3 findings, 2 fixed, 1 deferred)
  - Guard: ✓
```

### What If Agent Disputes a Finding?

```
Agent: Resolution status:
  #1 CRITICAL: ❓ Disputed

  Justification: The reviewer flagged missing boundary check for token length,
  but the @pre contract delegates to jwt.decode() which handles this internally.
  Adding redundant check would violate DRY. The contract correctly documents
  the delegation: "@pre: token is valid JWT format (delegated to jwt library)"

Agent: Disputed finding submitted for user review.
User: [Reviews justification, accepts or requires fix]
```

### Why This Matters

Without enforcement:
```
Review: Found 5 issues
Agent: "Noted." [ignores] → Task "complete"
```

With enforcement:
```
Review: Found 5 issues (2 CRITICAL)
Agent: Cannot complete until CRITICAL resolved
Agent: [Fixes issues] → Resolution tracked → Task complete
```

**The review becomes a real quality gate, not a checkbox.**

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

| Approach | Collusion Prevention | Author Blindness | Cost | Automation | Platform |
|----------|---------------------|------------------|------|------------|----------|
| Same-agent /review | ❌ No | ❌ No | Low | Easy | All |
| **Independent sub-agent** | ✅ Yes | ✅ Yes | Medium | Medium | Claude Code only |
| Human review | ✅ Yes | ✅ Yes | High | Manual | All |
| Guard suggestions only | N/A | N/A | Low | Full | All |

> **Note:** The "Independent sub-agent" approach currently requires Claude Code. Other agents receive Guard suggestions but must rely on manual or external review.

## Implementation Plan

### Phase 1: Guard Trigger Rule (Immediate) ✅

- [x] Add `review_suggested` rule to rules.py
- [x] Trigger on: escape count >= 3, contract ratio < 50%, security-sensitive path
- [x] Output as WARNING (strong suggest)
- [x] Add to rule_meta.py

**Effort:** 2-3 hours
**Scope:** All agents (Guard-based)
**Implemented:** 2025-12-25 (see `src/invar/core/review_trigger.py`)

### Phase 2: Structured Review Format — 📋 Deferred

- [ ] Define ReviewFinding and ReviewReport schema
- [ ] Define IssueResolution schema with status tracking
- [ ] Create reviewer prompt that outputs structured format
- [ ] Programmatic task completion gate

**Status:** Deferred
**Rationale:** Current Prompt-Based Guidance (like Guard) is sufficient. Programmatic enforcement adds complexity without proven need. Revisit if agents frequently ignore CRITICAL findings.

**Effort:** 2-3 hours
**Scope:** All agents (Schema definition)

### Phase 3: Agent Protocol Documentation ✅

**Original scope reduced.** Enforcement rules and resolution tracking deferred with Phase 2.

- [x] Add Review Gate trigger conditions to INVAR.md (source)
- [x] Document trigger conditions and response protocol (in templates/INVAR.md, AGENTS.md)
- [x] Update CLAUDE.md with review guidance (Agent Roles, Review Modes)
- [x] Update templates/CLAUDE.md.template with Agent Roles section
- [x] Create docs/mechanisms/documentation.md (INVAR vs CLAUDE attribution)

**Deferred to Phase 2:**
- Document enforcement rules (CRITICAL = blocking)
- Add resolution tracking requirements

**Effort:** 1 hour (reduced)
**Scope:** All agents (Protocol)
**Implemented:** 2025-12-25

### Phase 4: Platform Limitation Documentation ✅

- [x] Update README.md with platform support matrix
- [x] Add "Platform Support" section to docs (README.md serves as main doc)
- [x] Document Claude Code requirement for full feature
- [x] Explain Guard-only fallback for other agents
- [x] Add note to PyPI package description (README.md is PyPI long description)

**Effort:** 1-2 hours
**Scope:** Documentation only
**Implemented:** 2025-12-25

### Phase 5: Claude Code Sub-Agent Configuration (Short-term) ✅

- [x] Create adversarial reviewer prompt template (`.claude/commands/review.md`)
- [x] Ensure output follows structured format (CRITICAL/MAJOR/MINOR with location)
- [x] Document Task tool usage pattern for review (Isolated Mode section)
- [x] Add enforcement workflow examples (Mode Detection flow)

**Effort:** 2-3 hours
**Scope:** Claude Code only
**Implemented:** 2025-12-25

### Phase 6: Legacy Skill Update (Optional) ✅

- [x] Update /review skill with adversarial prompt
- [x] Add Mode Detection (Isolated vs Quick based on `review_suggested`)
- [x] Create template for new projects (`src/invar/templates/commands/review.md`)
- [x] Integrate into `invar init` (copies to `.claude/commands/`)

**Effort:** 1 hour
**Scope:** Skill-compatible agents
**Implemented:** 2025-12-25

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Automatic review triggers | 0% | 80%+ of qualifying tasks |
| Bugs found in review | ~20% of PRs | 50%+ |
| Contract quality issues caught | Unknown | Track |
| False positive rate | N/A | <20% |
| User-triggered vs auto-triggered | 100% manual | <20% manual |
| **CRITICAL issues fixed** | N/A | 100% (enforced) |
| **MAJOR issues addressed** | N/A | 90%+ (fixed or justified) |
| Review findings ignored | Unknown | 0% for CRITICAL |

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
