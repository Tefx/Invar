# DX-35: Workflow-based Phase Separation

> **"Human-directed phases, Agent-autonomous execution."**

**Status:** ✅ Complete (Phase 1-2 implemented, Phase 3-5 extracted)
**Created:** 2025-12-25
**Related:** DX-31 (Adversarial Reviewer), DX-33 (Verification Blind Spots), DX-34 (Review Cycle)

## Resolution

| Phase | Description | Resolution |
|-------|-------------|------------|
| Phase 1 | Documentation (modular INVAR.md) | ✅ Implemented |
| Phase 2 | Claude Code Skills (4 workflow skills) | ✅ Implemented |
| Phase 3 | Review Loop Integration | → Extracted to **DX-41** |
| Phase 4 | Auto-Routing | → Extracted to **DX-42** |
| Phase 5 | Tier 2 Support (Cursor, Windsurf) | → Extracted to **DX-43** |

### ✅ Implemented (Phase 1-2)

- Modular INVAR.md with `sections/` directory
- Simplified CLAUDE.md (~30 lines)
- 4 workflow skill files: `/investigate`, `/propose`, `/develop`, `/review`
- Workflow definitions with entry/exit criteria
- Check-In/Final markers in each skill

---

## Problem Statement

### Observed Issues

1. **Long Context Instruction Loss** — As conversation grows, early instructions get diluted
2. **Complex Workflow Non-compliance** — Agents struggle to follow multi-step processes
3. **Unclear Task Boundaries** — Agents don't know when to stop or transition

### Evidence

| Symptom | Cause |
|---------|-------|
| Agent forgets Check-In after 50+ turns | Instruction dilution |
| Agent skips review when `review_suggested` | Workflow non-compliance |
| Agent over-engineers simple fix | No clear task boundary |
| Agent starts coding on vague request | Missing investigation phase |

---

## Proposed Solution

### Core Design

**Four workflows with automatic routing and natural flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input                                │
│              "improve performance"                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                 ┌─────────────────┐
                 │  Auto-Routing   │
                 │  (Agent judges) │
                 └─────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ /investigate│   │  /propose   │   │  /develop   │
│ (understand)│   │  (decide)   │   │ (implement) │
└─────────────┘   └─────────────┘   └─────────────┘
         │                 │                 │
         └────────┬────────┘                 │
                  ▼                          ▼
         ┌─────────────┐            ┌─────────────┐
         │  /develop   │            │  /review    │
         │ (implement) │            │  (quality)  │
         └─────────────┘            └─────────────┘
                  │                          │
                  ▼                          │
         ┌─────────────┐                     │
         │  /review    │◄────────────────────┘
         │  (quality)  │
         └─────────────┘
```

### Workflow Definitions

#### 1. /investigate — Understanding Phase

| Aspect | Definition |
|--------|------------|
| **Purpose** | Understand problem, explore codebase, gather information |
| **Entry** | Vague task, "why" questions, unfamiliar area |
| **Exit** | Findings reported, understanding achieved |
| **Output** | Analysis report, findings summary |
| **Human Role** | Receive information, ask follow-ups |
| **Agent Autonomy** | High (free exploration) |
| **Duration** | Variable (until understood) |

**Example:**
```
User: "Why is the parser slow?"
Agent: [enters /investigate]
       [profiles code, reads implementation, analyzes complexity]
Agent: "Found 3 issues:
        1. O(n²) loop in parse_tokens (line 145)
        2. Redundant AST traversal in extract_symbols
        3. No caching for repeated imports
        Want me to propose solutions?"
```

#### 2. /propose — Decision Phase

| Aspect | Definition |
|--------|------------|
| **Purpose** | Present options, facilitate human decision |
| **Entry** | Design decision needed, multiple valid approaches |
| **Exit** | Human makes choice OR creates DX-XX document |
| **Output** | Options with trade-offs, recommendation |
| **Human Role** | Evaluate and choose |
| **Agent Autonomy** | Medium (bounded by options) |
| **Duration** | Until decision made |

**Example:**
```
User: "How should we cache the imports?"
Agent: [enters /propose]
       [analyzes options, evaluates trade-offs]
