<!--invar:skill version="5.0"-->
<!-- ========================================================================
     SKILL REGION - DO NOT EDIT
     This section is managed by Invar and will be overwritten on update.
     To add project-specific extensions, use the "extensions" region below.
     ======================================================================== -->
---
name: develop
description: Implementation phase following USBV workflow. Use when task is clear and actionable - "add", "implement", "create", "fix", "update", "build", "write". Requires Check-In at start and Final at end.
---

# Development Mode

> **Purpose:** Implement solution following USBV workflow with verification.

## Entry Actions (REQUIRED)

### Routing Announcement

Before any workflow action, display:

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

### Check-In

```python
invar_guard(changed=true)
invar_map(top=10)
```


**Display:**
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

**No visible Check-In = Development not started.**

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

## Visible Workflow

For complex tasks (3+ functions), show checkpoints:

```
□ [UNDERSTAND] Task description, context, constraints
□ [SPECIFY] Contracts before implementation
□ [VALIDATE] Guard results, integration status
```

**BUILD is internal work** — not shown in TodoList.

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

Agent: "Entering /develop for: Add input validation to parse_source

✓ Check-In: guard PASS | top: pre, post, Violation

□ [UNDERSTAND] Add input validation to parse_source
  - Current: accepts any string
  - Need: reject whitespace-only strings
  - File: src/invar/core/parser.py

□ [SPECIFY] Enhanced precondition
  @pre(lambda source, path: isinstance(source, str) and len(source.strip()) > 0)

[BUILD - implementing...]

□ [VALIDATE]
  - Guard: PASS (0 errors, 1 warning)
  - Tests: All passing

✓ Final: guard PASS | 0 errors, 1 warning

Development complete."
```
<!--/invar:skill--><!--invar:extensions-->
---
name: develop
description: Implementation phase following USBV workflow. Use when task is clear and actionable - "add", "implement", "create", "fix", "update", "build", "write". Requires Check-In at start and Final at end.
---

# Development Mode

> **Purpose:** Implement solution following USBV workflow with verification.

## Entry Actions (REQUIRED)

### Check-In

```python
invar_guard(changed=true)
invar_map(top=10)
```

**Display:**
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

**No visible Check-In = Development not started.**

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

**If Guard reports `review_suggested`:**
```
⚠ Review suggested. Run /review for quality check.
```

## Visible Workflow

For complex tasks (3+ functions), show checkpoints:

```
□ [UNDERSTAND] Task description, context, constraints
□ [SPECIFY] Contracts before implementation
□ [VALIDATE] Guard results, integration status
```

**BUILD is internal work** — not shown in TodoList.

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

Agent: "Entering /develop for: Add input validation to parse_source

✓ Check-In: guard PASS | top: pre, post, Violation

□ [UNDERSTAND] Add input validation to parse_source
  - Current: accepts any string
  - Need: reject whitespace-only strings
  - File: src/invar/core/parser.py

□ [SPECIFY] Enhanced precondition
  @pre(lambda source, path: isinstance(source, str) and len(source.strip()) > 0)

[BUILD - implementing...]

□ [VALIDATE]
  - Guard: PASS (0 errors, 1 warning)
  - Tests: All passing

✓ Final: guard PASS | 0 errors, 1 warning

Development complete."
```

<!--/invar:extensions-->
