#!/bin/bash
# Smart Invar Guard - Detects rule changes and runs full guard when needed
#
# DX-19: Default runs full verification (static + doctests + CrossHair + Hypothesis).
# When rule-affecting files are modified, runs full guard instead of --changed.
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

# DX-19: Default is full verification, no need for --prove flag
if [ "$FULL_GUARD" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Rule change detected - verifying entire codebase"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    invar guard
else
    invar guard --changed
fi