Agent: "3 options:
        A: LRU cache (simple, memory-bounded) ← Recommended
        B: File-based cache (persistent, slower)
        C: Lazy loading (complex, best performance)

        Trade-offs: [table]
        Which approach?"
User: "A"
Agent: "Noted. Ready to implement with /develop."
```

#### 3. /develop — Implementation Phase

| Aspect | Definition |
|--------|------------|
| **Purpose** | Implement solution following USBV |
| **Entry** | Clear, actionable task |
| **Exit** | Guard PASS, all todos completed |
| **Output** | Working code, commits |
| **Human Role** | Minimal (until review) |
| **Agent Autonomy** | High within USBV framework |
| **Duration** | 1-4 hours (task batch) |

**Internal Flow:**
```
/develop
    │
    ├── Check-In (guard + map)
    │
    ├── UNDERSTAND
    │   └── Read context.md, explore relevant code
    │
    ├── SPECIFY
    │   └── Write contracts, design decomposition
    │
    ├── BUILD
    │   ├── [Complex task?] → Plan Mode → User approval
    │   └── Implement, incremental commits
    │
    ├── VALIDATE
    │   └── Guard PASS (full verification)
    │
    └── Final
        └── "Development complete. /review recommended."
```

**Task Batching:**
```
User: "Implement caching for A, B, C"
Agent: [creates TodoWrite with 3 items]
       [executes each, Guard between tasks, commit after each]
       [total ~2-3 hours autonomous work]
```

#### 4. /review — Quality Phase

| Aspect | Definition |
|--------|------------|
| **Purpose** | Adversarial review, find issues human/Guard missed |
| **Entry** | Development complete OR `review_suggested` triggered |
| **Exit** | Convergence (DX-34 criteria) |
| **Output** | Review report, fixes applied |
| **Human Role** | Minimal (review final report) |
| **Agent Autonomy** | High (isolated sub-agent) |
| **Duration** | 1-3 rounds, ~30-60 min total |

**Review-Fix Loop (from DX-34):**
```
/review
    │
    ├── Spawn isolated sub-agent (fresh context)
    │
    ├── Round 1: Review
    │   └── Find issues, categorize by severity
    │
    ├── Fix CRITICAL + MAJOR issues
    │
    ├── Round 2: Re-review (if needed)
    │   └── Check fixes, find new issues
    │
    ├── Convergence check:
    │   ├── No CRITICAL/MAJOR → Exit
    │   ├── Round >= 3 → Exit
    │   └── No improvement → Exit
    │
    └── Report: remaining MINOR issues for backlog
```

**Convergence Criteria:**
```python
def should_exit_review_cycle(round: int, current: ReviewResult, previous: ReviewResult | None) -> bool:
    if round >= 3:
        return True  # Hard limit
    if current.critical == 0 and current.major == 0:
        return True  # Quality target met
    if previous and current.total >= previous.total:
        return True  # No improvement
    return False
```

---

## Automatic Routing

### Routing Heuristics

| Signal in User Input | Route To | Reason |
|---------------------|----------|--------|
| Specific symbol names | /develop | Clear target |
| "Add/implement/fix X" (X clear) | /develop | Actionable |
| "Improve/optimize/refactor" (vague) | /investigate | Needs analysis |
| "Should we...?" "How should...?" | /propose | Decision needed |
| "Why...?" "What is...?" | /investigate | Understanding needed |
| "Compare A vs B" | /propose | Choice needed |
| After /develop completes | /review | Quality gate |

### Agent Announcement

**Critical:** Agent MUST announce which workflow it's entering.

```
User: "Make the parser faster"

Agent: "This task is vague. Entering /investigate to:
        1. Profile current performance
        2. Identify bottlenecks
        3. Report findings

        After investigation, I'll recommend next steps."
