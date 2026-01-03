# Invar Usage Feedback - 2026-01-03

**Sessions**: 3 sessions today
**Total Duration**: 7.5 hours
**Total Messages**: 107

---

## Session Timeline

### Session 1: 08:30-11:30 (Implement Authentication)
**Messages**: 40 | **Duration**: 3h

Implemented JWT authentication for API endpoints. Main challenge was understanding Core/Shell separation for token validation logic.

### Session 2: 13:00-15:30 (Add Tests)
**Messages**: 35 | **Duration**: 2.5h

Added comprehensive test suite with doctests and property tests. Guard verification took longer than expected due to CrossHair timeout issues.

### Session 3: 16:00-18:00 (Fix Bugs)
**Messages**: 32 | **Duration**: 2h

Fixed edge cases found in code review. Learning curve improved - fewer contract syntax errors.

---

## 📊 Tool Usage Statistics

| Tool | Calls | Success | Failure | Success Rate |
|------|-------|---------|---------|--------------|
| invar_guard | 12 | 10 | 2 | 83.3% |
| invar_sig | 18 | 18 | 0 | 100% |
| invar_map | 5 | 5 | 0 | 100% |
| invar_refs | 3 | 2 | 1 | 66.7% |

**Total**: 38 tool calls, 35 successful (92.1% success rate)

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

**Context**:
Project has 500+ Python files. Guard takes 3-5 minutes even with `--changed` flag. CrossHair verification frequently times out on complex contract conditions.

**Evolution**:
> Session 1: "5 minutes breaks my flow, totally blocking"
> Session 3: "Found workaround but still annoying"

**Current status**: Unresolved, workaround reduces impact

**Workaround**:
```bash
invar guard --changed --skip-crosshair  # First pass
invar guard src/core/critical.py        # Manual targeted check
```

**Suggested Improvement**:
- Add incremental verification mode (only changed functions + callers)
- Show progress bar with ETA during long runs
- Allow cancellation with partial results
- Consider caching CrossHair results for unchanged functions

---

### P2: [High] Contract Syntax Confusion

**First seen**: Session 1 (08:45)
**Last seen**: Session 2 (14:20)
**Total occurrences**: 7 times across 2 sessions

**Session breakdown**:
- Session 1: 5 errors → Learning phase
- Session 2: 2 errors → Improving
- Session 3: 0 errors → Learned! ✓

**Context**:
Confusion about lambda parameter requirements in `@pre`/`@post` decorators. Error messages didn't clearly explain that lambda must include ALL parameters including defaults.

**What I tried** (wrong):
```python
@pre(lambda x: x >= 0)  # Missing y parameter!
def calc(x: int, y: int = 0):
    ...
```

**What worked**:
```python
@pre(lambda x, y=0: x >= 0)  # Include defaults
def calc(x: int, y: int = 0):
    ...
```

**Evolution**: **RESOLVED** through practice and better error messages in latest Guard version

**Suggested Improvement**:
- Show example in error message: "Did you forget parameters? Try: @pre(lambda x, y=0: ...)"
- Add to INVAR.md Critical Rules with prominent placement

---

### P3: [Medium] Core/Shell Decision Unclear

**First seen**: Session 1 (09:15)
**Last seen**: Session 3 (17:00)
**Total occurrences**: 5 times across 3 sessions

**Session breakdown**:
- Session 1: 3 decisions, ~15 min each → Re-read docs multiple times
- Session 2: 1 decision, ~5 min → Pattern becoming clearer
- Session 3: 1 decision, ~2 min → Faster decisions

**Context**:
Edge cases not covered in documentation:
- Function accepting `Path` parameter but not reading it
- Functions using `datetime.now()` or `random`
- Logging/stderr output

**Decision Pattern**:
| Function | My Guess | Actual | Time Spent |
|----------|----------|--------|------------|
| validate_path(p: Path) | Core? | Core ✓ | 5 min |
| read_config(p: Path) | Shell | Shell ✓ | 2 min |
| log_error(msg: str) | ??? | Shell | 15 min (re-read docs) |
| format_timestamp(dt) | Core? | Core ✓ | 3 min |

**Current status**: Ongoing learning, improving with experience

**Suggested Improvement**:
- Decision flowchart in INVAR.md
- More edge case examples in `.invar/examples/core_shell.py`
- Guard could hint: "This looks like Shell (uses logging)"

---

## ✅ What Worked Well

### 1. `invar_sig` for quick contract lookup

**Usage**: 18 times (most used tool)
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

**User experience**:
> "This is my go-to tool. Saves tons of time vs opening files. I now check contracts before writing any Core function."

---

### 2. Guard auto-fix suggestions

**Fixed automatically**: 5 issues
- 3x `missing_contract` → Guard suggested contracts based on type signatures
- 2x `redundant_type_contract` → Guard explained semantic constraint needed

**User experience**:
> "When Guard suggests fixes, I learn the pattern. By the 3rd similar error, I stopped making that mistake. The suggestions are educational, not just fixes."

---

### 3. Contract-first workflow (USBV)

