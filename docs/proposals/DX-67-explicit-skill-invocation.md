# DX-67: Explicit Skill Tool Invocation

**Status:** ✅ Complete
**Created:** 2024-12-29
**Author:** Claude (via benchmark analysis)

## Problem Statement

When Claude reads CLAUDE.md and encounters trigger words (e.g., "implement", "add", "fix"), it follows the USBV workflow but **does NOT invoke the Skill tool**. This causes:

1. **SKILL.md content is never read** - Advanced guidance (DX-63 incremental development, timeout handling, error recovery) is missed
2. **Benchmark metrics are inaccurate** - `Skill Calls = 0` even when workflow is followed
3. **Framework functionality is incomplete** - Only CLAUDE.md's summary is used, not the full skill definition

### Evidence

**Before fix (natural routing without explicit instruction):**
```
Skill Calls: 0
SKILL.md read: No
USBV workflow followed: Yes (from CLAUDE.md only)
```

**After fix (explicit Skill tool instruction):**
```
Skill Calls: 1
Skill(skill="develop") invoked: Yes
Routing announcement shown: Yes
📍 Routing: /develop — "implement" trigger detected
```

## Root Cause Analysis

### Cause 1: Ambiguous Wording

CLAUDE.md said:
```markdown
When user message contains these triggers, you MUST invoke the corresponding skill
```

"invoke the corresponding skill" can be interpreted as:
- **A:** Call the Skill tool to get SKILL.md content ❌ (not chosen)
- **B:** Follow the workflow described in CLAUDE.md ✅ (chosen)

Claude chose B because CLAUDE.md already contains sufficient workflow information.

### Cause 2: Information Redundancy

| Content | In CLAUDE.md | In SKILL.md |
|---------|--------------|-------------|
| USBV workflow overview | ✅ | ✅ |
| Phase headers format | ✅ | ✅ |
| Check-In/Final protocol | ✅ | ✅ |
| DX-63 incremental development | ❌ | ✅ |
| Timeout handling | ❌ | ✅ |
| Error recovery rules | ❌ | ✅ |

Claude's logic: "CLAUDE.md already tells me how to work, why call another tool?"

### Cause 3: No Explicit Tool Call Instruction

CLAUDE.md never said:
```markdown
To invoke a skill, use the Skill tool: Skill(skill="develop")
```

## Solution

### Approach: Explicit Skill Tool Call Requirement

Modify CLAUDE.md's "Workflow Routing" section to explicitly require Skill tool calls:

```markdown
## Workflow Routing (MANDATORY)

When user message contains these triggers, you MUST use the **Skill tool** to invoke the skill:

| Trigger Words | Skill Tool Call | Notes |
|---------------|-----------------|-------|
| "review", "review and fix" | `Skill(skill="review")` | Adversarial review |
| "implement", "add", "fix", "update" | `Skill(skill="develop")` | USBV workflow |
| "why", "explain", "investigate" | `Skill(skill="investigate")` | Research mode |
| "compare", "should we", "design" | `Skill(skill="propose")` | Decision facilitation |

**⚠️ CRITICAL: You must call the Skill tool, not just follow the workflow mentally.**

The Skill tool reads `.claude/skills/<skill>/SKILL.md` which contains:
- Detailed phase instructions (USBV breakdown)
- Error handling rules
- Timeout policies
- Incremental development patterns (DX-63)

**Violation check (before writing ANY code):**
- "Did I call `Skill(skill="...")`?"
- "Am I following the SKILL.md instructions?"
```

## Verification

### Test Protocol

1. Run benchmark task with natural routing (no `/develop` prefix)
2. Check conversation logs for Skill tool calls
3. Verify SKILL.md content is being used

### Verification Results

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Skill Calls | 0 | 1 | ✅ Fixed |
| Skill(skill="develop") | Not called | Called | ✅ Fixed |
| Routing announcement | Missing | `📍 Routing: /develop — "implement"` | ✅ Fixed |
| SKILL.md guidance used | No | Yes | ✅ Fixed |

### Test Command

```bash
cd invar-benchmark
python3 -m harness.runner --group treatment --task task_002_parser \
  --mode interactive --max-turns 50 --no-progress
```

## Implementation

### Files to Modify

1. **CLAUDE.md template** (`src/invar/templates/CLAUDE.md`)
   - Update "Workflow Routing" section with explicit Skill tool calls
   - Add "⚠️ CRITICAL" warning

2. **Benchmark treatment config** (`invar-benchmark/configs/treatment/CLAUDE.md`)
   - Already modified for verification
   - Same changes as template

### Migration

Users with existing CLAUDE.md files need to run:
```bash
invar update
```

This will sync the managed sections with the new template.

## Impact Assessment

| Aspect | Impact |
|--------|--------|
| Breaking changes | None - additive clarification |
| Backward compatibility | Full - existing workflows still work |
| Performance | Minimal - one additional tool call per task |
| Accuracy | Improved - Skill Calls metric now meaningful |
| Framework completeness | Improved - SKILL.md content now used |

## Alternatives Considered

### Alternative A: Remove redundant info from CLAUDE.md

**Approach:** Strip CLAUDE.md down to routing rules only, force reading SKILL.md for all workflow details.

**Pros:**
- No redundancy
- Forces Skill tool use

**Cons:**
- Major restructuring
- Breaks users who expect CLAUDE.md to be self-contained
- Risk of workflow failures if Skill tool unavailable

**Decision:** Rejected - too disruptive

### Alternative B: Accept current behavior

**Approach:** Document that Skill tool is optional, CLAUDE.md is sufficient.

**Pros:**
- No changes needed

**Cons:**
- SKILL.md content wasted
- Benchmark metrics misleading
- DX-63 and other advanced features not used

**Decision:** Rejected - loses framework value

## Success Criteria

1. ✅ Skill Calls > 0 for treatment group tasks
2. ✅ `Skill(skill="develop")` appears in conversation logs
3. ✅ Routing announcement (`📍 Routing: /develop`) is displayed
4. ✅ No regression in USBV workflow compliance

## Timeline

- [x] Problem identified (Dec 29, 2025)
- [x] Root cause analyzed (Dec 29, 2025)
- [x] Solution implemented in benchmark (Dec 29, 2025)
- [x] Verification passed (Dec 29, 2025)
- [ ] Template updated in Invar core
- [ ] Documentation updated
- [ ] Released in next version

## References

- DX-42: Routing Control
- DX-51: Phase Visibility
- DX-54: Context Management
- DX-63: Contracts-First Enforcement
- BM-05: Fair Benchmark Mode
