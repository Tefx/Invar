# DX-79: Invar Usage Feedback Collection

**Status**: Draft
**Created**: 2026-01-03
**Category**: Meta-Improvement
**Priority**: Medium

---

## Problem Statement

Invar 作为 AI-native 开发框架，需要从真实使用场景中收集反馈以持续改进。当前缺乏系统化的机制来：

1. **识别痛点**: 用户在实际使用中遇到的困难和障碍
2. **发现盲区**: 文档未覆盖或解释不清的场景
3. **收集改进建议**: 基于真实工作流的优化方向
4. **验证设计**: 确认工具和工作流是否符合预期

当前依赖手动反馈，无法捕捉隐性问题（用户适应了但不会主动报告的痛点）。

---

## Solution Overview

**核心思路**: 让使用 Invar 的项目中的 AI agent 自动反思工具使用体验，生成结构化反馈文档。

### Key Components

1. **Skill: `/invar-reflect`** - 分析工作 session，生成结构化反馈
2. **Hook: `PostTaskCompletion`** - 任务完成后自动触发反思
3. **Config: `feedback.enabled`** - 用户可配置开关（默认 enable）
4. **Storage: `.invar/feedback/`** - 本地存储，用户完全控制

---

## Design

### 1. Skill: `/invar-reflect`

#### Naming Rationale

- ❌ `/reflect` - 太通用，容易与其他技能冲突
- ✅ `/invar-reflect` - 明确指向 Invar 框架反馈
- 或 `/reflect-invar` - 同样明确，但前缀更统一

**选择**: `/invar-reflect` (动词+主题，符合技能命名习惯)

#### Behavior

```
触发条件:
1. 手动调用: 用户执行 `/invar-reflect`
2. 自动触发: Hook PostTaskCompletion (见下文)

执行内容:
1. 分析当前 session 的工具调用历史
   - invar_guard / invar_sig / invar_map / invar_refs
   - 成功/失败次数
   - 错误类型分布

2. 识别使用模式
   - 重复出现的错误
   - 频繁查阅的文档/示例
   - 绕过或规避的场景

3. 反思工作流体验
   - 哪些环节流畅
   - 哪些环节卡住
   - 哪些文档/工具没用上

4. 生成结构化反馈文档
   - 保存到 .invar/feedback/{timestamp}.md
   - 格式见下文

输出:
"✓ Feedback saved to .invar/feedback/2026-01-03-143022.md"
```

#### Skill Definition

```markdown
# Skill: invar-reflect

**Purpose**: Reflect on Invar tool usage experience and generate structured feedback.

## When to Use

- After completing a major development task
- When encountering repeated friction with Invar tools
- Periodically (via auto-trigger, see Hook section)

## What It Does

1. **Analyze tool usage**
   - Parse session history for invar_* tool calls
   - Calculate success/failure rates
   - Identify error patterns

2. **Identify pain points**
   - Repeated errors (same issue > 2 times)
   - Workarounds used (bypass patterns)
   - Confusion points (frequent doc/example lookups)

3. **Generate feedback document**
   - Structured markdown report
   - Saved locally to .invar/feedback/
   - User reviews before sharing (privacy-first)

## Output Format

See "Feedback Document Structure" below.

## Privacy

- All data stays local in `.invar/feedback/`
- User decides what (if anything) to share
- No automatic telemetry
```

### 2. Hook: PostTaskCompletion

#### Trigger Strategy

**Rejected: Fixed interval (e.g., every N messages)**
- ❌ 20 轮太频繁 - 每天可能产生 3-5 个文件，快速堆积
- ❌ 50 轮仍频繁 - 中等项目一天仍有多个文件
- ❌ 无视任务边界 - 可能在任务中间打断

**Recommended: Task completion + Threshold (No hard frequency cap)**

