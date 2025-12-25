# Session Start: Check-In Protocol

> **"No visible check-in = Session not started."**

## Quick Reference

Every agent session begins with Check-In:

```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

This is displayed in your **first message** to the user.

## The Check-In Protocol

### Steps

1. **Execute `invar guard --changed`**
   - Verify current project state
   - Identify any existing violations

2. **Execute `invar map --top 10`**
   - Find entry points
   - Understand project structure

3. **Display one-line summary**
   ```
   ✓ Check-In: guard PASS | top: parse_file, check_rules
   ```

4. **Read `.invar/context.md`**
   - Project state
   - Lessons learned
   - Current blockers

### Check-In Format

```
✓ Check-In: guard <STATUS> | top: <entry1>, <entry2>
```

| Field | Value | Meaning |
|-------|-------|---------|
| STATUS | PASS | All checks passed |
| STATUS | FAIL | Errors exist (show count) |
| top | entries | Top 2 entry points by reference count |

### Examples

```
✓ Check-In: guard PASS | top: main, process_request

✓ Check-In: guard FAIL (3 errors) | top: cli, api_handler

✓ Check-In: guard PASS | top: (no symbols found)
```

## Why Check-In?

### 1. Establish Project State

Before working, know:
- Is the project healthy?
- What are the entry points?
- What lessons apply?

### 2. Signal Session Start

The user sees:
- Agent has initialized correctly
- Invar tools are working
- Agent understands the project

### 3. Context Economy

Check-In provides:
- Quick overview (not reading all files)
- Entry points for navigation
- Existing violations to address

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
  ✓ Check-In: guard PASS | top: main, cli

... work happens ...

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

### On Check-In

If `invar guard --changed` shows errors:

```
✓ Check-In: guard FAIL (3 errors) | top: main, cli
```

Then:
1. Report the existing errors to user
2. Ask if they want to fix first
3. Proceed with caution (don't add more errors)

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

## Current State
- Status: Feature complete
- Version: 1.0.2
- Blockers: None

## Lessons Learned
1. Always use AST for code detection
2. String matching causes false positives
3. ...

## Technical Debt
- None (as of v0.7.1)
```

### Using Context

Read context.md during Check-In to:
- Understand project history
- Avoid repeating mistakes
- Apply learned lessons

## MCP Server Tools

When using MCP, equivalent tools:

| CLI Command | MCP Tool |
|-------------|----------|
| `invar guard --changed` | `invar_guard(changed=true)` |
| `invar map --top 10` | `invar_map(top=10)` |
| `invar sig <file>` | `invar_sig(file="<file>")` |

### MCP Check-In Example

```python
# Execute via MCP
guard_result = invar_guard(changed=True)
map_result = invar_map(top=10)

# Format output
status = "PASS" if guard_result.errors == 0 else f"FAIL ({guard_result.errors} errors)"
top_entries = ", ".join(map_result.top[:2])

print(f"✓ Check-In: guard {status} | top: {top_entries}")
```

## Configuration

### In INVAR.md

The Check-In format is defined in INVAR.md v3.27:

```markdown
## Check-In (Required)

Your first message MUST display:
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

### In CLAUDE.md

Project-specific additions:

```markdown
## Check-In

After standard Check-In, also read:
- `.invar/context.md` for lessons
- `docs/DESIGN.md` for architecture
```

## Troubleshooting

### No Symbols Found

```
✓ Check-In: guard PASS | top: (no symbols found)
```

This means:
- New project with no code yet
- Or `invar map` couldn't parse files

Proceed normally; map will populate as code is added.

### Guard Not Available

```
✓ Check-In: guard N/A | project not initialized
```

Run `invar init` to initialize the project.

### Context File Missing

If `.invar/context.md` doesn't exist:
- Project may not be fully set up
- Create it or ask user about project state

## See Also

- [USBV Workflow](./usbv.md) - Full development workflow
- [INVAR.md Check-In section](../../INVAR.md) - Protocol definition
- [Verification Overview](../verification/README.md) - What guard checks