```

### Natural Flow Transitions

Workflows can suggest transitions:

| From | To | Trigger |
|------|----|---------|
| /investigate | /propose | "Found issues. Want solutions?" |
| /investigate | /develop | "Issue is clear. Ready to fix?" |
| /propose | /develop | "Option chosen. Ready to implement?" |
| /develop | /review | "Guard PASS. Review recommended." |
| /review | /develop | "Issues found. Fixes needed." |

---

## Instruction Re-injection

### The Problem

Long conversations dilute early instructions. After 100+ turns, the agent may forget:
- Check-In requirement
- Tool preferences (invar vs grep)
- Project-specific rules

### The Solution

Each workflow re-injects relevant instructions at entry.

**Workflow Entry Template:**
```markdown
## [Workflow Name] Active

### Phase-Specific Instructions
[Relevant subset of INVAR.md]

### Success Criteria
[Clear exit conditions]

### Tools for This Phase
[Phase-relevant tool guidance]
```

### What Each Workflow Injects

| Workflow | Injects |
|----------|---------|
| /investigate | Exploration tools, no-edit rule |
| /propose | Proposal format, decision facilitation |
| /develop | USBV flow, Guard usage, commit rules |
| /review | DX-31 review protocol, severity definitions |

---

## Time Granularity

### Autonomous Work Durations

| Workflow | Typical Duration | Max Recommended |
|----------|------------------|-----------------|
| /investigate | 15-60 min | 2 hours |
| /propose | 10-30 min | 1 hour |
| /develop | 1-3 hours | 4 hours (with task batching) |
| /review | 30-60 min | 90 min (3 rounds max) |

### Self-Management Mechanisms

Within long autonomous phases, agent uses:

1. **TodoWrite** — Persistent task tracking
2. **Guard runs** — Natural checkpoints between tasks
3. **Commits** — Rollback points after each sub-task
4. **Phase transitions** — USBV stages refresh context

### User Intervention Points

| Point | User Action |
|-------|-------------|
| Workflow entry | Confirm or redirect |
| Workflow transition | Approve next phase |
| /propose options | Make choice |
| /review report | Accept or request changes |

---

## Platform Tiering

### Support Levels

| Tier | Platform | Capabilities |
|------|----------|--------------|
| **Tier 1** | Claude Code | Full (skills, sub-agents, MCP) |
| **Tier 2** | Cursor/Windsurf | Baseline (rules file, manual workflow) |
| **Tier 3** | Others | Protocol only (INVAR.md) |

### Tier 1: Claude Code

**Implementation:** Skills + Sub-agents

```
.claude/skills/
├── investigate/SKILL.md
├── propose/SKILL.md
├── develop/SKILL.md
└── review/SKILL.md
```

**Features:**
- Automatic workflow routing
- Instruction re-injection via skills
- Isolated review via sub-agent (Task tool)
- MCP tools (invar_guard, invar_sig, invar_map)

### Tier 2: Cursor/Windsurf

**Implementation:** Rules file + Manual workflow

```
.cursorrules or .windsurfrules
```

**Features:**
- INVAR.md protocol (manual compliance)
- CLI tools (invar guard, invar sig, invar map)
- Manual workflow transitions
- No skill automation
- No isolated sub-agents

### Tier 3: Others

**Implementation:** INVAR.md only

**Features:**
- Protocol reference (USBV, contracts)
- Can use CLI if installed
- Fully manual workflow

---

## Document Restructuring

### INVAR.md — Protocol Reference (Modular)

```markdown
# INVAR.md

## Core Principles (Always loaded, ~30 lines)
- Philosophy
- Check-In/Final
- Basic rules

## Workflow: Investigation (Loaded by /investigate)
- Exploration guidelines
- Tool selection
- No-edit rule

## Workflow: Proposal (Loaded by /propose)
- Proposal format
- Trade-off analysis
- Decision facilitation

## Workflow: Development (Loaded by /develop)
- USBV detailed flow
- Guard usage
- Commit protocol

