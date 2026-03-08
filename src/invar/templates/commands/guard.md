---
_invar:
  version: "5.0"
  type: command
---

# Guard

Run Invar verification on the project and report results.

---

## Behavior

Execute `invar_guard()` and report:
- Pass/fail status
- Error count with details
- Warning count with details

**Do NOT fix issues** - just report verification results.

---

## When to Use

- Quick verification check
- Before committing changes
- After pulling changes
- To see current project health

---

## Execution

Run verification:

```
invar_guard(changed=true)
```

Or for full project verification:

```
invar_guard()
```

---

## Report Format

```
## Guard Results

**Status:** PASS / FAIL
**Errors:** N
**Warnings:** N

### Errors (if any)

| Rule | File | Line | Message |
|------|------|------|---------|
| missing_contract | src/foo.py | 42 | Function 'bar' has no @pre/@post |

### Warnings (if any)

| Rule | File | Line | Message |
|------|------|------|---------|
| function_size | src/baz.py | 15 | Function exceeds 50 lines |
```

---

## Next Steps

After reporting results:
- If PASS: No action needed
- If FAIL: User decides whether to fix issues

**Remember:** You are READ-ONLY. Report results, don't fix them.

---

Now run verification on the current project.
