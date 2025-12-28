---
name: develop
description: Implementation phase following USBV workflow. Use when task is clear and actionable - "add", "implement", "create", "fix", "update", "build", "write". Requires Check-In at start and Final at end.
_invar:
  version: "5.0"
  managed: skill
---
<!--invar:skill-->

# Development Mode

> **Purpose:** Implement solution following USBV workflow with verification.

## Entry Actions (REQUIRED)

### Context Refresh (DX-54)

Before any workflow action:
1. Read `.invar/context.md` (especially Key Rules section)
2. Display routing announcement

### Routing Announcement

```
📍 Routing: /develop — [trigger detected, e.g. "add", "fix", "implement"]
   Task: [user's request summary]
```

### Simple Task Detection

If task appears simple (4+ signals: single file, clear target, additive change, <50 lines):

```
📊 Simple task (1 file, ~N lines).
   Auto-orchestrate: investigate → develop → validate?
   [Y/N]
```

- Y → Execute full cycle without intermediate confirmations
- N → Proceed with normal USBV checkpoints
- No response → Default to step-by-step (safe)

## USBV Workflow

### 1. UNDERSTAND

- **Intent:** What exactly needs to be done?
- **Inspect:** Use `invar_sig` to see existing contracts
- **Context:** Read relevant code, understand patterns
- **Constraints:** What must NOT change?

### 2. SPECIFY

- **Contracts FIRST:** Write `@pre`/`@post` before implementation
- **Doctests:** Add examples for expected behavior
- **Design:** Decompose complex tasks into sub-functions

```python
# SPECIFY before BUILD:
@pre(lambda x: x > 0)
@post(lambda result: result >= 0)
def calculate(x: int) -> int:
    """
    >>> calculate(10)
    100
    """
    ...  # Implementation comes in BUILD
```

#### Function-Level Gates (DX-63)

When creating new modules, use **incremental development**:

1. Create ONE file
2. Write contracts for all functions (body = `...`)
3. Run `invar_guard(contracts_only=true)` to verify coverage
4. Implement functions
5. Run `invar_guard(changed=true)`
6. Proceed to next file

❌ Do NOT create multiple file skeletons at once
❌ Do NOT "structure first, fill later"

**TodoList Pattern: Interleaved SPECIFY/BUILD**

For each function:
```
□ [SPECIFY] Write contract for validate_input
□ [BUILD] Implement validate_input
□ [SPECIFY] Write contract for process_data
□ [BUILD] Implement process_data
```

NOT:
```
□ [SPECIFY] Write all contracts
□ [BUILD] Implement all functions
```

**Violation Self-Check** — Before writing ANY implementation code:
1. "Have I written the contract for THIS function?"
2. "Have I shown it in my response?"
3. "Have I run `invar_guard(contracts_only=true)`?"
If any NO → Stop. Write contract first.

### 3. BUILD

**For complex tasks:** Enter Plan Mode first, get user approval.

**Implementation rules:**
- Follow the contracts written in SPECIFY
- Run `invar_guard(changed=true)` frequently
- Commit after each logical unit

