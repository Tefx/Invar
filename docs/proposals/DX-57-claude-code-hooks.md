# DX-57: Claude Code Hooks Integration

**Status:** Ready for Implementation
**Created:** 2025-12-27
**Updated:** 2025-12-28
**Dependencies:** DX-54 (Context Management), DX-42 (Workflow Routing), DX-58 (Document Structure)
**Related:** DX-60 (Structured Rules SSOT) will optimize token usage post-implementation

## Problem Statement

### Current State

Invar provides MCP tools (`invar_guard`, `invar_sig`, `invar_map`) but relies on documentation and system prompts for enforcement. This creates several issues:

```
┌─────────────────────────────────────────────────────────────┐
│                 Current Enforcement Model                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CLAUDE.md docs  ──→  Agent reads  ──→  Agent may forget     │
│                            ↓                                 │
│                    ~50% tool compliance                      │
│                    ~40% workflow compliance                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Problems Identified

#### 1. Long Context Protocol Forgetting (Critical)

From Lesson #29: Agent skips workflows in long conversations.

```
Message 1-10:  Agent follows USBV, uses invar_guard
Message 11-20: Agent starts using pytest "out of habit"
Message 21+:   Agent forgets Check-In/Final requirements
```

**Root cause:** No mechanism to refresh protocol in long conversations.

#### 2. Wrong Tool Selection

Despite MCP tools being available:

| Desired | Actual | Frequency |
|---------|--------|-----------|
| invar_guard | pytest | ~30% |
| invar_sig | Read full file | ~40% |
| invar_map | Grep "def " | ~50% |

**Root cause:** Habit over methodology. Documentation doesn't change behavior.

#### 3. No Verification Reminder After Edits

Agent modifies Python files but forgets to run `invar_guard` before claiming "done".

**Root cause:** No feedback loop between edit and verify actions.

### DX-16 Analysis Recap

| Enforcement Level | Mechanism | Compliance Rate |
|-------------------|-----------|-----------------|
| Level 1: Documentation | CLAUDE.md | ~10% |
| Level 2: Skills | /develop, /review | ~20% |
| Level 3: **Hooks** | PreToolUse, etc. | **~95%** |
| Level 4: MCP Server | Tool availability | ~50-60% |

**Key insight:** Level 3 (Hooks) is the only mechanism that can **physically prevent** incorrect behavior.

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Invar Hooks Architecture                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: Smart Blocking (PreToolUse)                        │
│  ├─ Block: pytest, crosshair → redirect to invar_guard       │
│  ├─ Auto-escape: debugging flags, external tests             │
│  └─ Stability: ⭐⭐⭐⭐⭐ (command names are stable)              │
│                                                              │
│  Layer 2: Effect Detection (PostToolUse)                     │
│  ├─ Primary: git diff (tool-agnostic)                        │
│  ├─ Fallback: timestamp-based (non-git projects)             │
│  ├─ Smart triggers: 3+ files, core/ changes, time threshold  │
│  └─ Stability: ⭐⭐⭐⭐⭐ (graceful degradation)                  │
│                                                              │
│  Layer 3: Protocol Refresh (UserPromptSubmit)                │
│  ├─ Progressive injection based on message count             │
│  ├─ Keyword-triggered reminders                              │
│  ├─ Full INVAR.md injection (~1,800t) for true SSOT          │
│  └─ Stability: ⭐⭐⭐⭐⭐ (content always matches protocol)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

| Principle | Rationale |
|-----------|-----------|
| Detect effects, not tools | Future tools won't break hooks |
| Block with smart escape | Understand intent, not blindly block |
| Suggest for preferences | Only block clearly wrong actions |
| Progressive disclosure | Minimize token overhead |
| Graceful degradation | Works without git, just with reduced capability |
| User hooks priority | Never overwrite user customizations |

### Block vs Suggest: Agent-Native Analysis

From honest agent self-reflection:

| Action Type | Enforcement | Rationale |
|-------------|-------------|-----------|
| pytest/crosshair | **Block** | Clearly wrong when invar_guard exists |
| Read .py for structure | Suggest | Not wrong, just suboptimal |
| Grep for functions | Suggest | Could be valid exploration |
| Long time without guard | Suggest | Timing is contextual |

**Key insight:** Block forces immediate learning. Suggestions are often acknowledged but not acted upon.

## Hook Specifications

### 1. PreToolUse: Smart Blocking with Auto-Escape

```bash
#!/bin/bash
# .claude/hooks/invar.PreToolUse.sh