## Workflow: Review (Loaded by /review)
- DX-31 protocol
- Severity definitions
- Convergence criteria

## Rules Reference (On demand)
- Complete rule explanations
```

### CLAUDE.md — Project Configuration (Brief)

```markdown
# CLAUDE.md

## Check-In (~5 lines)
## Project Structure (~10 lines)
## Project-Specific Rules (as needed)
## Dependencies (as needed)
```

### Skill Files — Workflow Triggers

Each skill file:
1. Announces workflow entry
2. Re-injects relevant INVAR.md section
3. Sets success criteria
4. Provides phase-specific tool guidance

---

## Concrete Skill Implementations

### /investigate Skill

**File:** `.claude/skills/investigate/SKILL.md`

```markdown
---
name: investigate
description: Exploration and understanding phase - no code changes
---

# Investigation Mode Active

## Purpose
Understand the problem, explore the codebase, gather information.
**NO CODE CHANGES in this phase.**

## Entry Actions
1. Announce: "Entering /investigate for: [topic]"
2. Run `invar_map(top=10)` for orientation
3. Read `.invar/context.md` if relevant

## Allowed Tools
| Tool | Usage |
|------|-------|
| invar_sig | Understand function signatures and contracts |
| invar_map | Find entry points and hot spots |
| Read | Read files for understanding |
| Grep/Glob | Search for patterns |
| WebSearch | Research external topics |
| Task(Explore) | Deep codebase exploration |

## Forbidden Actions
- Edit, Write (no code changes)
- git commit (nothing to commit)
- Creating new files

## Exit Conditions
Report findings in this format:

### Investigation Complete

**Topic:** [what was investigated]

**Findings:**
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

**Recommendation:**
- [ ] /propose - if design decision needed
- [ ] /develop - if ready to implement
- [ ] More investigation - if unclear

**Next step?**
```

### /propose Skill

**File:** `.claude/skills/propose/SKILL.md`

```markdown
---
name: propose
description: Decision phase - present options for human choice
---

# Proposal Mode Active

## Purpose
Analyze options and facilitate human decision-making.
Output: Structured options with trade-offs and recommendation.

## Entry Actions
1. Announce: "Entering /propose for: [decision topic]"
2. Explore relevant context if needed

## Output Format

For quick decisions (< 3 options, simple trade-offs):

### Decision: [Topic]

| Option | Pros | Cons |
|--------|------|------|
| A: [name] | ... | ... |
| B: [name] | ... | ... |

**Recommendation:** [A/B] because [reason]

**Your choice?**

---

For complex decisions (formal proposal):

Create `docs/proposals/DX-XX-[topic].md`:

```
# DX-XX: [Title]

**Status:** Discussion
**Created:** [date]

## Problem Statement
[What needs to be decided]

## Options

### Option A: [Name]
- Description
- Pros
- Cons
- Effort estimate (Low/Medium/High)

### Option B: [Name]
...

## Recommendation
[Which option and why]

## Open Questions
[What needs clarification]
```

## Exit Conditions
- Human makes choice → Ready for /develop
- Human requests more info → Back to /investigate
- Human approves proposal document → Document created
```

### /develop Skill

**File:** `.claude/skills/develop/SKILL.md`

```markdown
---
name: develop
description: Implementation phase following USBV workflow
---

# Development Mode Active

## Entry Actions (REQUIRED)

### Check-In
```
invar_guard(changed=true)
invar_map(top=10)
```

Display:
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

## USBV Workflow

### 1. UNDERSTAND
- Read relevant code with `invar_sig`
- Understand existing patterns
- Identify affected areas

### 2. SPECIFY
- Write @pre/@post contracts FIRST
- Add doctests for expected behavior
- Design decomposition if complex

### 3. BUILD
**For complex tasks:** Enter Plan Mode, get user approval

**For all tasks:**
- Implement following contracts
- Run `invar_guard(changed=true)` frequently
- Commit after each logical unit:
  ```
  git add . && git commit -m "feat: [description]

  🤖 Generated with Claude Code
  Co-Authored-By: Claude <noreply@anthropic.com>"
  ```