| Condition | Description | Example |
|-----------|-------------|---------|
| Task completed | User finished major work | After "implement auth" task |
| AND message count >= 30 | Sufficient context | Avoid trivial tasks |
| AND time elapsed >= 2 hours | Non-trivial session | Avoid quick fixes |

**Natural Filtering**: Thresholds naturally limit frequency without arbitrary daily caps.
**File Merging**: Same-day feedback merged into single file (see below).

#### Hook Configuration

```json
// .claude/settings.json
{
  "hooks": {
    "post_task_completion": {
      "action": "skill:invar-reflect",
      "conditions": {
        "min_messages": 30,
        "min_duration_hours": 2
      },
      "mode": "silent"
    }
  },
  "feedback": {
    "enabled": true,          // User can disable
    "auto_trigger": true,     // Separate toggle for auto-trigger
    "retention_days": 90      // Auto-cleanup old feedback
  }
}
```

**Note**: No `max_per_day` limit. Same-day sessions automatically merge into one file.

**Mode**: `silent` - 不打断当前对话，后台生成反馈

### 3. Feedback Document Structure

```markdown
# Invar Usage Feedback

**Session**: 2026-01-03-143022
**Project**: my-awesome-project
**Duration**: 2.5 hours
**Messages**: 45
**Model**: claude-sonnet-4-5
**Invar Version**: 1.12.0

---

## 📊 Tool Usage Statistics

| Tool | Calls | Success | Failure | Success Rate |
|------|-------|---------|---------|--------------|
| invar_guard | 8 | 7 | 1 | 87.5% |
| invar_sig | 12 | 12 | 0 | 100% |
| invar_map | 3 | 3 | 0 | 100% |
| invar_refs | 5 | 4 | 1 | 80% |

**Total**: 28 tool calls, 26 successful, 2 failed (92.9% success rate)

---

## 😫 Pain Points (High Impact)

### P1: [Critical] Guard timeout on large codebase

**Frequency**: Every guard run (8 times)
**Impact**: Blocking - had to use `--changed` workaround every time
**Context**:
- Project: 500+ Python files
- Guard takes 3-5 minutes even with `--changed`
- CrossHair verification times out

**Workaround Used**:
```bash
# Had to split verification
invar guard --changed --skip-crosshair  # First pass
invar guard src/core/critical.py        # Manual targeted check
```

**User Experience**:
> "I understand Guard is thorough, but 5 minutes for every change breaks flow. I'm now avoiding guard until I batch multiple changes, which defeats the purpose of fast feedback."

**Suggested Improvement**:
- Add incremental verification mode (only changed functions)
- Show progress bar with ETA
- Allow cancellation with partial results

---

### P2: [High] Unclear error message: "missing_contract"

**Frequency**: 3 times this session
**Impact**: Annoying - had to read examples to understand what to do
**Context**:
- Forgot to add `@pre/@post` on Core function
- Error message: "missing_contract: function 'parse' has no contracts"
- Didn't know if it wanted `@pre`, `@post`, or both

**What I Tried** (wrong):
```python
@pre(lambda source: source)  # Confused - what constraint?
def parse(source: str) -> AST:
    ...
```

**What Finally Worked** (after reading examples):
```python
@pre(lambda source: len(source.strip()) > 0)
@post(lambda result: result is not None)
def parse(source: str) -> AST:
    ...
```

**User Experience**:
> "The error told me WHAT was wrong but not HOW to fix it. I had to hunt for examples in .invar/examples/contracts.py."

**Suggested Improvement**:
```
Error: missing_contract: function 'parse' has no contracts

Core functions require @pre/@post contracts:
  @pre(lambda source: ...)   # Input constraints
  @post(lambda result: ...)  # Output guarantees