TOOL_NAME="$1"
TOOL_INPUT="$2"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Only process Bash commands
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

CMD=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)
[[ -z "$CMD" ]] && exit 0

# ============================================
# pytest blocking with smart escape
# ============================================
if echo "$CMD" | grep -qE '\bpytest\b|python.*-m\s+pytest'; then

  # Auto-escape 1: Debugging mode (--pdb, --debug, --tb=long)
  if echo "$CMD" | grep -qE '\-\-pdb|\-\-debug|\-\-tb='; then
    echo "⚠️ pytest debugging allowed. Run invar_guard after."
    exit 0
  fi

  # Auto-escape 2: External/vendor tests
  if echo "$CMD" | grep -qE 'vendor/|third_party/|external/|node_modules/'; then
    exit 0
  fi

  # Auto-escape 3: Explicit coverage collection
  if echo "$CMD" | grep -qE '\-\-cov'; then
    echo "⚠️ pytest coverage allowed. Run invar_guard for contract verification."
    exit 0
  fi

  # Auto-escape 4: Environment variable override
  if [[ "$INVAR_ALLOW_PYTEST" == "1" ]]; then
    exit 0
  fi

  # Default: Block with helpful message
  echo "❌ Use invar_guard instead of pytest"
  echo "   invar_guard = static + doctests + CrossHair + Hypothesis"
  echo ""
  echo "   Auto-allowed: pytest --pdb (debug), pytest --cov (coverage)"
  echo "   Manual escape: INVAR_ALLOW_PYTEST=1 pytest ..."
  exit 1
fi

# ============================================
# crosshair blocking (always redirect)
# ============================================
if echo "$CMD" | grep -qE '\bcrosshair\b'; then
  if [[ "$INVAR_ALLOW_CROSSHAIR" == "1" ]]; then
    exit 0
  fi

  echo "❌ Use invar_guard (includes CrossHair by default)"
  echo "   Manual escape: INVAR_ALLOW_CROSSHAIR=1 crosshair ..."
  exit 1
fi

exit 0
```

**Auto-Escape Matrix:**

| Scenario | Escaped? | Rationale |
|----------|----------|-----------|
| `pytest --pdb` | ✅ Yes | Debugging needs interactive pytest |
| `pytest --cov` | ✅ Yes | Coverage collection is valid use |
| `pytest vendor/` | ✅ Yes | External code, not Invar-managed |
| `pytest tests/` | ❌ No | Should use invar_guard |
| `INVAR_ALLOW_PYTEST=1` | ✅ Yes | Explicit user override |

### 2. PostToolUse: Git-Based Detection with Fallback

```bash
#!/bin/bash
# .claude/hooks/invar.PostToolUse.sh

TOOL_NAME="$1"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Use session-specific state directory
STATE_DIR="/tmp/invar_hooks_$(id -u)_$$"
mkdir -p "$STATE_DIR" 2>/dev/null

CHANGES_FILE="$STATE_DIR/changes"
LAST_GUARD="$STATE_DIR/last_guard"
LAST_CHECK_MARKER="$STATE_DIR/last_check"

# ============================================
# Reset state on guard run
# ============================================
if [[ "$TOOL_NAME" == "mcp__invar__invar_guard" ]]; then
  date +%s > "$LAST_GUARD"
  rm -f "$CHANGES_FILE"
  touch "$LAST_CHECK_MARKER"
  exit 0
fi

