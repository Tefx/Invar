#!/bin/bash
# Smart Invar Guard - Detects rule changes and runs full guard when needed
#
# DX-19: Default runs changed-file verification.
# When rule-affecting files are modified, runs full guard (--all).
# This prevents the situation where a rule severity upgrade passes locally
# (because only changed files are checked) but fails in CI (full check).

set -e

# Files that affect rule behavior - changes require full verification
RULE_FILES=(
    "src/invar/core/rule_meta.py"
    "src/invar/core/rules.py"
    "src/invar/core/contracts.py"
    "src/invar/core/purity.py"
    "pyproject.toml"
)

# Activate venv
source .venv/bin/activate
export INVAR_UVX_RESPAWNED=1
INVAR_CMD="$(pwd)/.venv/bin/invar"

# Check if any rule-affecting files are staged
STAGED_FILES=$(git diff --cached --name-only)
FULL_GUARD=false

for rule_file in "${RULE_FILES[@]}"; do
    if echo "$STAGED_FILES" | grep -q "^${rule_file}$"; then
        FULL_GUARD=true
        echo "⚠️  Detected change to ${rule_file} - running FULL guard"
        break
    fi
done

# Default is changed-file verification; use --all for rule-level changes.
if [ "$FULL_GUARD" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Rule change detected - verifying entire codebase"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    "$INVAR_CMD" guard --all
else
    "$INVAR_CMD" guard
fi
