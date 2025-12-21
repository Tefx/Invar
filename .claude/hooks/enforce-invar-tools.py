#!/usr/bin/env python3
"""
Enforce Invar workflow: prefer invar sig over Read for Python files.

Hook outputs:
- "allow": proceed without asking
- "ask": show confirmation with reason
- "deny": block with reason
"""

import json
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # No input, allow

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Check if reading a Python file in src/invar/
    if file_path.endswith(".py") and "/src/invar/" in file_path:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    "Consider using 'invar sig <file>' to see contracts, "
                    "or Serena find_symbol for semantic search. "
                    "Read shows raw code without contract context."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Allow all other reads
    sys.exit(0)


if __name__ == "__main__":
    main()
