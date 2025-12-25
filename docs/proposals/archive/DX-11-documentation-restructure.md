# DX-11: Documentation Restructure for Multi-Agent Support

**Date:** 2025-12-21
**Status:** ✅ Mostly Implemented (Archived 2025-12-25)
**Priority:** ★★★★★ (Foundational)
**Effort:** 1-2 days

## Completion Status

| Feature | Status | Notes |
|---------|--------|-------|
| INVAR.md header warning | ✅ Implemented | Managed file header exists |
| `.invar/examples/` directory | ✅ Implemented | Examples exist |
| `invar update` command | ✅ Implemented | Updates managed files |
| Multi-agent detection | ⚠️ Partial | Basic detection in init |
| `invar migrate` command | ❌ Not implemented | → DX-43 |
| Token efficiency (duplication removal) | ✅ Implemented | Via workflow skills |

**Remaining items extracted to:** DX-43 (Cross-Platform Distribution)

---

## Executive Summary

Current documentation structure has overlapping content between INVAR.md and CLAUDE.md, causing duplication and confusion. Additionally, the design is Claude Code-specific, limiting support for other AI agents (Cursor, Aider, Codex, Gemini CLI).

This proposal restructures documentation to:
1. Make INVAR.md the universal, agent-agnostic protocol
2. Reduce CLAUDE.md to project-specific content + protocol reference
3. Support multiple AI agents through detection and auto-configuration
4. Improve token efficiency by eliminating duplication

---

## Problem Analysis

### Current State

| File | Content | Lines | Issues |
|------|---------|-------|--------|
| INVAR.md | Protocol + ICIDIV + Examples | ~170 | Duplicates CLAUDE.md content |
| CLAUDE.md | Protocol + ICIDIV + Project Structure + Tools | ~150 | Duplicates INVAR.md content |

**Total: ~320 lines, ~40% duplication**

### Identified Problems

1. **Duplication**
   - ICIDIV workflow in both files
   - Guard commands in both files
   - Core/Shell architecture in both files
   - Agent reads both → 2x token cost for same content

2. **Ownership Ambiguity**
   - Who owns CLAUDE.md? Invar or user?
   - If Invar updates protocol, how to update CLAUDE.md without overwriting user content?
   - If user customizes, how to preserve during `invar update`?

3. **Claude Code Lock-in**
   - CLAUDE.md is Claude Code-specific
   - Cursor uses `.cursorrules`
   - Aider uses `.aider.conf.yml`
   - Other agents have different config mechanisms
   - Invar content invisible to non-Claude agents

4. **`claude init` Conflict**
   - `claude init` creates CLAUDE.md with project analysis
   - `invar init` creates CLAUDE.md with protocol
   - Order matters; wrong order causes overwrites

---

## Proposed Solution

### Core Principle: Separation of Concerns

```
INVAR.md     = Universal Protocol (Invar-managed, agent-agnostic)
CLAUDE.md    = Project Context + Reference (user-managed, Claude-specific)
.cursorrules = Project Context + Reference (user-managed, Cursor-specific)
...          = Other agent configs follow same pattern
```

### File Structure

```
Project Root/
├── INVAR.md              # Protocol (~80 lines, Invar-managed)
│                         # - Six Laws (concise)
│                         # - Core/Shell definition
│                         # - ICIDIV checklist
│                         # - 1 quick example
│                         # - Links to more resources
│
├── .invar/
│   ├── context.md        # Project state (existing)
│   └── examples/         # Reference examples (Invar-managed)
│       ├── contracts.py  # Contract patterns
│       └── core_shell.py # Core/Shell separation
│
├── CLAUDE.md             # Claude Code config (user-managed)
│   │                     # - Reference to INVAR.md
│   │                     # - Project structure
│   │                     # - Session checklist
│   │                     # - User customizations
│   │
├── .cursorrules          # Cursor config (user-managed, optional)
├── .aider.conf.yml       # Aider config (user-managed, optional)
└── pyproject.toml        # Tool configuration
```

### Content Distribution

| Content | Location | Rationale |
|---------|----------|-----------|
| Six Laws | INVAR.md | Universal principle |
| Core/Shell definition | INVAR.md | Universal architecture |
| ICIDIV workflow | INVAR.md | Universal methodology |
| Contract example (1) | INVAR.md | Quick reference |
| Detailed examples | .invar/examples/ | On-demand reading |
| Deep explanations | Online docs | Always up-to-date |
| Project structure | CLAUDE.md | Project-specific |
| Session checklist | CLAUDE.md | Agent-specific |
| Team conventions | CLAUDE.md | User-defined |
| Tool commands | INVAR.md (brief) | Universal reference |

