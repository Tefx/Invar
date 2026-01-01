# LX-04: Multi-Agent Support Framework

**Status:** Phase 1-2 Complete (Phase 3 Cursor Pending)
**Priority:** High
**Category:** Language/Agent eXtensions
**Created:** 2025-12-29
**Updated:** 2025-12-30
**Based on:** LX-02 (research), LX-03 Phase 1 (docs), Framework Review, Pi Hook API Analysis
**Supersedes:** LX-03 Phase 2+ (template generation)
**Reduction:** 15 days → 4.5 days (leverages existing infrastructure + simplified CLI)

## Summary

Design a minimal, pragmatic multi-agent support leveraging existing Invar infrastructure (manifest.toml, sync_templates, region system) rather than building a new framework.

## Key Findings (2025-12-30 Review)

### Correct Version Flow

```
src/invar/templates/              ← SSOT (Single Source of Truth)
        │
        ├── invar dev sync        (Invar project, syntax=mcp)
        │
        └── invar init/update     (User projects, syntax=cli)
                │
                ▼
       Project files              ← Generated/synced
```

**Fix Required:** `.invar/context.md` incorrectly states "INVAR.md is the source". The templates are the true source.

### CLAUDE.md / INVAR.md Content Duplication

| Content | CLAUDE.md | INVAR.md | Issue |
|---------|-----------|----------|-------|
| Check-In | Full (16 lines) | Full (18 lines) | **Duplicate** |
| Visible Workflow | Partial | Full | Partial duplicate |
| Core/Shell | Summary table | Full + decision tree | OK (layered) |
| Contract Rules | None | Full (44 lines) | OK (INVAR.md only) |

**Recommendation:** Remove duplicates from CLAUDE.md, keep only references to INVAR.md.

### Content Gap Analysis (If Agent Only Reads CLAUDE.md)