# ============================================
# Detect changes (git with fallback)
# ============================================
is_git_repo() {
  git rev-parse --git-dir >/dev/null 2>&1
}

detect_changes() {
  if is_git_repo; then
    # Primary: Git-based detection (accurate)
    git diff --name-only -- '*.py' 2>/dev/null
  elif [[ -f "$LAST_CHECK_MARKER" ]]; then
    # Fallback: Timestamp-based detection (approximate)
    # Find .py files modified since last check
    find . -name "*.py" -newer "$LAST_CHECK_MARKER" -type f 2>/dev/null | \
      grep -v __pycache__ | grep -v '.venv' | head -20
  fi
  # Update marker for next check
  touch "$LAST_CHECK_MARKER" 2>/dev/null
}

# Track changes
CHANGED=$(detect_changes)
if [[ -n "$CHANGED" ]]; then
  echo "$CHANGED" >> "$CHANGES_FILE"
  sort -u "$CHANGES_FILE" -o "$CHANGES_FILE" 2>/dev/null
fi

# ============================================
# Smart trigger evaluation
# ============================================
CHANGE_COUNT=$(wc -l < "$CHANGES_FILE" 2>/dev/null | tr -d ' ' || echo 0)
LAST_TIME=$(cat "$LAST_GUARD" 2>/dev/null || echo 0)
NOW=$(date +%s)
ELAPSED=$((NOW - LAST_TIME))

SHOULD_REMIND=false
REASON=""

# Trigger 1: Accumulated changes (3+ files)
if [[ $CHANGE_COUNT -ge 3 ]]; then
  SHOULD_REMIND=true
  REASON="$CHANGE_COUNT files changed"
fi

# Trigger 2: Core file changed (high priority)
if grep -qE "core/|contracts" "$CHANGES_FILE" 2>/dev/null; then
  SHOULD_REMIND=true
  REASON="core/ files modified"
fi

# Trigger 3: Time threshold (>5 min with changes)
if [[ $ELAPSED -gt 300 && $CHANGE_COUNT -gt 0 ]]; then
  SHOULD_REMIND=true
  REASON=">5 min since last guard"
fi

# Output reminder if triggered
if [[ "$SHOULD_REMIND" == "true" ]]; then
  echo ""
  echo "⚠️ Verification suggested: $REASON"
  echo "   Run: invar_guard --changed"
fi
```

**Fallback Capability Matrix:**

| Feature | With Git | Without Git |
|---------|----------|-------------|
| Change detection | ✅ Precise | ⚠️ Approximate (timestamp) |
| File list | ✅ Accurate | ⚠️ May include false positives |
| core/ detection | ✅ Works | ✅ Works |
| Error introduced | None | None (graceful degradation) |

### 3. UserPromptSubmit: Protocol Refresh (Full INVAR.md Injection)

```bash
#!/bin/bash
# .claude/hooks/invar.UserPromptSubmit.sh

USER_MESSAGE="$1"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Use session-specific state
STATE_DIR="/tmp/invar_hooks_$(id -u)_$$"
mkdir -p "$STATE_DIR" 2>/dev/null

COUNT_FILE="$STATE_DIR/msg_count"
COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$COUNT_FILE"

# ============================================
# Keyword triggers (independent of count)
# ============================================

# pytest intent → immediate correction
if echo "$USER_MESSAGE" | grep -qiE "run.*pytest|pytest.*test|用.*pytest"; then
  echo "<system-reminder>Use invar_guard, not pytest.</system-reminder>"
fi

# Implementation intent → workflow reminder (after warmup)
if [[ $COUNT -gt 3 ]]; then
  if echo "$USER_MESSAGE" | grep -qiE "^implement|^fix|^add|^实现|^修复|^添加"; then
    echo "<system-reminder>USBV: Specify contracts → Build → Validate</system-reminder>"
  fi
fi

# ============================================
# Progressive refresh based on message count
# ============================================