---

## Proposed INVAR.md Template

```markdown
# The Invar Protocol v3.23

> **"Trade structure for safety."**

## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Core (pure logic) / Shell (I/O) physically separate |
| 2. Contract Complete | @pre/@post uniquely determine implementation |
| 3. Context Economy | map → sig → code (only if needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct |

## Core/Shell Architecture

| Zone | Location | Requirements |
|------|----------|--------------|
| Core | `**/core/**` | @pre/@post, pure (no I/O) |
| Shell | `**/shell/**` | Result[T, E] return type |

**Forbidden in Core:** os, sys, subprocess, pathlib, open, requests, datetime.now

## Contract Example

```python
@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)
```

More examples: `.invar/examples/`

## ICIDIV Workflow

```
□ Intent    — What? Core or Shell? Edge cases?
□ Contract  — @pre/@post + doctests BEFORE code
□ Inspect   — invar sig <file>, invar map --top 10
□ Design    — Decompose: leaves first, then compose
□ Implement — Write code to pass your doctests
□ Verify    — invar guard. If fail: reflect → fix → verify
```

## Commands

```bash
invar guard              # Static + doctests (default)
invar guard --quick      # Static only
invar guard --prove      # + CrossHair symbolic verification
invar sig <file>         # Show function signatures + contracts
invar map --top 10       # Most-referenced symbols
```

---

*Protocol v3.23 | [Full Guide](https://tefx.github.io/Invar/guide) | [Examples](.invar/examples/)*
```

**~80 lines** — concise, complete, no duplication.

---

## Proposed CLAUDE.md Template

```markdown
# Project Development Guide

> **Protocol:** Follow [INVAR.md](./INVAR.md)

## Session Start

```
□ Read INVAR.md (protocol)
□ Run: invar guard --changed
□ Run: invar map --top 10
```

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post required)
└── shell/   # I/O operations (Result[T, E] required)
```

## Project-Specific Rules

<!-- Add your team conventions below -->

## Overrides

<!-- Document any exceptions to INVAR.md rules -->
```

**~30 lines** — minimal, references INVAR.md, clear user sections.

---

## Multi-Agent Support

### Detection Logic

```python
# src/invar/shell/init_cmd.py

AGENT_CONFIGS = {
    "claude": {
        "file": "CLAUDE.md",
        "reference": "> **Protocol:** Follow [INVAR.md](./INVAR.md)\n",
        "position": "prepend",
    },
    "cursor": {
        "file": ".cursorrules",
        "reference": "Follow the Invar Protocol in INVAR.md.\n",
        "position": "prepend",
    },
    "aider": {
        "file": ".aider.conf.yml",
        "reference": "# See INVAR.md for development protocol\n",
        "position": "prepend",
    },
}

def configure_agents():
    """Detect and configure agent config files."""
    results = []
    for agent, config in AGENT_CONFIGS.items():
        path = Path(config["file"])
        if path.exists():
            content = path.read_text()
            if "INVAR.md" not in content:
                # Add reference
                if config["position"] == "prepend":
                    new_content = config["reference"] + "\n" + content
                else:
                    new_content = content + "\n" + config["reference"]
                path.write_text(new_content)
                results.append((agent, "updated"))
            else:
                results.append((agent, "already configured"))
        else:
            results.append((agent, "not found"))
    return results
```

### `invar init` Behavior

```bash
$ invar init

Creating Invar project...
✓ Created INVAR.md (protocol)
✓ Created .invar/examples/
✓ Updated pyproject.toml

Configuring agents...
  ✓ CLAUDE.md - added Invar reference
  ✓ .cursorrules - added Invar reference
  ○ .aider.conf.yml - not found

For unconfigured agents, add to their config:
  "Follow the Invar Protocol in INVAR.md"

Run 'invar guard' to verify setup.
```

### `invar init` with No Existing Config

If no CLAUDE.md exists, create minimal template:

```bash
$ invar init

Creating Invar project...
✓ Created INVAR.md (protocol)
✓ Created CLAUDE.md (project guide)  # New: created from template
✓ Created .invar/examples/

No other agent configs detected.
```

---

## Recommended User Flow

### Claude Code Users

```bash
# Option A: Claude init first (recommended)
$ claude init           # Project analysis
$ invar init            # Add protocol (detects CLAUDE.md, appends)

# Option B: Invar only
$ invar init            # Creates both INVAR.md and CLAUDE.md
```

### Cursor Users

```bash
$ invar init            # Creates INVAR.md

# Then in Cursor:
# Settings → Rules → Add "Follow INVAR.md"
# Or create .cursorrules with the reference
```

### Other Agents

```bash
$ invar init            # Creates INVAR.md

# Add to agent's system prompt:
# "Follow the Invar Protocol in INVAR.md"
```

---

## `invar update` Behavior

```bash
$ invar update

Updating Invar files...
✓ INVAR.md updated (v3.23 → v3.24)
✓ .invar/examples/ updated

User-managed files unchanged:
  ○ CLAUDE.md (user-managed)
  ○ .cursorrules (user-managed)
  ○ pyproject.toml [tool.invar] section preserved
```

**Key principle:** Only update Invar-managed files. Never touch user-managed files.

---

## Migration Path

### For Existing Projects

```bash
$ invar migrate

Migrating to new structure...

Current files:
  INVAR.md (170 lines)
  CLAUDE.md (150 lines)

Analysis:
  - 40% content duplication detected
  - ICIDIV in both files
  - Guard commands in both files

Proposed changes:
  1. Replace INVAR.md with compact version (80 lines)
  2. Remove duplicated content from CLAUDE.md
  3. Create .invar/examples/ with detailed examples
  4. Preserve user customizations in CLAUDE.md

Proceed? [y/N]
```

### Backup Strategy

```bash
$ invar migrate --backup

✓ Backed up INVAR.md → .invar/backup/INVAR.md.bak
✓ Backed up CLAUDE.md → .invar/backup/CLAUDE.md.bak
✓ Migration complete

To restore: invar migrate --restore
```

---

## Token Efficiency Analysis

### Before (Current)

| File | Lines | Tokens (est.) |
|------|-------|---------------|
| INVAR.md | 170 | ~1,200 |
| CLAUDE.md | 150 | ~1,000 |
| **Total** | 320 | **~2,200** |

Duplication: ~40% → ~900 tokens wasted per session

### After (Proposed)

| File | Lines | Tokens (est.) |
|------|-------|---------------|
| INVAR.md | 80 | ~600 |
| CLAUDE.md | 30 | ~200 |
| **Total** | 110 | **~800** |

**Savings: ~1,400 tokens per session (64% reduction)**

### On-Demand Content

| File | Lines | When Read |
|------|-------|-----------|
| .invar/examples/contracts.py | ~50 | Writing contracts |
| .invar/examples/core_shell.py | ~50 | Refactoring |
| Online guide | N/A | Deep understanding |

Only loaded when needed → additional savings.

---

## Implementation Tasks

```
□ Phase 1: New Templates (0.5 day)
  ├── Create compact INVAR.md template
  ├── Create minimal CLAUDE.md template
  ├── Create .invar/examples/ files
  └── Update src/invar/templates/

□ Phase 2: Multi-Agent Detection (0.5 day)
  ├── Implement agent config detection
  ├── Implement reference injection
  ├── Update invar init command
  └── Add tests

□ Phase 3: Migration Command (0.5 day)
  ├── Implement invar migrate
  ├── Implement duplication detection
  ├── Implement backup/restore
  └── Add tests

□ Phase 4: Documentation (0.5 day)
  ├── Update README.md
  ├── Update online docs
  ├── Add migration guide
  └── Update CLAUDE.md guidance
```

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Token cost per session | ~2,200 | ~800 |
| Content duplication | 40% | 0% |
| Supported agents | 1 (Claude) | 3+ (Claude, Cursor, Aider...) |
| Files Invar manages | 2 | 1 (+ examples) |
| User confusion about ownership | High | Low |
| `invar update` safety | Risky | Safe |

---

## Structure Protection Mechanism

To prevent agents from inadvertently violating the documentation structure, implement a 4-layer defense:

### Layer 1: INVAR.md Header Warning

Add a visible warning block at the top of INVAR.md:

```markdown
<!--
  ┌─────────────────────────────────────────────────────────┐
  │ ⚠️  INVAR-MANAGED FILE - DO NOT EDIT DIRECTLY           │
  │                                                         │
  │ This file is managed by Invar.                          │
  │ Changes will be lost on `invar update`.                 │
  │                                                         │
  │ • Add project content → CLAUDE.md                       │
  │ • Update protocol → `invar update`                      │
  └─────────────────────────────────────────────────────────┘
-->
# The Invar Protocol v3.23
```

### Layer 2: CLAUDE.md Structure Documentation

Include a structure section in CLAUDE.md template:

```markdown
## Documentation Structure

| File | Owner | Edit? | Purpose |
|------|-------|-------|---------|
| INVAR.md | Invar | ❌ | Protocol (`invar update` to sync) |
| CLAUDE.md | User | ✅ | Project customization |
| .invar/examples/ | Invar | ❌ | Reference examples |
| .invar/context.md | User | ✅ | Project state, lessons |

**Rules:**
1. Never edit INVAR.md directly
2. Add project content to CLAUDE.md
3. Update .invar/context.md for significant changes
```

### Layer 3: context.md Structure Reminder

Add to .invar/context.md template:

```markdown
## Documentation Structure

- **INVAR.md** — Protocol, Invar-managed, DO NOT EDIT
- **CLAUDE.md** — Project guide, edit freely
- **.invar/examples/** — Reference, Invar-managed
- **.invar/context.md** — This file, update as project evolves

Decision rule: "Is this Invar protocol or project-specific?"
- Protocol → Already in INVAR.md, don't duplicate
- Project-specific → Add to CLAUDE.md
```

### Layer 4: Guard Rule Enforcement

New rule `invar_md_modified` to catch direct INVAR.md edits:

```python
# src/invar/core/rules.py

def check_invar_md_modified(staged_files: list[Path]) -> Violation | None:
    """Warn if INVAR.md is staged for commit."""
    for file in staged_files:
        if file.name == "INVAR.md":
            return Violation(
                rule="invar_md_modified",
                severity=Severity.WARNING,
                file=str(file),
                message="INVAR.md was modified directly.",
                suggestion=(
                    "INVAR.md is Invar-managed. "
                    "Use `invar update` to update protocol. "
                    "Add project content to CLAUDE.md instead. "
                    "Revert with: git checkout INVAR.md"
                )
            )
    return None
```

### Protection Summary

| Layer | When | Mechanism | Reliability |
|-------|------|-----------|-------------|
| 1. Header | Agent opens INVAR.md | Visual warning | ⚠️ May ignore |
| 2. CLAUDE.md | Session start | Rules in auto-loaded file | ✅ High |
| 3. context.md | Reads context | Persistent reminder | ⚠️ May not read |
| 4. Guard | Commit time | Hard enforcement | ✅ Guaranteed |

---

## Agent Detection Strategy

### Detection Approach

**Do NOT auto-detect agent type.** Instead:
1. Check for existing config files (simple file existence)
2. Ask before modifying (user consent)
3. Provide clear instructions when no config found

### `invar init` Interactive Flow

```bash
$ invar init

✓ Created INVAR.md (protocol)
✓ Created .invar/examples/

Checking for agent configurations...
  ○ CLAUDE.md not found
  ○ .cursorrules not found

No agent configuration detected.

Options:
  [1] Create minimal CLAUDE.md (recommended for Claude Code)
  [2] Show instructions for other agents
  [3] Skip (configure later)

Choice [1]:
```

### When Config Files Exist

```bash
$ invar init

✓ Created INVAR.md (protocol)
✓ Created .invar/examples/

Checking for agent configurations...
  ✓ Found CLAUDE.md

Add Invar reference to CLAUDE.md? [Y/n] y
✓ Added reference to CLAUDE.md

For other agents, add to their config:
  "Follow the Invar Protocol in INVAR.md"
```

### Recommended Flow

| User Type | Recommended Flow |
|-----------|------------------|
| Claude Code | `claude init` → `invar init` |
| Cursor | `invar init` → Settings → Rules |
| Other | `invar init` → Add to system prompt |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Users confused by change | Clear migration guide, backup |
| Examples not found | Fallback to inline in INVAR.md |
| Agent doesn't read INVAR.md | Error message in Guard output |
| Online docs unavailable | Local fallback in .invar/ |

---

## Appendix: Agent Configuration Reference

### Claude Code

```markdown
# CLAUDE.md
> **Protocol:** Follow [INVAR.md](./INVAR.md)
```

### Cursor

```
# .cursorrules
Follow the Invar Protocol in INVAR.md.
```

### Aider

```yaml
# .aider.conf.yml
# Follow the Invar Protocol in INVAR.md
read:
  - INVAR.md
```

### Generic (System Prompt)

```
Follow the Invar Protocol defined in INVAR.md in the project root.
```

---

## Complete Synchronization Checklist

All files that need to be updated when implementing DX-11:

### Templates (`src/invar/templates/`)

| File | Change | Priority |
|------|--------|----------|
| `INVAR.md` | Add header warning block, compact to ~80 lines | P0 |
| `CLAUDE.md.template` | Replace with minimal version (~30 lines), add structure section | P0 |
| `context.md.template` | Add documentation structure section | P0 |
| NEW: `examples/contracts.py` | Create contract examples file | P1 |
| NEW: `examples/core_shell.py` | Create Core/Shell separation examples | P1 |

### Code (`src/invar/`)

| File | Change | Priority |
|------|--------|----------|
| `shell/init_cmd.py` | Add agent detection, interactive flow, reference injection | P0 |
| `shell/cli.py` | Add `invar update` command, add `invar migrate` command | P1 |
| `core/rules.py` | Add `invar_md_modified` rule | P1 |
| `core/rule_meta.py` | Add metadata for `invar_md_modified` | P1 |
| `shell/templates.py` | Update to handle new template structure | P1 |

### Documentation (`docs/`)

| File | Change | Priority |
|------|--------|----------|
| `INVAR-GUIDE.md` | Update to reference new structure, remove duplicated content | P1 |
| `DESIGN.md` | Add documentation architecture section | P2 |
| `VISION.md` | Update if references old structure | P2 |
| `AGENTS.md` | Update multi-agent support section | P1 |
| `index.html` | Update GitHub Pages with new structure info | P1 |

### Project Root

| File | Change | Priority |
|------|--------|----------|
| `README.md` | Update Quick Start with new init flow | P0 |
| `INVAR.md` | Apply new compact template (this project) | P0 |
| `CLAUDE.md` | Apply new minimal template (this project) | P0 |
| `.invar/context.md` | Add documentation structure section | P1 |

### Configuration

| File | Change | Priority |
|------|--------|----------|
| `pyproject.toml` | Add `invar_md_modified` to default rules | P1 |

### New Files to Create

| File | Purpose |
|------|---------|
| `.invar/examples/contracts.py` | Contract pattern examples |
| `.invar/examples/core_shell.py` | Core/Shell separation examples |
| `.invar/examples/README.md` | Examples index |

---

## Implementation Phases (Detailed)

### Phase 1: Templates (0.5 day)

```
□ Create compact INVAR.md template (~80 lines)
  ├── Add header warning block
  ├── Six Laws table
  ├── Core/Shell table
  ├── One contract example
  ├── ICIDIV checklist
  ├── Commands reference
  └── Footer with links

□ Create minimal CLAUDE.md template (~30 lines)
  ├── Protocol reference line
  ├── Session start checklist
  ├── Project structure placeholder
  ├── Documentation structure section
  ├── Project-specific rules section
  └── Overrides section

□ Update context.md template
  └── Add documentation structure section

□ Create .invar/examples/
  ├── contracts.py (good/bad patterns)
  ├── core_shell.py (separation examples)
  └── README.md (index)
```

### Phase 2: Agent Detection (0.5 day)

```
□ Implement agent config detection
  ├── Check CLAUDE.md exists
  ├── Check .cursorrules exists
  ├── Check .aider.conf.yml exists
  └── Check other known configs

□ Implement reference injection
  ├── Prepend reference to existing file
  ├── Check if already has reference
  └── Handle different file formats

□ Update invar init
  ├── Add interactive prompts
  ├── Add --yes flag for non-interactive
  └── Add clear output messages

□ Add tests
  ├── Test detection with various configs
  ├── Test injection preserves content
  └── Test edge cases
```

### Phase 3: Migration & Protection (0.5 day)

```
□ Implement invar migrate
  ├── Detect current structure
  ├── Analyze duplication
  ├── Generate migration plan
  ├── Execute with backup
  └── Verify result

□ Implement invar update
  ├── Update INVAR.md from template
  ├── Update .invar/examples/
  ├── Preserve user files
  └── Show version changes

□ Add invar_md_modified rule
  ├── Check staged files for INVAR.md
  ├── Return warning with suggestion
  └── Add to rule_meta.py
```

### Phase 4: Documentation (0.5 day)

```
□ Update README.md
  ├── Update Quick Start section
  ├── Add multi-agent section
  └── Update file descriptions

□ Update docs/
  ├── INVAR-GUIDE.md
  ├── AGENTS.md
  └── index.html

□ Apply to this project
  ├── Update INVAR.md
  ├── Update CLAUDE.md
  └── Update .invar/context.md

□ Create migration guide
  └── docs/MIGRATION-DX11.md
```

---

## Verification Checklist

After implementation, verify:

```
□ invar init creates correct files
□ invar init detects existing CLAUDE.md
□ invar init adds reference without overwriting
□ invar update only touches Invar-managed files
□ invar migrate backs up and converts correctly
□ Guard catches INVAR.md modifications
□ All templates render correctly
□ Examples are accessible and useful
□ README instructions work for new users
□ Cursor users can configure successfully
□ Token count reduced as expected
```

---

*Proposal generated from ultrathink analysis 2025-12-21*
*Updated with structure protection and synchronization checklist*
