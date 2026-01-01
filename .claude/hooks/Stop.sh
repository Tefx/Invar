#!/bin/bash
# Invar hook wrapper (DX-57)
# Ensure correct working directory regardless of where Claude Code invokes from
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if ! cd "$PROJECT_ROOT" 2>/dev/null; then
  echo "[invar] Warning: Could not cd to $PROJECT_ROOT" >&2
  exit 0  # Don't block Claude Code
fi
source "$SCRIPT_DIR/invar.Stop.sh" "$@"