# Message 15: Lightweight checkpoint
if [[ $COUNT -eq 15 ]]; then
  echo "<system-reminder>"
  echo "Checkpoint: guard=verify, sig=contracts, USBV workflow."
  echo "</system-reminder>"
fi

# Message 25+: Full INVAR.md injection every 10 messages
# SSOT: Inject entire protocol to ensure no content drift
# DX-60 will optimize this to ~600 tokens while maintaining SSOT
if [[ $COUNT -ge 25 && $((COUNT % 10)) -eq 0 ]]; then
  echo "<system-reminder>"
  echo "=== Protocol Refresh (message $COUNT) ==="
  echo ""
  # Inject full INVAR.md content (generated at install time)
  # The INVAR_PROTOCOL variable is populated during hook generation
  echo "$INVAR_PROTOCOL"
  echo "</system-reminder>"
fi
```

**Hook Generation (during `invar init --claude`):**

```python
# src/invar/shell/commands/init.py

def generate_user_prompt_submit_hook(project_path: Path) -> str:
    """Generate UserPromptSubmit hook with embedded INVAR.md content."""

    # Read INVAR.md from installed location
    invar_md = (project_path / "INVAR.md").read_text()

    # Escape for bash heredoc
    invar_escaped = invar_md.replace("'", "'\"'\"'")

    # Generate hook with embedded content
    hook_template = HOOK_TEMPLATE.replace(
        'echo "$INVAR_PROTOCOL"',
        f"cat << 'INVAR_EOF'\n{invar_md}\nINVAR_EOF"
    )

    return hook_template
```

**Design Decision: Full INVAR.md Injection**

| Approach | Tokens | SSOT | Maintenance |
|----------|--------|------|-------------|
| Curated subset (~80t) | ~80 | ❌ Drift risk | High |
| Curated subset (~600t) | ~600 | ❌ Drift risk | Medium |
| **Full INVAR.md** | **~1,800** | **✅ True SSOT** | **Zero** |

**Rationale:**
- True SSOT: Injection content IS the protocol, no separate maintenance
- Zero drift risk: Content always matches INVAR.md
- Trade-off accepted: Higher token cost (~1,800 vs ~80-600) for correctness
- Future optimization: DX-60 will reduce to ~600t via structured generation while maintaining SSOT

### 4. Stop Hook (Phase 2 - Lower Priority)

```bash
#!/bin/bash
# .claude/hooks/invar.Stop.sh
# NOTE: Phase 2 implementation - terminal notification only

# Check for unverified changes
STATE_DIR="/tmp/invar_hooks_$(id -u)_$$"
CHANGES_FILE="$STATE_DIR/changes"

if [[ -f "$CHANGES_FILE" ]]; then
  CHANGE_COUNT=$(wc -l < "$CHANGES_FILE" 2>/dev/null | tr -d ' ' || echo 0)
  if [[ $CHANGE_COUNT -gt 0 ]]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Invar: $CHANGE_COUNT Python files not verified"
    echo "   Run before commit: invar guard --changed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  fi
fi

# Cleanup session state
rm -rf "$STATE_DIR" 2>/dev/null
```

**Stop Hook Value Analysis:**

| Aspect | Value |
|--------|-------|
| Can change agent behavior? | ❌ No (session ended) |
| User visibility? | ✅ Terminal output |
| Audit capability? | ✅ Can log to file |
| Priority | **Low** - Phase 2 |

**Conclusion:** Stop hook provides terminal notification and cleanup only. Cannot influence agent behavior since session has ended.

## Hook Installation Strategy

### File Naming Convention

```
.claude/hooks/
├── PreToolUse.sh           # User's hook (if exists)
├── invar.PreToolUse.sh     # Invar's hook
├── PostToolUse.sh          # User's hook (if exists)
├── invar.PostToolUse.sh    # Invar's hook
└── ...
```

**Challenge:** Claude Code may not support multiple hooks with same trigger.

### Merge Strategy

```bash
# During invar init --claude

