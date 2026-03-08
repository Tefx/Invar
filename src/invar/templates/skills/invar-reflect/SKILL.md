---
name: invar-reflect
description: Reflect on Invar tool usage experience and generate structured feedback for framework improvement.
_invar:
  version: "1.0"
  managed: skill
---
<!--invar:skill-->
# /invar-reflect — Invar Usage Feedback

> Extension Skill | Tier: T1 | Isolation: None (accesses session history)

## Purpose

Generate structured feedback on Invar tool usage to help improve the framework. Analyzes tool usage patterns, identifies pain points, tracks learning curves, and produces detailed feedback documents stored locally.

**Key Features**:
- **Intelligent aggregation**: Same-day sessions merge into single file
- **Semantic understanding**: Recognizes duplicate issues across sessions
- **Evolution tracking**: Monitors learning progress and problem resolution
- **Privacy-first**: All data stays local in `.invar/feedback/`

## Triggers

**Manual invocation**: User calls `/invar-reflect`

**Future (Phase B)**: Auto-trigger after task completion (30+ messages, 2+ hours)

## Relationship to Other Skills

- This skill is **meta**: It reflects on your usage of Invar, not on user's code
- Runs independently, doesn't interfere with other workflows
- Generates feedback for Invar maintainers, not for current task

---

## Workflow

### Step 1: Check for Today's Feedback File

```
today = 2026-01-03
filepath = .invar/feedback/feedback-{today}.md

if filepath exists:
    mode = "APPEND"
    existing_content = read(filepath)
else:
    mode = "CREATE"
    existing_content = None
```

### Step 2: Analyze Current Session

Gather information about:

1. **Tool usage statistics**:
   - Count of `invar_guard`, `invar_sig`, `invar_map`, `invar_refs` calls
   - Success/failure rates
   - Error types encountered

2. **Pain points**:
   - Repeated errors (same issue multiple times)
   - Workarounds used (patterns of avoiding certain features)
   - Confusion points (frequent doc/example lookups)

3. **Learning curve**:
   - Compare early session vs late session error rates
   - Identify resolved vs ongoing issues
   - Note improvements in workflow

4. **Subjective experience**:
   - What worked well (tools you relied on)
   - What was frustrating (blocking issues)
   - What was confusing (unclear documentation)

### Step 3: Generate or Merge Feedback

**If mode == CREATE** (new file):
- Generate fresh feedback document
- Use full template structure (see below)

**If mode == APPEND** (existing file):
- Read and understand existing content
- Identify duplicate issues using **semantic understanding**:
  - "Guard slow" ≈ "Guard timeout" → Same issue, update count
  - "Missing @pre" ≠ "Missing @post" → Different issues
- Track evolution:
  - Session 1: "5 contract errors"
  - Session 3: "0 contract errors" → Learned!
- Add new issues not previously recorded
- Regenerate daily summary with updated stats

### Step 4: Save Feedback

```
Write to: .invar/feedback/feedback-{today}.md
Output: "✓ Feedback saved to .invar/feedback/feedback-{today}.md"
```

---

## Agent Instructions

### Intelligence Guidelines

**Use your judgment, not mechanical rules**:

1. **Semantic matching**:
   - Recognize synonyms: "Guard performance issue" ≈ "Guard timeout"
   - Differentiate by context: "Core confusion" ≠ "Shell confusion"
   - Consider severity: "Blocking" ≠ "Annoying but manageable"

2. **Evolution tracking**:
   - Compare same issue across sessions
   - Note improvement: "5 errors → 2 errors → 0 errors"
   - Identify resolved issues: "Session 1: confused, Session 3: confident"

3. **Impact assessment**:
   - Blocking: Stopped progress, needed workaround
   - Major: Slowed down significantly (10+ minutes lost)
   - Minor: Slight friction, manageable

4. **Evidence-based reporting**:
   - Provide specific examples: file:line, command used, error message
   - Quote user experience: "I felt..." statements
   - Show workarounds: actual commands or code snippets