Example: .invar/examples/contracts.py#L45
Docs: INVAR.md#contract-rules
```

---

### P3: [Medium] Confusion: When to use Core vs Shell?

**Frequency**: Uncertain 5 times, re-read docs 3 times
**Impact**: Slows down - spent 10-15 min deciding per function
**Context**:
- Writing functions that do both logic AND I/O
- Documentation says "Core = pure, Shell = I/O"
- But edge cases unclear:
  - Function that takes `Path` param but doesn't read it?
  - Function that logs to stderr?
  - Function that uses `datetime.now()`?

**Decision Pattern**:
| Function | My Guess | Actual | Time Spent |
|----------|----------|--------|------------|
| validate_path(p: Path) | Core? | Core ✓ | 5 min |
| read_config(p: Path) | Shell | Shell ✓ | 2 min |
| log_error(msg: str) | ??? | Shell | 15 min (re-read docs) |
| format_timestamp(dt) | Core? | Core ✓ | 3 min |

**User Experience**:
> "The principle is clear, but I keep hitting edge cases not in the docs. I wish there was a decision tree or examples for ambiguous cases."

**Suggested Improvement**:
- Decision flowchart in INVAR.md
- More edge case examples in .invar/examples/core_shell.py
- Guard could suggest "This looks like Shell (uses logging)"

---

## ✅ What Worked Well

### 1. `invar_sig` for quick contract lookup

**Usage**: 12 times (most used tool)
**Success**: 100%

**Why it worked**:
- Instant feedback - no need to read full file
- Clear output format - contracts highlighted
- Fast - <1s response time

**Typical workflow**:
```bash
invar sig src/core/parser.py  # See all contracts
# Spot the function I need
# Copy contract pattern
```

**User Experience**:
> "This is my go-to tool. Saves tons of time vs opening files."

---

### 2. Auto-fix suggestions from Guard

**Fixed automatically**: 5 issues
- 3x `missing_contract` → Guard suggested contracts
- 2x `redundant_type_contract` → Guard explained semantic constraint needed

**User Experience**:
> "When Guard suggests fixes, I learn the pattern. By the 3rd similar error, I stopped making that mistake."

---

### 3. Contract-first workflow (USBV)

**Followed**: Understand → Specify → Build → Validate
**Result**: 0 contract violations caught by CrossHair

**User Experience**:
> "Writing contracts before code felt slow at first, but Guard caught zero violations later. Saved debugging time."

---

## 🤔 Confusion Points (Learning Curve)

### 1. @skip_property_test syntax

**What I tried** (wrong):
```python
@skip_property_test("too slow")
def expensive_function():
    ...
```

**Error**:
```
TypeError: skip_property_test() got an unexpected keyword argument
```

**What worked**:
```python
@skip_property_test(reason="too slow")
def expensive_function():
    ...
