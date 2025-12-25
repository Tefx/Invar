# Documentation Structure

> **Principle:** Protocol in INVAR, Configuration in CLAUDE.

This document defines the information attribution structure for Invar-enabled projects.

## File Roles

| File | Role | Owner | Sync |
|------|------|-------|------|
| **INVAR.md** | Protocol reference | Invar | `invar update` |
| **CLAUDE.md** | Project configuration | User | Manual |
| **.invar/context.md** | Session state, lessons | User | Manual |
| **.claude/commands/** | Agent skills | Invar | `invar init` |

### INVAR.md (Protocol)

The Invar Protocol specification. Managed by `invar update`.

**Contains:**
- Six Laws (principles)
- Core/Shell Architecture
- Contract requirements
- USBV Workflow
- Visible Workflow (DX-30)
- Review Gate triggers (DX-31)
- Task Completion criteria
- Commands reference
- Markers syntax

**Does NOT contain:**
- Project-specific structure
- Team conventions
- Tool configurations beyond Invar

### CLAUDE.md (Project Configuration)

Project-specific agent guidance. User-managed.

**Contains:**
- Check-In/Final (quick reference)
- Project structure
- Tool selection (Serena, other MCP tools)
- Agent Roles and commands
- Review Modes (Isolated vs Quick)
- Project-specific rules
- Overrides and exceptions

**Does NOT contain:**
- Protocol rules (refer to INVAR.md)
- Workflow definitions (refer to INVAR.md)

---

## Information Attribution

### Decision Rule

```
Is this information...

Protocol-level (universal)?     → INVAR.md
  - Guard rules
  - Architecture requirements
  - Workflow phases
  - Verification levels

Project-level (specific)?       → CLAUDE.md
  - Directory structure
  - Team conventions
  - Tool configurations
  - Agent behaviors
```

### Detailed Attribution Table

| Information | INVAR | CLAUDE | Rationale |
|-------------|-------|--------|-----------|
| Six Laws | ✅ | - | Universal principles |
| Core/Shell Architecture | ✅ | - | Protocol requirement |
| USBV Workflow | ✅ | Brief | Protocol, CLAUDE references |
| Visible Workflow | ✅ | Brief | Protocol with examples |
| Review Gate (triggers) | ✅ | - | Guard rule mechanism |
| Commands (/audit, /guard) | - | ✅ | User-invokable actions |
| Skills (/review) | - | ✅ | Agent workflow configuration |
| Check-In/Final | ✅ | ✅ | Protocol + quick reference |
| Task Completion | ✅ | - | Protocol criteria |
| Commands | ✅ | - | Tool reference |
| Markers | ✅ | - | Syntax specification |
| Project Structure | - | ✅ | Project-specific |
| Tool Selection | - | ✅ | Project-specific tools |
| Agent Roles | - | ✅ | Agent configuration |

---

## Review System Attribution

The review system spans both files with clear separation:

```
INVAR.md (Protocol)              CLAUDE.md (Configuration)
─────────────────                ─────────────────────────
Review Gate                      Commands & Skills
├─ Trigger conditions            ├─ /audit (read-only review)
│  ├─ escape hatches >= 3        ├─ /guard (run verification)
│  ├─ coverage < 50%             └─ /review skill (fix loop)
│  └─ security-sensitive
└─ review_suggested rule

Guard detects conditions ───────→ Agent selects response
      (Protocol)                       (Platform-specific)
```

**Why this split?**
- Review Gate is a Guard rule → Protocol
- Mode selection uses Task tool → Claude Code specific
- Other agents (Cursor, Copilot) may not support isolation

---

## Templates vs Source

### This Project (Invar itself)

| File | Role |
|------|------|
| `INVAR.md` | **SOURCE** - Full protocol |
| `CLAUDE.md` | Project guide for Invar development |
| `src/invar/templates/INVAR.md` | Compact version for distribution |
| `src/invar/templates/CLAUDE.md.template` | Template for new projects |

**Warning:** Do not run `invar update` on this project's INVAR.md!

### Other Projects (using Invar)

| File | Role |
|------|------|
| `INVAR.md` | Copy from template, updated by `invar update` |
| `CLAUDE.md` | User-customized from template |

---

## Duplication Policy

### Allowed Duplication

| Content | In INVAR | In CLAUDE | Purpose |
|---------|----------|-----------|---------|
| Check-In format | ✅ Full | ✅ Quick ref | Visibility |
| Final format | ✅ (in Task Completion) | ✅ Quick ref | Visibility |
| USBV overview | ✅ Full | Brief mention | Reference |

### Not Allowed

- Copying protocol rules to CLAUDE (refer instead)
- Copying project config to INVAR (wrong scope)
- Maintaining same content in both (sync burden)

---

## Maintenance

### When to Update INVAR.md Template

- Protocol changes (new laws, rules)
- Guard behavior changes
- Workflow methodology changes
- Command changes

### When to Update CLAUDE.md Template

- Agent capability changes (new modes)
- New commands (/audit, /guard) or skills (/review)
- Template structure improvements

### Sync Command

```bash
invar update    # Updates INVAR.md from template (other projects only)
```

**Note:** This command is for projects using Invar, not for the Invar project itself.

---

*Documentation Structure — Ensures consistent information attribution across Invar-enabled projects.*
