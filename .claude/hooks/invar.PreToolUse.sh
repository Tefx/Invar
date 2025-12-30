#!/bin/bash
# Invar PreToolUse Hook
# Protocol: v5.0 | Generated: 2025-12-30
# DX-57: Smart blocking with auto-escape for pytest/crosshair

TOOL_NAME="$1"
TOOL_INPUT="$2"

# Check if hooks are disabled
[[ -f ".claude/hooks/.invar_disabled" ]] && exit 0

# Only process Bash commands
[[ "$TOOL_NAME" != "Bash" ]] && exit 0

# Parse command from JSON input
# Primary: jq (accurate), Fallback: grep/sed (basic)
if command -v jq &>/dev/null; then
  CMD=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)
else
  # Fallback: Extract command field using grep/sed (handles simple cases)
  CMD=$(echo "$TOOL_INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*: *"\(.*\)"/\1/')
fi
[[ -z "$CMD" ]] && exit 0

# ============================================
# pytest blocking with smart escape
# ============================================
if echo "$CMD" | grep -qE '\bpytest\b|python.*-m\s+pytest\b'; then

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
