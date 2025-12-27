# Session Start: Check-In Protocol

> **"No visible check-in = Session not started."**

## Quick Reference

Every agent session begins with Check-In:

```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

This is displayed in your **first message** to the user.

## The Check-In Protocol (DX-54)

### Steps

1. **Read `.invar/context.md`**
   - Key Rules (quick reference)
   - Current State
   - Lessons Learned

2. **Display one-line summary**
   ```
   ✓ Check-In: MyProject | main | clean
   ```

**Do NOT execute guard or map at Check-In.**
Guard is for VALIDATE phase and Final only.

### Check-In Format

```
✓ Check-In: [project] | [branch] | [clean/dirty]
```

| Field | Value | Meaning |
|-------|-------|---------|
| project | name | Project name |
| branch | name | Current git branch |
| status | clean | No uncommitted changes |
| status | dirty | Uncommitted changes exist |

### Examples

```
✓ Check-In: MyProject | main | clean

✓ Check-In: Invar | feature/dx-54 | dirty

✓ Check-In: API-Server | develop | clean
```

## Why Check-In Changed (DX-54)

### Before: Guard at Check-In
```
✓ Check-In: guard PASS | top: main, cli  # OLD FORMAT
```

**Problems:**
- Ran verification before understanding context
- Guard is for VALIDATE phase, not session start
- Created confusion about when to run guard

### After: Context at Check-In
```
✓ Check-In: MyProject | main | clean  # NEW FORMAT
```

**Benefits:**
- Shows project state immediately
- Guard reserved for VALIDATE phase
- Clearer separation of concerns

## The Final Protocol

Implementation tasks end with Final:

```
✓ Final: guard PASS | 0 errors, 2 warnings
```

### Final Format

```
✓ Final: guard <STATUS> | <errors> errors, <warnings> warnings
```

### Check-In + Final Pair

```
Session Start:
  ✓ Check-In: MyProject | main | clean

... USBV workflow happens ...

VALIDATE phase:
  Run invar guard

Session End:
  ✓ Final: guard PASS | 0 errors, 0 warnings
```

**Both required.** Missing either = incomplete task.

## Task Completion Criteria

A task is complete only when **ALL** conditions are met:

| Criterion | How to Verify |
|-----------|---------------|
| Check-In displayed | First message shows `✓ Check-In:` |
| Intent stated | Task goal explicitly documented |
| Contract before implementation | USBV followed |
| Final displayed | Last message shows `✓ Final:` |
| User requirement satisfied | Actual goal achieved |

**Missing any = Task incomplete.**

## When Guard Fails

### On Final

If `invar guard` shows errors:

```
✓ Final: guard FAIL (1 error) | 1 error, 0 warnings
```

Then:
1. The task is NOT complete
2. Fix the error
3. Run Final again

## Context File

### Location

`.invar/context.md` in project root

### Contents

```markdown
# Project Context

## Key Rules (Quick Reference)
- Core: @pre/@post + doctests, NO I/O
- Shell: Result[T, E] return type

## Current State
- Status: Feature complete
- Version: 1.0.2
- Blockers: None

## Lessons Learned
1. Always use AST for code detection
2. String matching causes false positives
```

### Using Context

Read context.md during Check-In to:
- Understand project history
- Avoid repeating mistakes
- Apply learned lessons

## MCP Server Tools

When using MCP for VALIDATE phase:

| Purpose | MCP Tool |
|---------|----------|
| Verify code | `invar_guard()` |
| Check changed only | `invar_guard(changed=true)` |
| Find entry points | `invar_map(top=10)` |
| See contracts | `invar_sig(target="<file>")` |

### MCP Final Example

```python
# Execute via MCP during VALIDATE/Final
guard_result = invar_guard()

# Format output
if guard_result.status == "passed":
    print(f"✓ Final: guard PASS | {guard_result.errors} errors, {guard_result.warnings} warnings")
else:
    print(f"✓ Final: guard FAIL | {guard_result.errors} errors, {guard_result.warnings} warnings")
```

## Configuration

### In INVAR.md

The Check-In format is defined in INVAR.md v5.0:

```markdown
## Check-In (Required)

Your first message MUST display:
✓ Check-In: [project] | [branch] | [clean/dirty]

Do NOT execute guard or map at Check-In.
Guard is for VALIDATE phase and Final only.
```

## Troubleshooting

### Context File Missing

If `.invar/context.md` doesn't exist:
- Project may not be fully set up
- Run `invar init` to create it
- Or ask user about project state

### Guard Not Available

If Invar tools aren't installed:
- Check-In can still happen with project context
- Final verification requires Invar installation

## See Also

- [USBV Workflow](./usbv.md) - Full development workflow
- [INVAR.md Check-In section](../../INVAR.md) - Protocol definition
- [Verification Overview](../verification/index.md) - What guard checks