| Source | Lines | What Agent Misses |
|--------|-------|-------------------|
| **INVAR.md** | 310 | Six Laws, Contract Rules (44 lines), Core/Shell Examples, USBV details |
| **context.md** | 163 | Task Router, Lessons Learned, Tool Priority |
| **examples/** | ~400 | Working code patterns |

**Critical Missing Content:**

| Content | Location | Impact |
|---------|----------|--------|
| **Lambda Signature Rule** | INVAR.md:106-118 | Agents write `@pre(lambda x: ...)` for `def f(x, y)` → ERROR |
| **@post Scope Limitation** | INVAR.md:136-146 | Agents write `@post(lambda r: r > x)` → ERROR (`x` not accessible) |
| **Task Router** | context.md:30-42 | Agents skip reading examples before coding |
| **Core/Shell Examples** | INVAR.md:64-103 | Agents guess patterns instead of copying working code |

**Contract Rules That Agents Miss (INVAR.md:104-147):**

```python
# WRONG (agent common mistake) - Lambda missing parameter
@pre(lambda x: x >= 0)
def calc(x: int, y: int = 0): ...

# CORRECT - Lambda must include ALL params
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# WRONG - @post cannot access function parameters
@post(lambda result: result > x)  # 'x' not available!

# CORRECT - @post only sees 'result'
@post(lambda result: result >= 0)
```

**Conclusion:** These rules MUST be inlined in CLAUDE.md critical section.

### Agent Ecosystem (Updated)

| Agent | Prompt File | Skills | MCP | Hooks | Integration |
|-------|-------------|--------|-----|-------|-------------|
| **Claude Code** | CLAUDE.md | .claude/skills/ ✅ | ✅ | Bash | Native |
| **Pi** | CLAUDE.md ✅ | .claude/skills/ ✅ | ❌ | TypeScript | Native |
| **Cursor** | .cursor/rules/*.mdc | ❌ | ✅ | JSON | MCP |
| **Aider** | CONVENTIONS.md | ❌ | ❌ | lint-cmd | Lint Hook |

**Key Insight:** Pi reads CLAUDE.md and .claude/skills/ directly. Only hooks need Pi-specific files.

## Existing Infrastructure to Leverage

### 1. Template System (Already Complete)

```
src/invar/templates/
├── manifest.toml           ← File ownership & sync rules
├── protocol/INVAR.md       ← Protocol source
├── config/CLAUDE.md.jinja  ← Jinja2 with syntax variable
├── skills/*/SKILL.md.jinja ← Skills with syntax variable
└── hooks/*.sh.jinja        ← Bash hooks
```

### 2. Sync Engine (Already Complete)

```python
# DX-56: Unified sync engine
sync_templates(path, SyncConfig(
    syntax="mcp",                    # or "cli"
    inject_project_additions=True,  # or False
))
```

### 3. Region System (Already Complete)

```markdown
<!--invar:critical-->   ← Always update
<!--invar:managed-->    ← Update managed, preserve user
<!--invar:project-->    ← Inject from project-additions.md
<!--invar:user-->       ← Preserve user content
<!--invar:skill-->      ← Skill content
<!--invar:extensions--> ← User extensions for skills
```

## Pi Hook API Analysis (2025-12-30)

### Key Discovery: `pi.send()` Supports Message Injection

Pi's hook API supports injecting messages into the conversation via `pi.send()`:

| Method | Purpose | Behavior |
|--------|---------|----------|
| `pi.send(text, attachments?)` | Inject message | If streaming → queue; else → new agent loop |
| `queue_message` RPC | Queue for next turn | Inject without triggering new prompt |
| `set_queue_mode` | Control injection | Configure how queued messages are injected |

**Source:** [Pi Hooks Documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/hooks.md)

### Capability Comparison

| Feature | Claude Code | Pi | Parity |
|---------|-------------|-----|--------|
| pytest blocking | `tool_call` block | `tool_call` block | ✅ Full |
| Protocol injection | `UserPromptSubmit` echo | `agent_start` + `pi.send()` | ✅ Full |
| Message counting | File state | Memory variable | ✅ Full |
| Long conversation support | Every 10 msgs after 25 | Every 10 msgs after 25 | ✅ Full |

**Conclusion:** Pi hooks can achieve full feature parity with Claude Code hooks.

## What's Missing (Minimal Additions)

### 1. Pi TypeScript Hooks

```
src/invar/templates/hooks/pi/
└── invar.ts.jinja
```

**Content (Full Feature Parity with Claude Code):**
```typescript
import type { HookAPI } from "@mariozechner/pi-coding-agent/hooks";

const BLOCKED_CMDS = [/^pytest\b/, /^python\s+-m\s+pytest/, /^crosshair\b/];
const ALLOWED_FLAGS = [/--pdb/, /--cov/, /--debug/];

// Protocol content injected via Jinja
const INVAR_PROTOCOL = `{{ invar_protocol | escape_js }}`;

export default function(pi: HookAPI) {
  let msgCount = 0;

  // ============================================
  // Long Conversation Protocol Refresh
  // ============================================
  pi.on("agent_start", async () => {
    msgCount++;

    // Message 15: Lightweight checkpoint
    if (msgCount === 15) {
      pi.send("<system-reminder>Checkpoint: guard=verify, sig=contracts, USBV workflow.</system-reminder>");
    }

    // Message 25+: Full protocol injection every 10 messages
    if (msgCount >= 25 && msgCount % 10 === 0) {
      pi.send(`<system-reminder>
=== Protocol Refresh (message ${msgCount}) ===
${INVAR_PROTOCOL}
</system-reminder>`);
    }
  });

  // ============================================
  // pytest/crosshair Blocking
  // ============================================
  pi.on("tool_call", async (event) => {
    if (event.toolName !== "bash") return;
    const cmd = (event.input.command as string || "").trim();

    // Skip if not a blocked command
    if (!BLOCKED_CMDS.some(p => p.test(cmd))) return;

    // Allow if has debug/test flags
    if (ALLOWED_FLAGS.some(p => p.test(cmd))) return;

    return {
      block: true,
      reason: "Use `invar guard` instead of pytest/crosshair."
    };
  });
}
```

**Key Features:**
1. **Protocol injection** via `pi.send()` — same cadence as Claude Code (msg 15, 25, 35...)
2. **pytest/crosshair blocking** via `tool_call` — same logic as Claude Code
3. **Memory-based counting** — simpler than file-based state

### 2. Cursor Rules Template

```
src/invar/templates/config/cursor.mdc.jinja
```

**Content:**
```markdown
---
description: Invar verification rules
globs: ["**/*.py"]
alwaysApply: true
---

{{ critical_rules }}

## Contract Rules (Critical)

### Lambda Signature
\```python
# ❌ WRONG: Lambda only takes first parameter
@pre(lambda x: x >= 0)
def calculate(x: int, y: int = 0): ...

# ✅ CORRECT: Lambda must include ALL parameters
@pre(lambda x, y=0: x >= 0)
def calculate(x: int, y: int = 0): ...
\```

## MCP Tools

| Task | Tool |
|------|------|
| Verify | `invar_guard()` |
| Signatures | `invar_sig(target)` |
| Entry points | `invar_map()` |
```

### 3. manifest.toml Extensions

```toml
# Add agent configuration
[agents]
claude = { enabled = true }
pi = { enabled = false, hooks_lang = "typescript" }
cursor = { enabled = false, rules_format = "mdc" }

# Add new templates
[templates]
".pi/hooks/invar-guard.ts" = { src = "hooks/pi/invar-guard.ts.jinja", type = "jinja", agent = "pi" }
".cursor/rules/invar.mdc" = { src = "config/cursor.mdc.jinja", type = "jinja", agent = "cursor" }
```

