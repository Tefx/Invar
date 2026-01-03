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

The hook triggers when **ALL** conditions are met:

1. ✅ **Task completed** - User finished major work (natural stopping point)
2. ✅ **Message count >= 30** - Sufficient context for meaningful feedback
3. ✅ **Duration >= 2 hours** - Non-trivial session (avoids quick fixes)

**No hard frequency cap**: Same-day sessions merge into single file (see SKILL.md for merge logic).

---

## Silent Mode

When `mode: "silent"`:
- Feedback generation runs in background
- No interruption to current conversation
- User sees notification only: `✓ Feedback saved to .invar/feedback/feedback-{date}.md`

---

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

Since Claude Code doesn't yet support `PostTaskCompletion` hook, you can use the `Stop` hook as a temporary workaround.

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

**Completed**:
- ✅ Hook schema designed
- ✅ Configuration structure defined
- ✅ User control mechanism specified
- ✅ Stop hook workaround documented

**Waiting for Claude Code Support**:
- ⏸️ PostTaskCompletion hook type
- ⏸️ Skill invocation from hooks
- ⏸️ Session state tracking (message count, duration)

**Next Steps**:
- Implement Phase C: Init Integration (can be done independently)
- Submit feature request to Claude Code for PostTaskCompletion hook
- Test manual `/invar-reflect` invocation thoroughly

---

**Version**: 1.0 (Phase B - Proposed)
**Updated**: 2026-01-03
**Related**: DX-79 Invar Usage Feedback Collection
