#!/bin/bash
# Invar PostToolUse Hook
# Protocol: v5.0 | Generated: 2025-12-30
# DX-57: Git-based change detection with fallback

TOOL_NAME="$1"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Use session-specific state directory
STATE_DIR="${CLAUDE_STATE_DIR:-/tmp/invar_hooks_$(id -u)}"
mkdir -p "$STATE_DIR" 2>/dev/null

CHANGES_FILE="$STATE_DIR/changes"
LAST_GUARD="$STATE_DIR/last_guard"
LAST_CHECK_MARKER="$STATE_DIR/last_check"

# ============================================
# Reset state on guard run (MCP or CLI)
# ============================================
# MCP: invar_guard tool call
if [[ "$TOOL_NAME" == "mcp__invar__invar_guard" ]]; then
  date +%s > "$LAST_GUARD"
  rm -f "$CHANGES_FILE"
  touch "$LAST_CHECK_MARKER"
  exit 0
fi

# CLI: Bash command containing "invar guard"
if [[ "$TOOL_NAME" == "Bash" ]]; then
  TOOL_INPUT="$2"
  if echo "$TOOL_INPUT" | grep -qE '"command"[^}]*invar\s+guard'; then
    date +%s > "$LAST_GUARD"
    rm -f "$CHANGES_FILE"
    touch "$LAST_CHECK_MARKER"
    exit 0
  fi
fi

# ============================================
# Detect changes (git with fallback)
# ============================================
is_git_repo() {
  git rev-parse --git-dir >/dev/null 2>&1
}

detect_changes() {
  if is_git_repo; then
    # Primary: Git-based detection (includes staged + unstaged)
    { git diff --name-only -- '*.py' 2>/dev/null; git diff --cached --name-only -- '*.py' 2>/dev/null; } | sort -u
  elif [[ -f "$LAST_CHECK_MARKER" ]]; then
    # Fallback: Timestamp-based detection (approximate)
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
if grep -qE "/core/|/contracts/" "$CHANGES_FILE" 2>/dev/null; then
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
