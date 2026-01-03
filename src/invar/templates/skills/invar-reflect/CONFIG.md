# /invar-reflect Configuration

**Status**: Phase B - Hook Integration (Proposed)

This document describes the configuration for automatic feedback collection using the `/invar-reflect` skill.

---

## Overview

The `/invar-reflect` skill can be triggered:
1. **Manually**: User calls `/invar-reflect`
2. **Automatically** (Phase B): Via `PostTaskCompletion` hook when conditions are met

---

## Proposed Hook Schema


### Message Count Trigger (Implemented - DX-79)

**Status**: ✅ Implemented in v1.15.0

Both Claude Code and Pi now support automatic feedback triggering via **message count threshold**.

**Configuration in `.claude/settings.local.json`**:

```json
{
  "feedback": {
    "enabled": true,
    "min_messages": 30
  }
}
```

**Hook Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | boolean | true | Enable feedback collection |
| `min_messages` | number | 30 | Minimum messages before trigger |

**How it works**:

1. **Message counting**: Both hooks track message count per session
2. **Threshold trigger**: At `min_messages`, hook displays reminder
3. **User action**: Agent sees reminder and can run `/invar-reflect`

**Cross-platform implementation**:

| Platform | Hook File | Mechanism |
|----------|-----------|-----------|
| **Claude Code** | `.claude/hooks/invar.UserPromptSubmit.sh` | Bash script with jq config parsing |
| **Pi** | `.pi/hooks/invar.ts` | TypeScript with fs config reading |

Both read the same `.claude/settings.local.json` configuration file.

### PostTaskCompletion Hook (Waiting for Claude Code Support)

**Proposed configuration in `.claude/settings.json`**:

```json
{
  "hooks": {
    "PostTaskCompletion": [
      {
        "hooks": [
          {
            "type": "skill",
            "skill": "invar-reflect",
            "mode": "silent",
            "conditions": {
              "min_messages": 30,
              "min_duration_hours": 2
            }
          }
        ]
      }
    ]
  },
  "feedback": {
    "enabled": true,
    "auto_trigger": true,
    "retention_days": 90
  }
}
```

**Hook Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | - | Must be `"skill"` |
| `skill` | string | - | Skill name: `"invar-reflect"` |
| `mode` | string | `"silent"` | Silent mode (no user interruption) |
| `conditions.min_messages` | number | 30 | Minimum messages in session |
| `conditions.min_duration_hours` | number | 2 | Minimum session duration |

**Feedback Config**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | boolean | true | Enable feedback collection |
| `auto_trigger` | boolean | true | Auto-run via hook |
| `retention_days` | number | 90 | Auto-cleanup old files |

---

## Triggering Conditions


The hook triggers when the message count reaches the configured threshold (default: 30).

**Conditions**:

1. ✅ **Message count >= min_messages** (default: 30)
2. ✅ **Feedback enabled** (`feedback.enabled = true`)

**No hard frequency cap**: Users can run `/invar-reflect` manually at any time.

**Customizing threshold**:

```json
{
  "feedback": {
    "enabled": true,
    "min_messages": 50  // Trigger at 50 messages instead of 30
  }
}
```

## Silent Mode


The hook displays a **reminder** when the threshold is reached:

```
<system-reminder>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Invar: Auto-triggering usage feedback (30 messages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Session has reached 30 messages. Consider running /invar-reflect
to generate usage feedback.

To disable: Set feedback.enabled=false in .claude/settings.local.json
</system-reminder>
```

**Note**: The agent sees this reminder and can choose to invoke `/invar-reflect` or continue working.

## User Control

### Enable/Disable

**During init** (Phase C):
```bash
$ invar init
...
Enable automatic feedback collection? [Y/n]: n
```

**After init**:
```json
// .claude/settings.json
{
  "feedback": {
    "enabled": false  // Disable feedback collection
  }
}
```

Or disable auto-trigger only (manual `/invar-reflect` still works):
```json
{
  "feedback": {
    "enabled": true,
    "auto_trigger": false  // Manual only
  }
}
```

### File Management

Feedback files location:
```
.invar/feedback/
├── feedback-2026-01-03.md  # All sessions from Jan 3
├── feedback-2026-01-04.md  # All sessions from Jan 4
└── feedback-2026-01-10.md  # Jan 10 (gaps are OK)
```