```

**Gap**: The docstring for `@skip_property_test` doesn't show the signature clearly.

---

### 2. Deal vs invar_runtime contracts

**Confusion**: When to use `from deal import pre` vs `from invar_runtime import pre`?

**What I learned** (after trial and error):
- `deal.pre` → Lambda-based contracts
- `invar_runtime.pre` → Pre-built contract objects like `NonEmpty`

**Gap**: This distinction not explained in INVAR.md "Critical Rules" section.

---

## 🔄 Workarounds Used

| Issue | Workaround | Frequency |
|-------|------------|-----------|
| Guard timeout | `--changed` + manual spot checks | 8 times |
| Core/Shell confusion | Copy from examples instead of thinking | 3 times |
| Contract syntax | Copy-paste from .invar/examples/ | 5 times |

---

## 💡 Improvement Suggestions

### High Priority

1. **Incremental Guard mode**
   - **Problem**: Full project scan too slow
   - **Solution**: Only verify changed functions + their callers
   - **Benefit**: 10x speedup for iterative development

2. **Contextual error messages**
   - **Problem**: Errors say WHAT but not HOW
   - **Solution**: Include example link + fix hint in error
   - **Benefit**: Reduce "search for examples" friction

3. **Core/Shell decision tree**
   - **Problem**: Edge cases unclear
   - **Solution**: Flowchart in INVAR.md + more examples
   - **Benefit**: Faster decisions, less re-reading

### Medium Priority

4. **Interactive tutorial for first-time users**
   - **Problem**: Learning curve steep
   - **Solution**: `invar tutorial` command with guided examples
   - **Benefit**: Faster onboarding

5. **Guard progress indicator**
   - **Problem**: No feedback during long runs
   - **Solution**: Show "Checking file 45/120..."
   - **Benefit**: Less anxiety during wait

6. **Contract snippet library**
   - **Problem**: Repetitive contract patterns
   - **Solution**: `invar snippet list` with common patterns
   - **Benefit**: Copy-paste correct patterns quickly

### Low Priority

7. **Guard performance dashboard**
   - **Problem**: Can't see what's slow
   - **Solution**: `--profile` flag showing time per rule
   - **Benefit**: Optimize workflow

---

## 📈 Session Learning Curve

**Start of session**:
- Uncertain about Core/Shell (consulted docs 3 times)
- Made 5 contract syntax errors

**End of session**:
- Core/Shell decisions faster (pattern recognized)
- Contract syntax muscle memory (stopped making errors)
- Using `invar sig` proactively before writing code

**Overall**: Tools work well once learned, but initial learning curve is steep.

---

## 🎯 Session Success Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Task completed | ✅ Yes | Success |
| Guard final pass | ✅ 0 errors | Success |
| Time to first Guard pass | 2.5 hours | Could be faster |
| Stuck on Invar issues | ~30 min | Acceptable |
| Would recommend Invar | ✅ Yes | Positive |

---

## 📝 Additional Notes

- First time using `invar refs` - worked great for TypeScript files
- Didn't use `invar map` much - not sure when it's better than `invar sig`
- Skill system (`/develop`, `/review`) works smoothly - no issues

---

## 🔒 Privacy Notice

This feedback document is stored locally in `.invar/feedback/`.
You control what (if anything) to share with Invar maintainers.

**To share feedback**:
1. Review this document
2. Remove any sensitive project details
3. Submit via GitHub issue or email

---

*Generated by `/invar-reflect` v1.12.0*
```

---

### 4. File Merging & Intelligent Aggregation

#### Same-Day Merging Strategy

**Core Principle**: Same-day sessions merge into single file, leveraging agent intelligence.

**File Naming**:
```bash
.invar/feedback/
├── feedback-2026-01-03.md  # All sessions from Jan 3
├── feedback-2026-01-04.md  # All sessions from Jan 4
└── feedback-2026-01-10.md  # Jan 10 (gaps are OK)
```

**Note**: Each project has independent `.invar/feedback/` directory. No cross-project awareness.

#### Agent-Driven Intelligent Merging

**Why NOT mechanical similarity matching**:
- ❌ Keyword-based similarity (e.g., Jaccard index) is too simplistic
- ❌ Arbitrary thresholds (70%?) have no principled basis
- ❌ Misses semantic equivalence: "Guard slow" ≈ "Guard timeout"
- ❌ Wastes agent's natural language understanding capability

**Why agent intelligence**:
- ✅ Semantic understanding: Recognizes "Guard performance" ≈ "Guard timeout"
- ✅ Context-aware: Differentiates "Core confusion" ≠ "Shell confusion"
- ✅ Tracks evolution: "No idea" → "Still unsure" → "Now confident"
- ✅ Flexible: No hard-coded rules to maintain

#### Merge Workflow

```
1. Check if today's file exists
   ├─ YES → Read existing content
   │        Agent analyzes:
   │        - What issues were already recorded?
   │        - Is current issue duplicate or new?
   │        - How has problem evolved?
   │
   └─ NO  → Create new file

2. Agent generates merged output
   - Updates occurrence counts
   - Adds new observations
   - Tracks resolution progress
   - Generates daily summary

3. Save to feedback-{today}.md
```

#### Merged Document Structure