### 4. CLI Extension (DX-70 Aligned)

**No new flags.** Use interactive selection (consistent with DX-70 simplification):

```bash
invar init
# → Interactive menu:
#   [x] Claude Code (full support)
#   [ ] Pi (hooks + protocol injection)
#   [ ] Cursor (MCP + rules)
#   [ ] Other (AGENT.md only)
```

**Implementation:** Extend existing questionary menu in `init.py` to include agent selection.

## Content Optimization (Phase 1)

### Problem: CLAUDE.md/INVAR.md Duplication

Current Check-In content exists in both files (~95% duplicate).

### Solution: Reference, Don't Copy

**Before (CLAUDE.md):**
```markdown
## Check-In (DX-54)

Your first message MUST display:
...
[16 lines of content]
```

**After (CLAUDE.md):**
```markdown
## Check-In

> See [INVAR.md#check-in](./INVAR.md#check-in-required) for protocol.

Display: `✓ Check-In: [project] | [branch] | [clean/dirty]`
Then read `.invar/context.md`.
```

### Inline Critical Rules (MUST Add to CLAUDE.md)

Add to `<!--invar:critical-->` section in `CLAUDE.md.jinja`:

```markdown
## ⚡ Critical Rules

| Always | Remember |
|--------|----------|
| **Verify** | `invar_guard` — NOT pytest, NOT crosshair |
| **Core** | `@pre/@post` + doctests, NO I/O imports |
| **Shell** | Returns `Result[T, E]` from `returns` library |
| **Flow** | USBV: Understand → Specify → Build → Validate |

### Contract Rules (CRITICAL)

```python
# ❌ WRONG: Lambda must include ALL parameters
@pre(lambda x: x >= 0)
def calc(x: int, y: int = 0): ...

# ✅ CORRECT: Include defaults too
@pre(lambda x, y=0: x >= 0)
def calc(x: int, y: int = 0): ...

# ❌ WRONG: @post cannot access parameters
@post(lambda result: result > x)  # 'x' not available!

# ✅ CORRECT: @post only sees 'result'
@post(lambda result: result >= 0)
```
```

**Rationale:** These two rules have the highest agent failure rate. Inlining adds ~15 lines but prevents common errors.

## Implementation Plan

### Phase 1: Content Optimization ✅ Complete

| Task | File | Change | Status |
|------|------|--------|--------|
| 1.1 | `.invar/context.md` | Fixed version flow (templates are SSOT) | ✅ |
| 1.2 | `templates/config/CLAUDE.md.jinja` | Add Contract Rules to critical section (+15 lines) | ✅ |
| 1.3 | `templates/config/CLAUDE.md.jinja` | Simplify Check-In (reference INVAR.md, -11 lines) | ✅ |
| 1.4 | `invar dev sync` | Sync changes to Invar project | ✅ |
| 1.5 | Test | Verified in isolation environment | ✅ |

**Actual Change:** +4 lines in CLAUDE.md (add +15 contract rules, reduce -11 Check-In)

### Phase 1.5: Layered Redundancy ✅ Complete

| Task | File | Change | Status |
|------|------|--------|--------|
| 1.5a | `templates/config/CLAUDE.md.jinja` | Add Task Router reference (+1 line) | ✅ |
| 1.5b | `templates/config/CLAUDE.md.jinja` | Add Core/Shell edge cases (+7 lines) | ✅ |
| 1.5c | `templates/skills/develop/SKILL.md.jinja` | Add Task Router to Entry Actions (+1 line) | ✅ |

**Actual Change:** +10 lines in CLAUDE.md, +1 line in SKILL.md develop

### Phase 2: Pi Support (1.5 days) — ✅ COMPLETE (except testing)

| Task | Output | Priority | Status |
|------|--------|----------|--------|
| 2.1 Create Pi TypeScript hook template | `templates/hooks/pi/invar.ts.jinja` | P0 | ✅ Done |
| 2.2 Implement protocol injection (`pi.send()`) | Long conversation support | P0 | ✅ Done |
| 2.3 Implement pytest/crosshair blocking | Tool call interception | P0 | ✅ Done |
| 2.4 Add `escape_js` Jinja filter | Protocol escaping for JS | P1 | ✅ Done |
| 2.5 Extend interactive menu for Pi | Agent selection in init | P1 | ✅ Done |
| 2.6 Test Pi integration | pytest blocking + protocol refresh | P1 | 🔄 Pending |
| 2.7 Documentation | docs/guides/pi.md | P2 | ✅ Done |
| 2.8 Fix Pi preview in init | FILE_CATEGORIES correction | P0 | ✅ Done |
| 2.9 Add Pi to uninstall | .pi/hooks/ removal | P1 | ✅ Done |