**Commit format:**
```bash
git add . && git commit -m "feat: [description]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 4. VALIDATE

- Run `invar_guard()` (full verification)
- All TodoWrite items complete
- Integration works (if applicable)

## Task Batching

For multiple tasks:
1. Create TodoWrite with all items upfront
2. Execute sequentially (not parallel)
3. After each task:
   - Commit changes
- Run `invar_guard(changed=true)`
- Update TodoWrite
4. **Limits:** Max 5 tasks OR 4 hours OR Guard failure

## Failure Handling

| Guard Result | Action |
|--------------|--------|
| Static fixable (missing contract) | Auto-fix, retry (max 2) |
| Test failure | Report to user, ask for guidance |
| Contract violation | Report, suggest `/investigate` |
| Repeated failure | Stop, ask user |

## Common Guard Errors

Quick reference for resolving common Guard errors:

| Error | Cause | Quick Fix |
|-------|-------|-----------|
| `forbidden_import: io` | I/O library in Core | Use `iter(s.splitlines())` not `io.StringIO` |
| `forbidden_import: os` | os module in Core | Accept `Path` as parameter instead |
| `forbidden_import: pathlib` | pathlib in Core | Accept `Path` or `str` as parameter |
| `internal_import` | Import inside function | Move import to module top |
| `missing_contract` | Core function without @pre/@post | Add contract before implementation |
| `empty_contract` | Contract with no condition | Add meaningful condition |
| `redundant_type_contract` | Contract only checks types | Add semantic constraints (bounds, relationships) |
| `partial_contract` | Only some params validated | Validate all params or document why partial |
| `file_size` | File > 500 lines | Extract functions to new module |
| `shell_result` | Shell function missing Result | Return `Result[T, E]` from `returns` |

**Tip:** For `missing_contract`, Guard automatically suggests contracts based on parameter types.
Check the "Suggested:" line in Guard output.

**Note:** Use `from deal import pre, post` for lambda-based contracts.
`invar_runtime.pre/post` are for Contract objects like `NonEmpty`.

## Timeout Handling

| Threshold | Duration | Action |
|-----------|----------|--------|
| Warning | 3 hours (75%) | Soft warning with options |
| Hard stop | 4 hours (max) | Save state, exit |

**75% Warning:**
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

   Completed: [N]/[M] tasks
   Current task: [description] - [%] complete

   Saving state for resume. Run '/develop --resume' to continue.
```

## Exit Actions (REQUIRED)

### Final

```python
invar_guard()
```


**Display:**
```
✓ Final: guard [PASS/FAIL] | [errors] errors, [warnings] warnings
```

### Auto-Review (DX-41)

If Guard outputs `review_suggested`:

```
⚠ review_suggested: [reason]

📍 Routing: /review — review_suggested triggered
   Task: Review [N files changed]
```

Proceed directly to /review skill. User can say "skip" to bypass.

## Phase Visibility (DX-51)

**USBV phases must be visually distinct.** On each phase transition, display a phase header:

### Phase Header Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Compact Format (brief updates)

```
📍 VALIDATE — Running guard...
```

### Three-Layer Visibility

| Layer | What | Tool |
|-------|------|------|
| Skill | `/develop` | Routing announcement |
| Phase | `SPECIFY (2/4)` | Phase header (this section) |
| Tasks | Concrete items | TodoWrite |

**Phase headers are SEPARATE from TodoWrite.**
- Phase = where you are in workflow (visible in output)
- TodoWrite = what tasks need doing (visible in status panel)

**BUILD is internal work** — show header but no detailed breakdown.

## Tool Selection

| I want to... | Use |
|--------------|-----|
| See contracts | `invar_sig <file>` |
| Find entry points | `invar_map --top 10` |
| Verify code | `invar_guard` |
| Edit symbol | Serena `replace_symbol_body` |
| Add after symbol | Serena `insert_after_symbol` |
| Rename symbol | Serena `rename_symbol` |

## Example

```
User: "Add input validation to parse_source"

Agent:
📍 Routing: /develop — "add" trigger detected
   Task: Add input validation to parse_source

✓ Check-In: Invar | main | clean

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → UNDERSTAND (1/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Current: accepts any string
- Need: reject whitespace-only strings
- File: src/invar/core/parser.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → SPECIFY (2/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pre(lambda source, path: len(source.strip()) > 0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → BUILD (3/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Implementation...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 /develop → VALIDATE (4/4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ guard PASS | 0 errors, 1 warning

✓ Final: guard PASS | 0 errors, 1 warning
```
<!--/invar:skill--><!--invar:extensions-->
<!-- ========================================================================
     EXTENSIONS REGION - USER EDITABLE
     Add project-specific extensions here. This section is preserved on update.

     Examples of what to add:
     - Project-specific validation steps
     - Custom commit message formats
     - Additional tool integrations
     - Team-specific workflows
     ======================================================================== -->
<!--/invar:extensions-->