```markdown
# Invar Usage Feedback - 2026-01-03

**Sessions**: 3 sessions today
**Total Duration**: 7.5 hours
**Total Messages**: 107

---

## Session Timeline

### Session 1: 08:30-11:30 (Implement Authentication)
**Messages**: 40 | **Duration**: 3h

[Brief summary or full details...]

### Session 2: 13:00-15:30 (Add Tests)
**Messages**: 35 | **Duration**: 2.5h

[Brief summary or full details...]

### Session 3: 16:00-18:00 (Fix Bugs)
**Messages**: 32 | **Duration**: 2h

[Brief summary or full details...]

---

## 😫 Aggregated Pain Points

### P1: [Critical] Guard Performance Issues

**First seen**: Session 1 (08:30)
**Last seen**: Session 3 (16:45)
**Total occurrences**: 12 times across 3 sessions

**Session breakdown**:
- Session 1: 4 times → "Takes 5 minutes to run"
- Session 2: 5 times → "Timeout on CrossHair verification"
- Session 3: 3 times → "Still slow even with --changed"

**Evolution**:
> Session 1: "5 minutes breaks my flow, totally blocking"
> Session 3: "Found workaround but still annoying"

**Current status**: Unresolved, workaround reduces impact

**Workaround**:
```bash
invar guard --changed --skip-crosshair
```

### P2: [High] Contract Syntax Confusion

**First seen**: Session 1 (08:45)
**Last seen**: Session 2 (14:20)
**Total occurrences**: 7 times across 2 sessions

**Session breakdown**:
- Session 1: 5 errors → Learning phase
- Session 2: 2 errors → Improving
- Session 3: 0 errors → Learned! ✓

**Evolution**: **RESOLVED** through practice

---

## 📈 Daily Summary

### High-Frequency Issues (Top 3)
1. **Guard performance** - 12 occurrences, still blocking
2. **Contract syntax** - 7 occurrences, now resolved ✓
3. **Core/Shell decision** - 3 occurrences, ongoing learning

### Learning Progress
| Issue | Session 1 | Session 2 | Session 3 | Trend |
|-------|-----------|-----------|-----------|-------|
| Contract syntax | 5 errors | 2 errors | 0 errors | ✅ Learned |
| Core/Shell | Confused | Still unsure | Clearer | 📈 Improving |
| Guard usage | Blocked | Found workaround | Using workaround | ⚠️ Not fixed |

### Sentiment Evolution
- **Morning**: Frustrated (Guard blocks progress)
- **Afternoon**: Adapting (workarounds found)
- **Evening**: Productive (main friction remains but manageable)

---

*Generated by `/invar-reflect` v1.12.0*
*Last updated: 2026-01-03 18:15*
```

#### Agent Skill Prompt (Key Points)

```markdown
## When appending to existing file:

1. **Read and understand** what was recorded earlier today
2. **Semantic matching** (not keyword matching):
   - "Guard slow" ≈ "Guard timeout" → Same issue
   - "Missing @pre" ≠ "Missing @post" → Different issues
3. **Update intelligently**:
   - Increment counts
   - Track evolution ("5 errors" → "2 errors" → "0 errors")
   - Note resolution status
4. **Add new issues** not previously recorded
5. **Regenerate daily summary** with updated stats

## Intelligence guidelines:

- Use your judgment, not mechanical rules
- Recognize synonyms and variations
- Track learning curves and progress
- Differentiate by context and impact
- Aggregate statistics meaningfully
```

---

### 5. Init-Time Configuration

#### User Consent Flow

```bash
$ invar init

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Usage Feedback (Optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invar can automatically reflect on tool usage to help improve
the framework. Feedback is:
  - Stored locally in .invar/feedback/
  - Never sent automatically
  - You decide what (if anything) to share

Enable automatic feedback collection? [Y/n]:
```

**Default**: `Y` (enabled)
**Rationale**: Opt-out (not opt-in) maximizes feedback coverage while respecting user choice