### When Appending to Existing File

**Your task**:
1. Read existing feedback carefully
2. Identify which issues from current session are duplicates
3. Update occurrence counts for duplicate issues
4. Add evolution notes: "Still occurring" or "Now resolved"
5. Add genuinely new issues
6. Regenerate the Daily Summary section

**Example merge logic**:

```
Existing (Session 1):
  P1: Guard timeout - 4 occurrences

Current (Session 3):
  Found: Guard slow (5 minutes)

Agent reasoning:
  "Guard slow" and "Guard timeout" are the same issue (performance)

Updated output:
  P1: Guard Performance Issues
  First seen: Session 1 (08:30)
  Last seen: Session 3 (16:45)
  Total occurrences: 9 times across 2 sessions

  Session breakdown:
  - Session 1: 4 times → "Timeout on CrossHair"
  - Session 3: 5 times → "Takes 5 minutes even with --changed"
```

### Feedback Document Structure

Generate detailed markdown following this structure:

```markdown
# Invar Usage Feedback - {date}

**Sessions**: {N} sessions today
**Total Duration**: {X} hours
**Total Messages**: {Y}

---

## Session Timeline

### Session 1: {time} ({task description})
**Messages**: {N} | **Duration**: {X}h

[Brief summary of what was accomplished and main challenges]

### Session 2: {time} ({task description})
**Messages**: {N} | **Duration**: {X}h

[Brief summary...]

---

## 📊 Tool Usage Statistics

| Tool | Calls | Success | Failure | Success Rate |
|------|-------|---------|---------|--------------|
| invar_guard | {N} | {N} | {N} | {X}% |
| invar_sig | {N} | {N} | {N} | {X}% |
| invar_map | {N} | {N} | {N} | {X}% |
| invar_refs | {N} | {N} | {N} | {X}% |

**Total**: {N} tool calls, {N} successful ({X}% success rate)

---

## 😫 Aggregated Pain Points

### P1: [Critical] {Issue Title}

**First seen**: Session {N} ({time})
**Last seen**: Session {N} ({time})
**Total occurrences**: {N} times across {M} sessions

**Session breakdown**:
- Session 1: {N} times → "{specific observation}"
- Session 3: {N} times → "{specific observation}"

**Context**:
{Detailed description of when/why this issue occurs}

**Evolution**:
> Session 1: "{user sentiment/observation}"
> Session 3: "{user sentiment/observation}"

**Current status**: {Resolved / Unresolved / Workaround found}

**Workaround** (if applicable):
```bash
{actual command or code}
```

**Suggested Improvement**:
- {Concrete suggestion 1}
- {Concrete suggestion 2}

---

### P2: [High] {Issue Title}

[Same structure...]

---

## ✅ What Worked Well

### 1. {Tool or Feature}

**Usage**: {N} times
**Success rate**: {X}%

**Why it worked**:
{Explanation}

**Typical workflow**:
```bash
{Example commands}
```

**User experience**:
> "{Quote about positive experience}"

---

## 🤔 Confusion Points

### 1. {Topic}

**What I tried** (wrong):
```python
{Code example}
```

**What worked** (after reading docs/examples):
```python
{Code example}
```

**Gap**: {What documentation is missing or unclear}

---

## 🔄 Workarounds Used

| Issue | Workaround | Frequency |
|-------|------------|-----------|
| {Issue} | {Workaround description} | {N} times |

---

## 💡 Improvement Suggestions

### High Priority
1. **{Suggestion title}**
   - Problem: {What's wrong}
   - Solution: {Proposed fix}
   - Benefit: {Expected improvement}

### Medium Priority
{Same structure...}

### Low Priority
{Same structure...}

---

## 📈 Daily Summary

### High-Frequency Issues (Top 3)
1. **{Issue}** - {N} occurrences, {status}
2. **{Issue}** - {N} occurrences, {status}
3. **{Issue}** - {N} occurrences, {status}

### Learning Progress
| Issue | Session 1 | Session 2 | Session 3 | Trend |
|-------|-----------|-----------|-----------|-------|
| {Issue} | {N} errors | {N} errors | {N} errors | {✅/📈/⚠️} |

### Sentiment Evolution
- **Morning**: {Sentiment description}
- **Afternoon**: {Sentiment description}
- **Evening**: {Sentiment description}

---

## 🎯 Session Success Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Task completed | {Yes/No} | {Success/Blocked} |
| Guard final pass | {Pass/Fail} | {Result} |
| Time to first Guard pass | {X} hours | {Assessment} |
| Stuck on Invar issues | {X} min | {Acceptable/Too long} |
| Would recommend Invar | {Yes/No} | {Positive/Negative} |

---

## 📝 Additional Notes

{Any other observations, context, or insights}

---

## 🔒 Privacy Notice

This feedback document is stored locally in `.invar/feedback/`.
You control what (if anything) to share with Invar maintainers.

**To share feedback**:
1. Review this document
2. Remove any sensitive project details
3. Submit via GitHub issue or email

---

*Generated by `/invar-reflect` v1.0*
*Last updated: {timestamp}*
```