install_hooks() {
  local HOOK_TYPE="$1"  # PreToolUse, PostToolUse, etc.
  local USER_HOOK=".claude/hooks/${HOOK_TYPE}.sh"
  local INVAR_HOOK=".claude/hooks/invar.${HOOK_TYPE}.sh"

  # Copy Invar hook
  cp "$TEMPLATE_DIR/${HOOK_TYPE}.sh" "$INVAR_HOOK"

  # If user hook exists, create wrapper
  if [[ -f "$USER_HOOK" ]]; then
    # Backup user hook
    cp "$USER_HOOK" "${USER_HOOK}.user_backup"

    # Create merged hook
    cat > "$USER_HOOK" << 'EOF'
#!/bin/bash
# Merged hook: User + Invar
# User hooks run first (higher priority)

HOOK_DIR="$(dirname "$0")"

# Run user hook first
if [[ -f "$HOOK_DIR/invar.${HOOK_TYPE}.sh.user_backup" ]]; then
  source "$HOOK_DIR/${HOOK_TYPE}.sh.user_backup" "$@"
  USER_EXIT=$?
  [[ $USER_EXIT -ne 0 ]] && exit $USER_EXIT
fi

# Run Invar hook
if [[ -f "$HOOK_DIR/invar.${HOOK_TYPE}.sh" ]]; then
  source "$HOOK_DIR/invar.${HOOK_TYPE}.sh" "$@"
fi
EOF

    echo "Merged with existing ${HOOK_TYPE}.sh (user hook has priority)"
  else
    # No user hook, create simple wrapper
    cat > "$USER_HOOK" << EOF
#!/bin/bash
# Invar hook wrapper
source "\$(dirname "\$0")/invar.${HOOK_TYPE}.sh" "\$@"
EOF
  fi

  chmod +x "$USER_HOOK" "$INVAR_HOOK"
}
```

**Priority Order:**
1. User hook runs first
2. If user hook exits non-zero, stop (user can override Invar)
3. Then Invar hook runs

### Installation via `invar init`

**New flags for DX-57:**

| Flag | Effect |
|------|--------|
| `--claude-hooks` | Install Claude Code hooks (default when `--claude`) |
| `--no-claude-hooks` | Skip Claude Code hooks installation |

**Note:** `--hooks`/`--no-hooks` refers to git pre-commit hooks (existing). `--claude-hooks`/`--no-claude-hooks` is for Claude Code hooks (DX-57).

```bash
# Full Claude Code integration with hooks
invar init --claude

# Claude Code without hooks
invar init --claude --no-claude-hooks

# Update existing project (hooks auto-updated if present)
invar init
```

**Installation output:**

```bash
# When --claude or --claude-hooks

echo "Claude Code Hooks Installation"
echo "==============================="
echo ""
echo "Hooks will:"
echo "  ✓ Block pytest/crosshair → redirect to invar_guard"
echo "  ✓ Remind to verify after code changes"
echo "  ✓ Refresh protocol in long conversations (~1,800 tokens)"
echo ""
echo "Auto-escape (no blocking):"
echo "  • pytest --pdb (debugging)"
echo "  • pytest --cov (coverage)"
echo "  • pytest vendor/ (external code)"
echo ""
echo "Manual escape: INVAR_ALLOW_PYTEST=1"
echo ""

install_hooks "PreToolUse"
install_hooks "PostToolUse"
install_hooks "UserPromptSubmit"
echo "✓ Claude Code hooks installed"
```

### Hook Update via `invar init` (Idempotent)

**Critical:** Hooks embed INVAR.md content, so they must be regenerated when protocol updates.

**Key insight:** `invar init` is idempotent (DX-55) - running it again updates managed content while preserving user customizations. Hooks follow the same pattern.

```python
# src/invar/shell/commands/init.py (extended)