### 4. VALIDATE
- Run `invar_guard()` (full verification)
- All tests pass
- All todos complete

## Task Batching

For multiple tasks:
1. Create TodoWrite with all items
2. Execute sequentially
3. Run Guard between each task
4. Commit after each task
5. Max batch: 5 tasks or 4 hours

## Exit Actions (REQUIRED)

### Final
```
invar_guard()
```

Display:
```
✓ Final: guard [PASS/FAIL] | [summary]
```

If Guard reports `review_suggested`:
```
⚠ Review suggested. Run /review for quality check.
```

## Failure Handling

If Guard fails:
1. Report specific failures
2. Attempt fix (max 2 attempts)
3. If still failing: Ask user or suggest /investigate
```

### /review Skill

**File:** `.claude/skills/review/SKILL.md`

```markdown
---
name: review
description: Adversarial code review with fix loop
---

# Review Mode Active

## Mode Selection

Check Guard output for `review_suggested`:
- If triggered OR `--isolated` flag: **Isolated Mode** (spawn sub-agent)
- Otherwise: **Quick Mode** (same context)

## Isolated Mode (Sub-Agent)

Spawn with Task tool:
```
Task(
  subagent_type="general-purpose",
  prompt="""
  You are an ADVERSARIAL CODE REVIEWER. Your job is to find problems.

  ## Context
  - Project: [project name]
  - Changed files: [list]
  - Recent commits: [list]

  ## Review Focus
  1. Contract quality (not just presence)
  2. Boundary conditions
  3. Error handling
  4. Security considerations
  5. Dead code / logic errors

  ## Severity Definitions
  - CRITICAL: Security vulnerability, data loss risk, crash
  - MAJOR: Logic error, missing validation, poor contracts
  - MINOR: Style, documentation, minor improvements

  ## Output Format
  ### Review Round [N]

  #### CRITICAL
  - [ ] [file:line] [description]

  #### MAJOR
  - [ ] [file:line] [description]

  #### MINOR
  - [ ] [file:line] [description]

  #### Summary
  - Critical: N
  - Major: N
  - Minor: N

  Be adversarial. Challenge assumptions. Find what Guard missed.
  """
)
```

## Review-Fix Loop

```
Round 1: Review
    │
    ├── Issues found?
    │   ├── NO → Exit, report clean
    │   └── YES ↓
    │
    ├── Fix CRITICAL + MAJOR
    │   (MINOR → backlog)
    │
Round 2: Re-review
    │
    ├── Convergence check:
    │   ├── No CRITICAL/MAJOR → Exit ✓
    │   ├── No improvement → Exit (warn)
    │   └── Round >= 3 → Exit (max reached)
    │
    └── Continue if needed
```

## Convergence Criteria

```python
def should_exit(round: int, current: Issues, previous: Issues | None) -> tuple[bool, str]:
    if round >= 3:
        return True, "max_rounds"
    if current.critical == 0 and current.major == 0:
        return True, "quality_met"
    if previous and current.total >= previous.total:
        return True, "no_improvement"
    return False, "continue"
```

## Exit Report

### Review Complete

**Rounds:** [N]
**Exit reason:** [quality_met / max_rounds / no_improvement]

**Fixed:**
- [list of fixed issues]

**Remaining (MINOR - backlog):**
- [list of minor issues]