### Quality Checklist

Before saving, verify:
- [ ] Specific examples provided (not generic statements)
- [ ] User experience quotes included (subjective perspective)
- [ ] Workarounds documented (actual commands/code)
- [ ] Learning progression tracked (improvement noted)
- [ ] Suggestions are actionable (concrete, not vague)
- [ ] No sensitive information (code snippets, project names)

---

## Output

After generating/updating feedback:

```
✓ Feedback saved to .invar/feedback/feedback-2026-01-03.md

Summary:
- Sessions today: 3
- New issues identified: 2
- Updated issues: 5
- Resolved issues: 1

High-priority issues:
1. Guard performance (still blocking)
2. Error message clarity (ongoing confusion)

Review the feedback file before sharing with Invar maintainers.
```

---

## Privacy & Ethics

**What's collected**:
- Tool usage counts (no actual code)
- Error types (no error details/messages)
- User's subjective experience
- Time/duration statistics

**NOT collected**:
- Source code
- File paths
- Project-specific details
- Error messages (might leak code)

**User control**:
- All data stays in `.invar/feedback/` (local)
- User reviews before sharing
- Easy to disable: Delete `.invar/feedback/` or skip skill

---

## Examples

### Example 1: First Session of the Day

**Input**: Manual call `/invar-reflect` after 3-hour session

**Output**:
```
✓ Feedback saved to .invar/feedback/feedback-2026-01-03.md

Summary:
- Sessions today: 1
- Issues identified: 4 (2 critical, 2 medium)
- Tools used: guard (5), sig (8), map (2)

High-priority issues:
1. Guard timeout on large codebase
2. Unclear error: missing_contract

Review the feedback file for full details.
```

### Example 2: Third Session of the Day

**Input**: Manual call `/invar-reflect` after another 2-hour session

**Agent reasoning**:
- Reads existing feedback-2026-01-03.md
- Sees "Guard timeout" was reported in Session 1
- Current session also encountered "Guard slow" (5 occurrences)
- Recognizes these are the same issue
- Updates count: 5 → 10 occurrences
- Adds evolution note: "Still unresolved, user found workaround"

**Output**:
```
✓ Feedback updated: .invar/feedback/feedback-2026-01-03.md

Summary:
- Sessions today: 3 (updated)
- New issues: 1
- Updated issues: 3
- Learning progress: Contract syntax errors (5 → 0) ✅

High-priority issues:
1. Guard performance (10 occurrences, still blocking)
2. Contract syntax (RESOLVED - no errors in Session 3)

Daily summary regenerated with latest statistics.
```

---

<!--/invar:skill-->
<!--invar:extensions-->
<!-- User extensions preserved on update -->
<!--/invar:extensions-->