def sync_claude_hooks(project_path: Path, invar_md: str) -> Result[None, str]:
    """Regenerate Claude Code hooks with current INVAR.md content."""

    hooks_dir = project_path / ".claude" / "hooks"
    if not hooks_dir.exists():
        return Success(None)  # No hooks installed

    # Check if Invar hooks are installed
    invar_hook = hooks_dir / "invar.UserPromptSubmit.sh"
    if not invar_hook.exists():
        return Success(None)  # User chose --no-claude-hooks

    # Check version in existing hook
    old_content = invar_hook.read_text()
    old_version = extract_version(old_content)  # e.g., "5.0"
    new_version = PROTOCOL_VERSION

    if old_version != new_version:
        print(f"Updating Claude hooks: v{old_version} → v{new_version}")

    # Regenerate all Invar hooks
    for hook_type in ["PreToolUse", "PostToolUse", "UserPromptSubmit"]:
        regenerate_hook(hooks_dir, hook_type, invar_md)

    return Success(None)
```

**Integration with `invar init`:**

```python
# In init() command, after sync_templates()

def init(...):
    # ... existing template sync (INVAR.md, CLAUDE.md, etc.) ...

    # DX-57: Update Claude Code hooks if installed
    if (project_path / ".claude" / "hooks" / "invar.UserPromptSubmit.sh").exists():
        invar_md = (project_path / "INVAR.md").read_text()
        sync_claude_hooks(project_path, invar_md)
```

**Version tracking in hooks:**

```bash
#!/bin/bash
# .claude/hooks/invar.UserPromptSubmit.sh
# Protocol: v5.0 | Generated: 2025-12-28

# ... hook content ...
```

**Update Flow:**

```
pip install -U invar-tools  (升级工具)
    ↓
invar init  (重新初始化，幂等)
    ↓
┌─────────────────────────────────────┐
│ init()                               │
│ ├── sync_templates()                 │
│ │   ├── INVAR.md 更新 ✓              │
│ │   ├── CLAUDE.md 更新 ✓             │
│ │   └── context.md 更新 ✓            │
│ └── sync_claude_hooks() ← NEW        │
│     ├── 检测版本变化                  │
│     ├── 重新嵌入 INVAR.md 内容        │
│     └── 保留用户 wrapper hook         │
└─────────────────────────────────────┘
```

**User Hook Preservation:**

```python
def regenerate_hook(hooks_dir: Path, hook_type: str, invar_md: str):
    """Regenerate Invar hook while preserving user customizations."""

    invar_hook = hooks_dir / f"invar.{hook_type}.sh"

    # Only regenerate invar.*.sh, never touch user's wrapper
    new_content = generate_hook_content(hook_type, invar_md)
    invar_hook.write_text(new_content)

    # Wrapper {hook_type}.sh (if exists) still sources invar.*.sh
    # User customizations in wrapper are preserved
```

### Uninstall Mechanism

```bash
# invar hooks --remove

remove_hooks() {
  echo "Removing Invar hooks..."

  for HOOK in PreToolUse PostToolUse UserPromptSubmit Stop; do
    # Remove Invar-specific hook
    rm -f ".claude/hooks/invar.${HOOK}.sh"

    # Restore user backup if exists
    if [[ -f ".claude/hooks/${HOOK}.sh.user_backup" ]]; then
      mv ".claude/hooks/${HOOK}.sh.user_backup" ".claude/hooks/${HOOK}.sh"
      echo "  Restored user ${HOOK}.sh"
    else
      # Remove wrapper if it only contained Invar hook
      if grep -q "invar.${HOOK}.sh" ".claude/hooks/${HOOK}.sh" 2>/dev/null; then
        rm -f ".claude/hooks/${HOOK}.sh"
      fi
    fi
  done

  echo "✓ Invar hooks removed"
}

# Temporary disable without removal
disable_hooks() {
  touch ".claude/hooks/.invar_disabled"
  echo "✓ Invar hooks disabled (remove .claude/hooks/.invar_disabled to re-enable)"
}

