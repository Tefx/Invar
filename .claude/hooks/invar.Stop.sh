#!/bin/bash
# Invar Stop Hook
# Protocol: v5.0 | Generated: 2025-12-30
# DX-57: Session cleanup and unverified changes warning

# Use session-specific state
STATE_DIR="${CLAUDE_STATE_DIR:-/tmp/invar_hooks_$(id -u)}"
CHANGES_FILE="$STATE_DIR/changes"

# Check for unverified changes
if [[ -f "$CHANGES_FILE" ]]; then
  CHANGE_COUNT=$(wc -l < "$CHANGES_FILE" 2>/dev/null | tr -d ' ' || echo 0)
  if [[ $CHANGE_COUNT -gt 0 ]]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Invar: $CHANGE_COUNT Python files not verified"
    echo "   Run before commit: invar_guard --changed"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  fi
fi

# Cleanup session state
rm -rf "$STATE_DIR" 2>/dev/null