**Implementation Details (2025-12-31 Audit):**
- `templates/hooks/pi/invar.ts.jinja` — Full Pi hook template with:
  - `pi.send()` protocol injection (msg 15, 25, 35...)
  - `tool_call` pytest/crosshair blocking
  - Session state management
- `src/invar/shell/pi_hooks.py` (208 LOC) — Hook generation and installation:
  - `generate_pi_hook_content()` — Template rendering with protocol escaping
  - `install_pi_hooks()` — Creates `.pi/hooks/invar.ts`
  - `sync_pi_hooks()` — Updates existing hooks
  - `remove_pi_hooks()` — Cleanup for uninstall
- `src/invar/core/template_helpers.py` — `escape_for_js_template()` filter
- `init.py` line 492 calls `install_pi_hooks()`
- `uninstall.py` handles `.pi/hooks/` removal

**Remaining:**
- Test with real Pi agent (manual verification needed)

**Key Changes from Original:**
- ~~`--agent pi` flag~~ → Interactive menu (DX-70 aligned)
- Added protocol injection via `pi.send()` (major feature)
- Simplified to single hook file (pytest + protocol combined)

### Phase 3: Cursor Support (1 day)

| Task | Output | Priority |
|------|--------|----------|
| 3.1 Create Cursor .mdc template | `templates/config/cursor.mdc.jinja` | P0 |
| 3.2 Extend interactive menu for Cursor | Agent selection in init | P1 |
| 3.3 Test Cursor MCP integration | Validation | P1 |

**Note:** Cursor has no hook equivalent. Protocol refresh relies on MCP tools + rules file.

**Total: 4.5 days** (vs original 6 days, vs original-original 15 days)

## Architecture Comparison

| Aspect | Original LX-04 | Revised LX-04 (2025-12-30) |
|--------|----------------|----------------------------|
| Manifest | New JSON Schema | **Extend manifest.toml** |
| Copy-Sync | Full implementation | **Not needed** (Pi reads .claude/) |
| Templates | Jinja2 system | **Already exists** |
| Sync engine | New implementation | **Use sync_templates()** |
| Region markers | Generation markers | **Use existing <!--invar:*-->** |
| CLI flags | `--agent pi/cursor` | **Interactive menu** (DX-70) |
| Pi protocol refresh | Not planned | **`pi.send()` injection** ✨ |
| Time estimate | 15 days | **4.5 days** |

## Testing Strategy

### Test: Agent Link Following (Validated by Design)

**Question:** Will agents follow `[INVAR.md](./INVAR.md)` links?

**Answer:** Unreliably. Design already mitigates this:
- Critical rules inlined in CLAUDE.md
- Task Router uses explicit "STOP and read" prompts
- "**Must read:**" emphasis for examples

**Conclusion:** No runtime test needed. Keep critical rules in CLAUDE.md.

### Test: Task Router Works

1. Request "add a function to core/"
2. Observe: Does agent read `.invar/examples/contracts.py` first?
3. **Success criteria:** Agent shows evidence of reading example before coding

### Test: Pi Integration (Phase 2)

**Test A: pytest Blocking**
1. Run `invar init` → select Pi
2. Run `pi -p "run: pytest --version"`
3. **Success:** Command blocked with "Use invar guard instead"

**Test B: Protocol Injection (Long Conversation)**
1. Start Pi session with Invar project
2. Send 25+ messages
3. **Success:** Protocol refresh message appears at message 25, 35, etc.

**Test C: Full Workflow**
1. Run `invar init` → select Pi
2. Request: "add a function to calculate compound interest"
3. **Success:** Agent follows USBV, uses `invar guard`, contracts correct

## Risks and Mitigations

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Agent doesn't follow INVAR.md link | Medium | Keep critical rules in CLAUDE.md |
| Pi TypeScript hook compatibility | Low | Test with Pi 0.30.2+; minimal API surface |
| `pi.send()` timing issues | Low | Queue behavior documented; test streaming scenarios |
| Cursor .mdc format changes | Low | Simple template, easy to update |
| Protocol too large for injection | Low | Use same ~300 line protocol as Claude Code |

## Open Questions

1. **Session persistence:** Does Pi hook state (msgCount) persist across session restore?
   - If not, protocol refresh may trigger unexpectedly after restore
   - Mitigation: Use `session` event to reset count on restore

2. **`pi.send()` during streaming:** What happens if we call `pi.send()` while agent is streaming?
   - Documentation says "queued" — need to verify this works for protocol injection

## References

- [Pi Hooks Documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/hooks.md)
- [Pi RPC Documentation](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/rpc.md)
- [Cursor Rules](https://cursor.com/docs/context/rules)
- [DX-56: Unified Sync Engine](./completed/DX-56-template-sync.md)
- [DX-70: Init Simplification](./DX-70-init-simplification.md)