**Followed**: Understand → Specify → Build → Validate
**Result**: 0 contract violations caught by CrossHair in Session 3

**User experience**:
> "Writing contracts before code felt slow at first (Session 1), but by Session 3, Guard caught zero violations. Saved debugging time. The upfront investment paid off."

---

## 🤔 Confusion Points

### 1. @post cannot access parameters

**What I tried** (wrong):
```python
@pre(lambda x: x > 0)
@post(lambda result: result > x)  # ERROR: 'x' not available!
def double(x: int) -> int:
    return x * 2
```

**Error**:
```
NameError: name 'x' is not defined
```

**What worked**:
```python
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)  # Only access 'result'
def double(x: int) -> int:
    return x * 2
```

**Gap**: CLAUDE.md "Contract Rules" section mentions this, but I skimmed it and missed the detail. Could be more prominent.

---

### 2. Deal vs invar_runtime contracts

**Confusion**: When to use `from deal import pre` vs `from invar_runtime import pre`?

**What I learned** (after trial and error):
- `deal.pre` → Lambda-based contracts: `@pre(lambda x: x > 0)`
- `invar_runtime.pre` → Pre-built contract objects: `@pre(NonEmpty())`

**Gap**: This distinction not explained in INVAR.md "Critical Rules" section. Found it in examples after searching.

---

## 🔄 Workarounds Used

| Issue | Workaround | Frequency |
|-------|------------|-----------|
| Guard timeout | `--changed` + manual spot checks | 12 times |
| Core/Shell confusion | Copy from examples instead of thinking | 5 times |
| Contract syntax | Copy-paste from `.invar/examples/` | 7 times (Sessions 1-2) |

---

## 💡 Improvement Suggestions

### High Priority

1. **Incremental Guard mode**
   - Problem: Full project scan too slow (3-5 minutes)
   - Solution: Only verify changed functions + their callers
   - Benefit: 10x speedup for iterative development

2. **Contextual error messages**
   - Problem: Errors say WHAT but not HOW
   - Solution: Include example link + fix hint in error
   - Benefit: Reduce "search for examples" friction

3. **Core/Shell decision tree**
   - Problem: Edge cases unclear
   - Solution: Flowchart in INVAR.md + more examples
   - Benefit: Faster decisions, less re-reading

### Medium Priority

4. **Interactive tutorial for first-time users**
   - Problem: Learning curve steep (Session 1 had 5 contract errors)
   - Solution: `invar tutorial` command with guided examples
   - Benefit: Faster onboarding

5. **Guard progress indicator**
   - Problem: No feedback during long runs (anxiety-inducing)
   - Solution: Show "Checking file 45/120..." with ETA
   - Benefit: Less anxiety, can estimate wait time

6. **Contract snippet library**
   - Problem: Repetitive contract patterns (e.g., "non-empty string")
   - Solution: `invar snippet list` with common patterns
   - Benefit: Copy-paste correct patterns quickly

### Low Priority

7. **Guard performance dashboard**
   - Problem: Can't see what's slow
   - Solution: `--profile` flag showing time per rule/file
   - Benefit: Optimize workflow, identify bottlenecks

---

## 📈 Daily Summary

### High-Frequency Issues (Top 3)
1. **Guard performance** - 12 occurrences, still blocking
2. **Contract syntax** - 7 occurrences, now resolved ✓
3. **Core/Shell decision** - 5 occurrences, ongoing learning

### Learning Progress
| Issue | Session 1 | Session 2 | Session 3 | Trend |
|-------|-----------|-----------|-----------|-------|
| Contract syntax | 5 errors | 2 errors | 0 errors | ✅ Learned |
| Core/Shell | Confused (15 min) | Still unsure (5 min) | Clearer (2 min) | 📈 Improving |
| Guard usage | Blocked | Found workaround | Using workaround | ⚠️ Not fixed |

### Sentiment Evolution
- **Morning (Session 1)**: Frustrated (Guard blocks progress, contract errors)
- **Afternoon (Session 2)**: Adapting (workarounds found, fewer errors)
- **Evening (Session 3)**: Productive (main friction remains but manageable)

---

## 🎯 Session Success Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Task completed | ✅ Yes | Success |
| Guard final pass | ✅ 0 errors | Success |
| Time to first Guard pass | 2.5 hours | Could be faster |
| Stuck on Invar issues | ~45 min total | Acceptable |
| Would recommend Invar | ✅ Yes | Positive overall |

---

## 📝 Additional Notes

- First time using `invar refs` - worked great for finding TypeScript symbol usage
- Didn't use `invar map` much this session - not sure when it's better than `invar sig`
- Skill system (`/develop`, `/review`) works smoothly - no issues
- USBV workflow feels natural by Session 3 - initial friction worth it

---

## 🔒 Privacy Notice

This feedback document is stored locally in `.invar/feedback/`.
You control what (if anything) to share with Invar maintainers.

**To share feedback**:
1. Review this document
2. Remove any sensitive project details
3. Submit via GitHub issue or email to invar-maintainers@example.com

---

*Generated by `/invar-reflect` v1.0*
*Last updated: 2026-01-03 18:15*