**Auto-cleanup**: Files older than `retention_days` are automatically deleted.

**Manual cleanup**:
```bash
# Delete all feedback
rm -rf .invar/feedback/

# Delete specific file
rm .invar/feedback/feedback-2026-01-03.md
```

---

## Workaround: Using Stop Hook (Until PostTaskCompletion is Available)


### Implementation Details

**Claude Code Hook** (`.claude/hooks/invar.UserPromptSubmit.sh`):

```bash
# DX-79: Feedback trigger at threshold
FEEDBACK_ENABLED=true
MIN_MESSAGES=30

if [[ -f ".claude/settings.local.json" ]]; then
  if command -v jq &> /dev/null; then
    FEEDBACK_ENABLED=$(jq -r '.feedback.enabled // true' .claude/settings.local.json)
    MIN_MESSAGES=$(jq -r '.feedback.min_messages // 30' .claude/settings.local.json)
  fi
fi

if [[ "$FEEDBACK_ENABLED" == "true" && $COUNT -eq $MIN_MESSAGES ]]; then
  echo "<system-reminder>"
  echo "📊 Invar: Auto-triggering usage feedback ($COUNT messages)"
  echo "Consider running /invar-reflect to generate usage feedback."
  echo "</system-reminder>"
fi
```

**Pi Hook** (`.pi/hooks/invar.ts`):

```typescript
// DX-79: Helper to read feedback configuration
function readFeedbackConfig() {
  try {
    const fs = require("fs");
    const settingsPath = ".claude/settings.local.json";
    if (fs.existsSync(settingsPath)) {
      const settings = JSON.parse(fs.readFileSync(settingsPath, "utf-8"));
      return {
        enabled: settings.feedback?.enabled ?? true,
        min_messages: settings.feedback?.min_messages ?? 30,
      };
    }
  } catch {
    // Ignore errors, use defaults
  }
  return { enabled: true, min_messages: 30 };
}

pi.on("agent_start", async () => {
  msgCount++;
  
  // ... protocol refresh logic ...
  
  const feedbackConfig = readFeedbackConfig();
  if (msgCount === feedbackConfig.min_messages && feedbackConfig.enabled) {
    pi.send(`<system-reminder>
📊 Invar: Auto-triggering usage feedback (${msgCount} messages)
Consider running /invar-reflect to generate usage feedback.
</system-reminder>`);
  }
});
```

**Installation**: Hooks are automatically installed via `invar init --claude` or `invar init --pi`.

### Stop Hook Implementation

Create `.claude/hooks/invar.FeedbackTrigger.sh`:

```bash
#!/bin/bash
# Invar Feedback Trigger (Stop Hook Workaround)
# DX-79 Phase B: Auto-trigger /invar-reflect on session end

# Read feedback config
FEEDBACK_ENABLED=$(jq -r '.feedback.enabled // true' .claude/settings.local.json 2>/dev/null)
AUTO_TRIGGER=$(jq -r '.feedback.auto_trigger // true' .claude/settings.local.json 2>/dev/null)

if [[ "$FEEDBACK_ENABLED" != "true" ]] || [[ "$AUTO_TRIGGER" != "true" ]]; then
  exit 0  # Feedback disabled
fi

# Check session conditions (requires session state tracking)
STATE_DIR="${CLAUDE_STATE_DIR:-/tmp/invar_hooks_$(id -u)}"
SESSION_START_FILE="$STATE_DIR/session_start"
MESSAGE_COUNT_FILE="$STATE_DIR/message_count"

# Calculate duration
if [[ -f "$SESSION_START_FILE" ]]; then
  SESSION_START=$(cat "$SESSION_START_FILE")
  SESSION_END=$(date +%s)
  DURATION_HOURS=$(( (SESSION_END - SESSION_START) / 3600 ))
else
  DURATION_HOURS=0
fi

# Read message count
MESSAGE_COUNT=$(cat "$MESSAGE_COUNT_FILE" 2>/dev/null || echo 0)

# Check conditions
if [[ $MESSAGE_COUNT -ge 30 ]] && [[ $DURATION_HOURS -ge 2 ]]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📊 Invar: Generating usage feedback..."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Session complete: $MESSAGE_COUNT messages, ${DURATION_HOURS}h duration"
  echo "Feedback will be saved to .invar/feedback/feedback-$(date +%Y-%m-%d).md"
  echo ""
  echo "To review or share: cat .invar/feedback/feedback-$(date +%Y-%m-%d).md"
  echo "To disable: Set feedback.auto_trigger=false in .claude/settings.local.json"
fi

# Cleanup session state
rm -rf "$STATE_DIR" 2>/dev/null
```