**Ready for:** [next action]
```

---

## Automatic Routing Logic

### Pattern Matching Rules

```python
ROUTING_PATTERNS = {
    # /develop patterns - clear, actionable
    "develop": [
        r"^(add|implement|create|write|build)\s+.+",  # "add login button"
        r"^fix\s+(the\s+)?(bug|error|issue)\s+in\s+.+",  # "fix the bug in parser"
        r"^(update|change|modify)\s+\w+\s+(to|in)\s+.+",  # "update config to..."
        r"specific symbol mentioned AND action verb",
    ],

    # /investigate patterns - understanding needed
    "investigate": [
        r"^why\s+(does|is|are|do)\s+.+",  # "why is it slow"
        r"^what\s+(is|are|does)\s+.+",  # "what is this function"
        r"^how\s+does\s+.+work",  # "how does auth work"
        r"^(explain|understand|analyze)\s+.+",  # "explain the parser"
        r"vague verbs: improve, optimize, refactor (without specific target)",
    ],

    # /propose patterns - decision needed
    "propose": [
        r"^(should\s+we|how\s+should)\s+.+",  # "should we use Redis"
        r"^(compare|which|choose)\s+.+",  # "compare A vs B"
        r"^(design|architect|plan)\s+.+",  # "design the caching layer"
        r"explicit OR: A or B?",
    ],
}
```

### Decision Tree

```
User input received
         │
         ▼
┌─────────────────────────────────────┐
│ Contains specific symbol + action?  │
│ (e.g., "fix parse_source function") │
└─────────────────────────────────────┘
         │
    YES  │  NO
         │   │
    ┌────┘   └────┐
    ▼             ▼
/develop    ┌─────────────────────────────────────┐
            │ Question word? (why/what/how does)  │
            └─────────────────────────────────────┘
                      │
                 YES  │  NO
                      │   │
                 ┌────┘   └────┐
                 ▼             ▼
           /investigate  ┌─────────────────────────────────────┐
                         │ Decision word? (should/which/compare)│
                         └─────────────────────────────────────┘
                                   │
                              YES  │  NO
                                   │   │
                              ┌────┘   └────┐
                              ▼             ▼
                         /propose    ┌─────────────────────────────────────┐
                                     │ Vague verb? (improve/optimize)      │
                                     └─────────────────────────────────────┘
                                               │
                                          YES  │  NO
                                               │   │
                                          ┌────┘   └────┐
                                          ▼             ▼
                                    /investigate    /develop
                                                   (default)
```

### Announcement Template

```
Agent response to vague input "make the parser faster":