enable_hooks() {
  rm -f ".claude/hooks/.invar_disabled"
  echo "✓ Invar hooks enabled"
}
```

**Uninstall Options:**

| Command | Effect |
|---------|--------|
| `invar hooks --remove` | Permanently remove Claude Code hooks |
| `invar hooks --disable` | Temporarily disable (create .invar_disabled) |
| `invar hooks --enable` | Re-enable disabled hooks |
| `invar init --claude --no-claude-hooks` | Install without Claude Code hooks |
| `invar init` | Update project (auto-updates hooks if present) |

## Implementation Plan

### Phase 1: Core Hooks (Priority)

1. Create hook scripts in `src/invar/templates/hooks/`
2. Implement smart escape logic in PreToolUse
3. Implement git + fallback detection in PostToolUse
4. Implement progressive refresh in UserPromptSubmit (embed full INVAR.md)
5. Add hook installation to `invar init --claude` (new `--claude-hooks` flag)
6. Add `invar hooks` subcommand for management
7. **Integrate hook update into `invar init` (idempotent, DX-55 pattern)**

### Phase 2: Refinement

1. Add Stop hook for terminal notification
2. Tune trigger thresholds based on feedback
3. Add optional `.invar/hooks.toml` configuration
4. Document hook customization

### Phase 3: Testing

1. Test with git and non-git projects
2. Test hook merging with user hooks
3. Test auto-escape scenarios
4. Measure token overhead in long conversations

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Tool compliance (invar_guard vs pytest) | ~50% | >90% |
| Workflow compliance (USBV) | ~40% | >80% |
| Protocol retention in long sessions | ~30% | >70% |
| Token overhead per 50-msg session | N/A | ~5,700 (DX-60: ~2,000) |
| User hook compatibility | N/A | 100% |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Hooks too noisy | Smart triggers, progressive disclosure |
| Git not available | Timestamp-based fallback |
| Blocks legitimate pytest use | Auto-escape for debugging/coverage |
| Overwrites user hooks | Merge strategy with user priority |
| User wants to disable | Easy disable/remove commands |
| Performance impact | Lightweight bash, no heavy processing |

## Appendix: Token Overhead Analysis

### Current Design (Full INVAR.md Injection)

| Messages | Injections | Estimated Tokens |
|----------|------------|------------------|
| 1-5 | 0 | 0 |
| 6-14 | ~2 keyword triggers | ~40 |
| 15 | 1 checkpoint | ~30 |
| 16-24 | ~2 keyword triggers | ~40 |
| 25 | 1 full INVAR.md | ~1,800 |
| 26-34 | ~2 keyword triggers | ~40 |
| 35 | 1 full INVAR.md | ~1,800 |
| **Total (35 msgs)** | | **~3,750 tokens** |

### Token Trade-off Analysis

| Metric | Curated (~80t) | Full INVAR.md (~1,800t) |
|--------|----------------|-------------------------|
| SSOT | ❌ Separate file | ✅ True SSOT |
| Maintenance | Manual sync | Zero |
| Drift risk | High | None |
| 50-msg session cost | ~250 tokens | ~5,700 tokens |
| Coverage | ~40% rules | 100% rules |
| Compliance improvement | +20-30% | +45-55% |

**Decision:** Accept higher token cost for true SSOT and zero maintenance. DX-60 will reduce to ~600t while maintaining SSOT through structured generation.

### Future Optimization (DX-60)

| Phase | Approach | Tokens | SSOT |
|-------|----------|--------|------|
| DX-57 (current) | Full INVAR.md | ~1,800 | ✅ |
| DX-60 (future) | Generated from YAML | ~600 | ✅ |

DX-60 will extract rules to structured YAML and generate both INVAR.md and injection content, reducing tokens by 67% while maintaining single source of truth.

## References

- DX-16: Agent Tool Enforcement
- DX-54: Agent-Native Context Management
- DX-58: Document Structure Optimization
- **DX-60: Structured Rules SSOT** (future optimization for token reduction)
- Lesson #29: Agent Workflow Compliance
- Claude Code Hooks Documentation