#### Generated Config

```json
// .claude/settings.json
{
  "feedback": {
    "enabled": true,            // User can disable anytime
    "auto_trigger": true,       // Auto-run /invar-reflect
    "min_messages": 30,         // Threshold for meaningful session
    "min_duration_hours": 2,    // Avoid trivial tasks
    "max_per_day": 1,           // Frequency cap
    "retention_days": 90        // Auto-cleanup old files
  }
}
```

#### Manual Disable

```bash
# Disable feedback collection
invar config set feedback.enabled false

# Disable auto-trigger only (manual /invar-reflect still works)
invar config set feedback.auto_trigger false

# Check current setting
invar config get feedback
```

---

## Privacy & Ethics

### Design Principles

1. **Local-First**: All data stored on user's machine
2. **Transparency**: User sees exactly what's collected
3. **Control**: Easy to disable, edit, or delete
4. **No Tracking**: Zero telemetry or analytics
5. **Informed Consent**: Clear explanation during init

### Data Collected

**Session metadata**:
- Timestamp
- Message count
- Duration
- Model name
- Invar version

**Tool usage**:
- Tool name (e.g., invar_guard)
- Success/failure count
- Error types (NO error details - might contain code)

**Qualitative feedback**:
- Pain points (agent's analysis)
- Confusion points
- Improvement suggestions

**NOT collected**:
- Source code
- Project names (anonymized)
- File paths (anonymized)
- Error messages (might leak code)

### Anonymization

Before any potential sharing, the document is auto-anonymized:

```python
def anonymize_feedback(doc: str) -> str:
    """Remove identifying information."""
    doc = re.sub(r'\*\*Project\*\*: .*', '**Project**: [redacted]', doc)
    doc = re.sub(r'File: src/.*', 'File: [path redacted]', doc)
    doc = re.sub(r'function \'.*\'', 'function [name redacted]', doc)
    return doc
```

User can review before sharing.

---

## Implementation Plan

### Phase A: Core Skill (Week 1)

**Deliverables**:
```
.claude/skills/invar-reflect/
├── SKILL.md              # Skill definition
└── template.md           # Feedback document template
```

**Tasks**:
1. Create skill definition following LX-07 structure
2. Implement feedback generation logic
3. Test on sample session

**Acceptance Criteria**:
- Manual `/invar-reflect` works
- Generates valid markdown document
- Saves to `.invar/feedback/`

---

### Phase B: Hook Integration (Week 2)

**Deliverables**:
- `PostTaskCompletion` hook type
- Auto-trigger configuration
- Silent execution mode

**Tasks**:
1. Define hook schema in `.claude/settings.json`
2. Implement task completion detection
3. Add frequency cap (max 1/day)
4. Test auto-trigger doesn't interrupt workflow

**Acceptance Criteria**:
- Hook triggers at task completion
- Respects min_messages/min_duration thresholds
- Silent mode works (no user interruption)
- User can disable via config

---

### Phase C: Init Integration (Week 2)

**Deliverables**:
- Consent prompt in `invar init`
- Config generation
- Documentation update

**Tasks**:
1. Add feedback consent step to init flow
2. Generate `.claude/settings.json` with feedback config
3. Update CLAUDE.md with feedback explanation
4. Add to .invar/context.md

**Acceptance Criteria**:
- Init prompts user about feedback
- Default is "enabled"
- Config generated correctly
- Documentation clear

---

### Phase D: Analysis Tools (Optional, Week 3-4)

**Deliverables**:
- `invar feedback` command group
- Local aggregation
- Trend analysis

**Commands**:
```bash
# List all feedback files
invar feedback list

# Aggregate multiple files
invar feedback aggregate --last 7days > summary.md

# Identify high-frequency issues
invar feedback trends

# Anonymize for sharing
invar feedback anonymize 2026-01-03-143022.md > safe-to-share.md

# Clean up old files
invar feedback cleanup --older-than 90days
```

**Nice-to-have**:
- Markdown → JSON export for analysis
- Frequency heatmap (which errors repeat most)
- Success rate trends over time

---

## Alternatives Considered

### 1. Fixed Interval (Every N Messages)

**Rejected**: Creates file spam, ignores task boundaries

**Example**:
- 20 messages: 3-5 files/day (too many)
- 50 messages: Still 1-2 files/day (accumulates quickly)
- 100 messages: Might miss short sessions

**Why task-based + same-day merging is better**:
- Aligns with natural work units (task completion)
- Same-day merging consolidates multiple sessions
- More meaningful context (full task scope)

---

### 2. Opt-In (Disabled by Default)

**Rejected**: Low adoption rate, insufficient feedback

**Data from similar tools**:
- Opt-in telemetry: 5-15% adoption
- Opt-out telemetry: 70-85% adoption

**Compromise**:
- Default: Enabled (opt-out)
- Init: Clear explanation + easy to decline
- Runtime: Easy to disable anytime

---

### 3. Mechanical Similarity Matching (e.g., Keyword Jaccard Index)

**Rejected**: Too simplistic, wastes agent intelligence

**Why mechanical matching fails**:
- Keyword-based similarity (Jaccard, cosine) misses semantics
  - "Guard slow" vs "Guard timeout" → Low keyword overlap but same issue
  - "Core confusion" vs "Shell confusion" → High keyword overlap but different issues
- Arbitrary thresholds (70%? 80%?) lack principled basis
- Cannot track evolution: "No idea" → "Still learning" → "Now confident"
- Requires maintenance as patterns change

**Why agent intelligence is better**:
- Natural language understanding recognizes synonyms and variations
- Context-aware differentiation (blocking vs annoying)
- Tracks learning curves automatically
- No hard-coded rules to maintain
- Generates richer insights (sentiment, trends, resolution status)

---

### 4. Central Collection Server

**Rejected**: Privacy concerns, trust issues

**Risks**:
- Users hesitant to share code-adjacent data
- Server infrastructure cost
- Data breach liability
- Compliance (GDPR, etc.)

**Local-first is better**:
- User keeps full control
- No infrastructure needed
- Voluntary sharing builds trust

---

## Success Metrics

### Adoption Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Init acceptance rate | >70% | Count "Y" vs "n" in init |
| Active users (enabled) | >60% | Config setting analysis |
| Feedback files created | >100/month | File count in community |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pain points identified | >50 unique | Manual review |
| Improvement suggestions | >30 actionable | Manual triage |
| Fixed based on feedback | >10/quarter | GitHub issues |

### User Satisfaction

| Metric | Target | Measurement |
|--------|--------|-------------|
| Users who disable | <20% | Config analysis |
| Users who re-enable | >50% | Config toggle tracking |
| Complaints about spam | <5% | GitHub issues |

---

## Risks & Mitigations

### Risk 1: File Accumulation

**Problem**: Users forget to clean up, `.invar/feedback/` grows large

**Mitigation**:
- Auto-cleanup after 90 days (configurable)
- Show file count in feedback header
- Remind user periodically: "You have 20 feedback files. Review or archive?"

---

### Risk 2: User Annoyance

**Problem**: Auto-trigger feels intrusive

**Mitigation**:
- Silent mode (no interruption)
- Frequency cap (max 1/day)
- Easy to disable
- Clear benefit explanation

---

### Risk 3: Low-Quality Feedback

**Problem**: Agent generates generic or unhelpful feedback

**Mitigation**:
- Prompt engineering for specificity
- Require concrete examples
- Filter out sessions with insufficient data
- Iterate on skill prompt based on output quality

---

### Risk 4: Privacy Concerns

**Problem**: Users fear data leakage

**Mitigation**:
- Explicit "stays local" messaging
- No automatic uploads
- Anonymization tooling
- Open-source skill code (auditable)

---

## Open Questions

1. **Trigger timing**: Should we trigger immediately after task completion, or wait for user to end session?
   - Immediate: More timely, but might miss context
   - End-of-session: More complete, but user might close terminal

2. **Feedback detail level**: How verbose should the generated document be?
   - Minimal (1 page): Easy to review, might miss nuance
   - **Detailed (3-5 pages): Recommended** - Reveals hidden patterns and edge cases
   - Rationale: Purpose is to uncover implicit issues, not just count errors

3. **Sharing mechanism**: Should we provide built-in sharing?
   - Option A: Manual (user emails or GitHub issue)
   - Option B: `invar feedback submit` (requires backend)
   - Recommendation: Start with manual, add submit later if demand

4. **Skill vs Built-in**: Should this be a skill or core command?
   - Skill: User can customize, easier to disable
   - Built-in: More integrated, harder to bypass
   - Recommendation: Start as skill, migrate to core if widely adopted

---

## Related Work

### Similar Features in Other Tools

| Tool | Feedback Mechanism | Approach |
|------|-------------------|----------|
| VS Code | Opt-in telemetry | Automatic, anonymized |
| Homebrew | `brew doctor` output | Manual sharing |
| Rust compiler | Error code explanations | Help users, learn from patterns |
| PyCharm | Usage statistics | Opt-in, periodic prompts |

### Lessons Learned

1. **Transparency wins**: Users accept telemetry if they understand why
2. **Opt-out > Opt-in**: Higher participation, users who care can disable
3. **Local-first**: Privacy-conscious users prefer local storage
4. **Actionable > Volume**: 10 detailed reports better than 100 generic ones

---

## Next Steps

### Immediate (This Week)

1. **Finalize proposal**: Review with team, gather feedback
2. **Design skill structure**: Define .claude/skills/invar-reflect/ layout
3. **Prototype template**: Create sample feedback.md to validate format

### Short-term (Next 2 Weeks)

4. **Implement Phase A**: Core `/invar-reflect` skill
5. **Test with real sessions**: Generate feedback on actual Invar development
6. **Iterate on prompt**: Refine feedback quality based on output

### Medium-term (Next Month)

7. **Implement Phase B**: Hook integration
8. **Implement Phase C**: Init integration
9. **Release v1.13.0**: Ship feedback collection feature

### Long-term (Future)

10. **Analyze feedback**: Mine collected data for improvement opportunities
11. **Implement Phase D**: Analysis tools (if needed)
12. **Measure impact**: Track whether feedback leads to actual improvements

---

## Conclusion

**Why this matters**:
- Invar is AI-native - agents can reflect better than humans on tool UX
- Systematic feedback beats ad-hoc reports
- Early adopters' pain points guide framework evolution

**Success looks like**:
- 70%+ users keep feedback enabled
- 50+ unique pain points identified in first quarter
- 10+ framework improvements driven by feedback

**User value**:
- Better Invar (faster, clearer, easier)
- Feeling heard (their friction leads to fixes)
- Community contribution (even without manual reporting)

---

**Approval needed**:
- [ ] Design approval (skill name, hook strategy, privacy approach)
- [ ] Implementation priority (versus other DX work)
- [ ] Timeline confirmation (3-week effort reasonable?)

**Design decisions resolved**:
1. ✅ Skill name: `/invar-reflect` (includes "invar" to avoid conflicts)
2. ✅ No hard frequency cap (same-day merging prevents spam)
3. ✅ Agent-driven merging (not mechanical similarity matching)
4. ✅ Detailed feedback format (3-5 pages to reveal patterns)
5. ✅ Opt-out by default (maximize coverage, easy to disable)

**Questions for team**:
1. Should we start with Phase A only (skill) and iterate before hooks/init?
2. Any privacy concerns not addressed?
3. Timeline: 3-week implementation reasonable for all phases?
