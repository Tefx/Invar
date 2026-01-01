# DX-40: Smart Tool Redirect Hook

> **"Don't tell agents what to do. Make wrong choices impossible."**

**Status:** ✗ Dropped (2025-12-27)
**Created:** 2025-12-25
**Origin:** Extracted from DX-16 Phase 2
**Effort:** Low
**Risk:** Low

## Drop Reason

This proposal contradicts **Lesson #19** from project experience:

> **Lesson #19:** 干预时机决定效果。提交前阻止 = 有效。操作后提醒 = 噪音。
> "Pre-commit blocks are effective; PreToolUse hooks are noise (decision already made)"

The same mechanism (PreToolUse hook) was previously attempted for Read/.py files and removed after reflection. The fundamental problem is timing:

```
Decision timeline:
1. Agent decides to use pytest     ← Decision made HERE
2. Agent calls Bash("pytest ...")
3. Hook triggers                   ← Hook fires HERE (too late!)
4. Hook blocks and suggests alternative
5. Agent must re-decide            ← Not guaranteed to choose correctly
```

The hook cannot prevent the agent from **choosing** pytest; it can only prevent **executing** pytest. By then, the decision has already been made.

---

## Problem Statement

DX-16 Phase 1 (MCP Server) achieves ~50-60% compliance rate with Invar tools. Agents still sometimes use `Bash("pytest ...")` instead of `invar_guard`.

**Root cause:** MCP tools are available but not enforced. Agents can still choose wrong tools.

## Proposed Solution

Add PreToolUse hook that intelligently redirects basic verification commands to Invar tools.

### Hook Logic

```python
# .claude/hooks/invar_tool_redirect.py

import re
import json
import sys

# Block basic patterns that should use invar_guard
BLOCKED_PATTERNS = [
    r"pytest\s+[\w/]+\.py(\s+--doctest-modules)?\s*$",
    r"crosshair\s+check\s+[\w/]+\.py\s*$",
    r"python\s+-m\s+pytest\s+[\w/]+\.py\s*$",
]

# Allow advanced patterns that have legitimate uses
ALLOWED_PATTERNS = [
    r"pytest.*(-k\s|--pdb|--cov|--tb=|--lf|--ff)",  # Debug/specific tests
    r"crosshair\s+(watch|diffbehavior|cover)",       # Advanced features
    r"pytest.*--benchmark",                           # Performance testing
]

def check_command(command: str) -> dict:
    """Check if command should be blocked."""
    # First check if it's an allowed advanced pattern
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command):
            return {"allow": True}

    # Then check if it's a blocked basic pattern
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            return {
                "allow": False,
                "message": f"Use `invar_guard` instead of direct pytest/crosshair.\n"
                          f"Blocked: {command}\n"
                          f"Alternative: invar_guard(changed=true)"
            }

    return {"allow": True}

if __name__ == "__main__":
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        result = check_command(command)
        print(json.dumps(result))
    else:
        print(json.dumps({"allow": True}))
```

### Hook Registration

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": "python .claude/hooks/invar_tool_redirect.py"
      }
    ]
  }
}
```

## Expected Effect

| Metric | Before (DX-16 P1) | After (DX-40) |
|--------|-------------------|---------------|
| Agent uses invar for verification | ~50-60% | ~95% |
| False positive blocks | N/A | <5% |
| Advanced usage blocked | N/A | 0% |

## Why Separate from DX-16

DX-16 Phase 1 (MCP Server) is **environment design** — providing better tools.
DX-40 (Hook) is **constraint enforcement** — preventing wrong tools.

These are independent mechanisms that can be deployed separately.

## Implementation Plan

1. Create hook script at `.claude/hooks/invar_tool_redirect.py`
2. Add hook registration to `.claude/settings.json`
3. Test with common verification patterns
4. Update `invar init --claude` to include hook setup

## Success Criteria

- [ ] Block basic pytest/crosshair commands
- [ ] Allow advanced usage (debugging, coverage)
- [ ] False positive rate < 5%
- [ ] Clear error messages with correct alternative

## Related

- DX-16: Agent Tool Enforcement (Phase 1 origin, archived)
- MCP Server: `src/invar/mcp/`
- Claude Code hooks: https://docs.anthropic.com/claude-code/hooks