**Note**: This workaround provides notification but doesn't actually generate feedback automatically. Full auto-generation requires:
1. Claude Code to support skill invocation from hooks, OR
2. Hook to write state file that triggers `/invar-reflect` on next user interaction

---

## Configuration Template (for `invar init`)

When Phase C is complete, `invar init` will generate this configuration:

```json
{
  "permissions": {
    "allow": [
      // ... existing permissions ...
    ]
  },
  "hooks": {
    "PostTaskCompletion": [
      {
        "hooks": [
          {
            "type": "skill",
            "skill": "invar-reflect",
            "mode": "silent",
            "conditions": {
              "min_messages": 30,
              "min_duration_hours": 2
            }
          }
        ]
      }
    ],
    // ... existing hooks ...
  },
  "feedback": {
    "enabled": true,
    "auto_trigger": true,
    "retention_days": 90
  }
}
```

**Init prompt** (Phase C):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Usage Feedback (Optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invar can automatically reflect on tool usage to help improve
the framework. Feedback is:
  - Stored locally in .invar/feedback/
  - Never sent automatically
  - You decide what (if anything) to share

Enable automatic feedback collection? [Y/n]:
```

---

## Privacy & Security

**What's stored**:
- Tool usage statistics (counts, success/failure)
- Error types (NO error messages)
- Session metadata (duration, message count)
- User's subjective experience (generated by AI)

**What's NOT stored**:
- Source code
- File paths (anonymized)
- Error messages (might contain code)
- Project-specific details

**All data stays local** in `.invar/feedback/`. User reviews before sharing.

---

## Testing (Phase B Acceptance Criteria)

### Manual Testing

1. **Test manual invocation**:
   ```bash
   # In Claude Code session
   /invar-reflect
   ```
   - ✅ Generates feedback file
   - ✅ Saves to `.invar/feedback/feedback-{today}.md`
   - ✅ No errors

2. **Test config disable**:
   ```json
   // .claude/settings.local.json
   { "feedback": { "enabled": false } }
   ```
   - ✅ `/invar-reflect` still works (manual override)
   - ✅ Hook doesn't trigger (when implemented)

3. **Test same-day merge**:
   ```bash
   # Session 1: Morning
   /invar-reflect
   # Creates feedback-2026-01-03.md

   # Session 2: Afternoon (same day)
   /invar-reflect
   # Updates feedback-2026-01-03.md (not create new file)
   ```
   - ✅ Single file per day
   - ✅ Intelligent merging (semantic understanding)
   - ✅ Daily summary regenerated

### Automated Testing (when hook is implemented)

1. **Test condition thresholds**:
   - Session < 30 messages: Hook doesn't trigger
   - Session < 2 hours: Hook doesn't trigger
   - Session >= 30 messages AND >= 2 hours: Hook triggers

2. **Test silent mode**:
   - Hook triggers in background
   - No interruption to conversation
   - Notification shown only

3. **Test retention**:
   - Files older than 90 days auto-deleted
   - Configurable via `retention_days`

---

## Phase B Status


**Completed** (v1.15.0):
- ✅ Message Count trigger strategy designed
- ✅ Cross-platform implementation (Claude Code + Pi)
- ✅ Shared configuration structure
- ✅ Hook templates updated
- ✅ Installation via `invar init`

**Replaced PostTaskCompletion with Message Count** because:
- PostTaskCompletion hook not supported by Claude Code or Pi
- Message count is universally implementable
- Simpler, more predictable trigger mechanism
- User has full control via config

**Testing**:
- Manual `/invar-reflect` invocation: Works
- Hook trigger at threshold: Implemented
- Config disable: Honored by both hooks
- Multi-agent setup: Both hooks installed

**Next Steps**:
- Monitor user feedback on threshold defaults
- Consider adding reminder messages at other checkpoints (e.g., 60, 90 messages)