"Task analysis:
- Target: parser (identified)
- Action: 'faster' (vague - what metric? what's slow?)
- Clarity: LOW

Entering /investigate to:
1. Profile current parser performance
2. Identify specific bottlenecks
3. Measure baseline metrics

After investigation, I'll report findings and suggest next steps.

---
[begins investigation]"
```

---

## Integration with Existing Features

### Plan Mode

Plan Mode is a tool WITHIN /develop, not a separate workflow.

```
/develop
    │
    ├── Simple task → Direct implementation
    │
    └── Complex task → Enter Plan Mode
                           │
                           ├── Explore codebase
                           ├── Design approach
                           ├── User approval
                           └── Exit Plan Mode → Continue /develop
```

### Guard Integration

| Workflow | Guard Usage |
|----------|-------------|
| /investigate | `invar map` for orientation |
| /propose | None (no code changes) |
| /develop | Full guard at VALIDATE, between tasks |
| /review | Guard triggers `review_suggested` |

### Review Triggers (from DX-31)

Guard output `review_suggested` when:
- `escape_hatches >= 3`
- `contract_ratio < 50%`
- Security-sensitive path detected

This automatically suggests /review after /develop.

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Instruction compliance | > 90% | Check-In/Final present |
| Workflow completion | > 95% | Reach defined exit state |
| Autonomous duration | 2-4 hours | Time without intervention |
| Review convergence | < 3 rounds avg | Mean rounds to quality target |
| User satisfaction | Qualitative | Reduced friction, clear progress |

---

## Implementation Roadmap

### Phase 1: Documentation (Week 1)

- [ ] Restructure INVAR.md into modular sections
- [ ] Simplify CLAUDE.md to essentials
- [ ] Document workflow definitions

### Phase 2: Claude Code Skills (Week 2)

- [ ] Create skill files for each workflow
- [ ] Implement instruction re-injection
- [ ] Test workflow transitions

### Phase 3: Review Loop Integration (Week 3)

- [ ] Integrate DX-34 convergence criteria
- [ ] Implement isolated sub-agent for /review
- [ ] Test multi-round review cycle

### Phase 4: Auto-Routing (Week 4)

- [ ] Implement routing heuristics
- [ ] Add workflow announcement
- [ ] Test with various task types

### Phase 5: Tier 2 Support (Optional)

- [ ] Create .cursorrules template
- [ ] Document manual workflow for Tier 2
- [ ] Test with Cursor

---

## Open Questions — Resolved

### Q1: Workflow Override

**Question:** Should user be able to force a specific workflow?

**Answer: Yes, with explicit syntax.**

| Syntax | Behavior |
|--------|----------|
| `/develop` | Normal routing (may redirect to /investigate if vague) |
| `/develop!` | Force /develop, skip routing analysis |
| `develop: [task]` | Explicit workflow prefix |

**Rationale:** User knows best sometimes. Override should be explicit (!) to avoid accidental misrouting.

**Implementation:**
```python
def parse_command(input: str) -> tuple[str, str, bool]:
    """Returns (workflow, task, is_forced)."""
    if input.startswith("/"):
        parts = input[1:].split(" ", 1)
        cmd = parts[0]
        task = parts[1] if len(parts) > 1 else ""
        forced = cmd.endswith("!")
        workflow = cmd.rstrip("!")
        return workflow, task, forced
    return None, input, False  # No explicit workflow
```

---

### Q2: Mid-Workflow Switch

**Question:** What if user wants to switch workflows mid-stream?

**Answer: Allow with state preservation.**

**Scenario:**
```
User: [in /develop, implementing feature]
User: "wait, should we use approach B instead?"
Agent: "Pausing /develop. Current state:
        - Task: [description]
        - Progress: 2/5 todos complete
        - Uncommitted changes: 3 files

        Entering /propose for: approach A vs B

        [presents options]"
```

**Rules:**
1. **Save state** before switching (TodoWrite, uncommitted changes noted)
2. **Announce** the switch explicitly
3. **Resume** is possible: "continue /develop" restores context
4. **Discard** is possible: "cancel /develop" abandons (with confirmation if uncommitted changes)

**Implementation:**
```python
@dataclass
class WorkflowState:
    workflow: str
    task: str
    todos: list[Todo]
    uncommitted_files: list[str]
    started_at: datetime

# Store in conversation context
suspended_workflows: list[WorkflowState] = []
```

---

### Q3: Batch Limits

**Question:** How many tasks in one /develop batch?

**Answer: 5 tasks OR 4 hours OR Guard failure, whichever first.**

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max tasks | 5 | Cognitive load, error accumulation |
| Max duration | 4 hours | Context degradation |
| Hard stop | Guard failure | Don't proceed with broken code |

**Batch Execution Rules:**
1. Create TodoWrite with all tasks upfront
2. Execute sequentially (not parallel)
3. After each task:
   - Commit changes
   - Run `invar_guard(changed=true)`
   - Update TodoWrite
4. If Guard fails:
   - Stop batch
   - Report which task failed
   - Ask: fix and continue, or abort batch?

**Example:**
```
User: "Implement A, B, C, D, E"
Agent: "5 tasks received. Estimated 2-3 hours.

        Todo:
        1. [ ] Implement A
        2. [ ] Implement B
        3. [ ] Implement C
        4. [ ] Implement D
        5. [ ] Implement E

        Starting with task 1..."

[After task 3, Guard fails]

Agent: "Task 3 (Implement C) completed but Guard failed:
        - Error: missing_contract in new function

        Options:
        A: Fix and continue batch
        B: Abort batch, keep completed work
        C: Investigate failure

        Choice?"
```

---

### Q4: Failure Handling

**Question:** What if /develop fails (Guard doesn't pass)?

**Answer: Graduated response based on failure type and attempts.**

**Failure Types:**

| Type | Response |
|------|----------|
| Static analysis (fixable) | Auto-fix, retry (max 2) |
| Test failure | Report, ask user |
| Contract violation | Report, suggest /investigate |
| Unknown error | Report, ask user |

**Graduated Response:**

```
Attempt 1: Guard fails
    │
    ├── Fixable? (missing contract, style issue)
    │   └── Auto-fix → Attempt 2
    │
    └── Not fixable? (test failure, logic error)
        └── Report to user

Attempt 2: Guard still fails
    │
    ├── Same issue?
    │   └── Report: "Cannot auto-fix. Options: manual fix, /investigate, abort"
    │
    └── Different issue?
        └── Report: "Fixed previous, new issue found: [details]"

Max 2 auto-fix attempts, then human decision required.
```

**Example Interaction:**
```
Agent: "Guard failed after implementing feature:

        FAIL: tests/test_parser.py::test_edge_case
              Expected: None
              Got: ParseError

        This is a test failure (not auto-fixable).

        Options:
        A: I'll investigate the test failure
        B: Skip this task, continue batch
        C: Abort /develop, enter /investigate

        Choice?"
```

---

### Q5: Workflow Timeout (New)

**Question:** What if a workflow takes too long?

**Answer: Soft warning at 75% of max, hard stop at max.**

| Workflow | Max Duration | 75% Warning |
|----------|--------------|-------------|
| /investigate | 2 hours | 90 min |
| /propose | 1 hour | 45 min |
| /develop | 4 hours | 3 hours |
| /review | 90 min | ~65 min |

**Warning Message:**
```
⏱ Time check: /develop has been running for 3 hours.
   Remaining estimate: [based on TodoWrite progress]

   Options:
   A: Continue (1 hour max remaining)
   B: Wrap up current task and exit
   C: Checkpoint and pause for later

   Choice? (auto-continue in 2 minutes if no response)
```

**Hard Stop:**
```
⏱ /develop reached 4-hour limit.

   Completed: 4/5 tasks
   Current task: [description] - 80% complete

   Saving state for resume. Run '/develop --resume' to continue.
```

---

### Q6: Review Loop Stall (New)

**Question:** What if review finds the same issues repeatedly?

**Answer: Detect stall, escalate to human.**

**Stall Detection:**
```python
def detect_stall(rounds: list[ReviewResult]) -> bool:
    if len(rounds) < 2:
        return False

    current = rounds[-1]
    previous = rounds[-2]

    # Same issues reappearing
    current_ids = {(i.file, i.line, i.type) for i in current.issues}
    previous_ids = {(i.file, i.line, i.type) for i in previous.issues}

    overlap = current_ids & previous_ids
    if len(overlap) > len(current_ids) * 0.5:  # >50% same issues
        return True

    return False
```

**Stall Response:**
```
⚠ Review cycle stalled.

Round 2 found same issues as Round 1:
- [file:line] [description] (unfixed)
- [file:line] [description] (unfixed)

Possible causes:
1. Fixes introduced new problems
2. Issues are false positives
3. Issues require design change

Options:
A: Mark as false positives and exit
B: Enter /investigate to understand root cause
C: Continue review (round 3, last chance)

Choice?
```

---

## Summary

DX-35 introduces workflow-based phase separation to address instruction loss and workflow non-compliance:

| Workflow | Purpose | Exit Condition |
|----------|---------|----------------|
| /investigate | Understand | Findings reported |
| /propose | Decide | Human chooses option |
| /develop | Implement | Guard PASS |
| /review | Quality | Convergence (DX-34) |

**Key innovations:**
1. Automatic routing based on task analysis
2. Instruction re-injection at workflow entry
3. Clear exit conditions for each phase
4. Natural flow between workflows
5. Review-fix loop integration (DX-34)
6. Tiered platform support

**Core principle:** Human directs at phase boundaries, Agent executes autonomously within phases.

---

*Builds on DX-31 (Adversarial Review), DX-33 (Verification Blind Spots), and DX-34 (Review Cycle).*
