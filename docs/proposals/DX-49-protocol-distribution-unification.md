# DX-49: Protocol Distribution Unification

> **"One source, one truth, everywhere."**

**Status:** Draft
**Created:** 2025-12-26
**Effort:** Medium-High
**Risk:** Medium
**Dependencies:** DX-47 (command/skill naming)

## Problem Statement

Current state violates Single Source of Truth (SSOT):

| File Type | Project Version | Template Version | Problem |
|-----------|-----------------|------------------|---------|
| INVAR.md | 93 lines | 208 lines | Different content |
| CLAUDE.md | 67 lines | 115 lines | Different structure |
| skills/*.md | MCP syntax | CLI syntax | Syntax differs, no sync |
| sections/*.md | Exists | N/A | Duplicates skills/ |
| commands/*.md | Exists | Exists | Overlaps with skills (DX-47) |

**Root cause:** Multiple sources, inconsistent flow direction.

## Design Principles

| Priority | Principle | Requirement |
|----------|-----------|-------------|
| 1 | **Single Source** | templates/ is the ONLY source for all managed files |
| 2 | **Derived Everywhere** | Project files are generated, not manually written |
| 3 | **No Choice** | `invar init` has one mode, no decisions needed |

## Solution: Unified Source in templates/

### Core Principle

```
┌─────────────────────────────────────────────────────────────────┐
│                 templates/ = Single Source of Truth              │
│                                                                  │
│  Everything flows FROM templates, never TO templates             │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  ┌─────────────┐     ┌─────────────┐      ┌─────────────┐
  │ invar       │     │ invar init  │      │ invar       │
  │ sync-self   │     │ (new proj)  │      │ update      │
  └─────────────┘     └─────────────┘      └─────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
  ┌─────────────┐     ┌─────────────┐      ┌─────────────┐
  │ Invar proj  │     │ New project │      │ Existing    │
  │ + MCP syntax│     │ + CLI syntax│      │ project     │
  │ + additions │     │ + defaults  │      │ + preserve  │
  └─────────────┘     └─────────────┘      └─────────────┘
```

### Templates Directory Structure

```
src/invar/templates/
├── manifest.toml           # Defines all template behaviors
│
├── protocol/               # Protocol files (direct copy)
│   └── INVAR.md            # ~130 lines, self-contained
│
├── config/                 # Configuration templates (with variables)
│   ├── CLAUDE.md.jinja     # Project guide with user regions
│   ├── context.md.jinja    # Project state template
│   └── pre-commit.yaml.jinja
│
├── skills/                 # Agent instructions (MCP/CLI variants)
│   ├── develop.md.jinja
│   ├── investigate.md.jinja
│   ├── propose.md.jinja
│   └── review.md.jinja
│
├── examples/               # Example code (direct copy)
│   ├── contracts.py
│   ├── core_shell.py
│   └── README.md
│
└── integrations/           # Optional tool integrations
    ├── cursor.rules.jinja  # --cursor flag
    └── aider.conf.jinja    # --aider flag
```

**Note:** `commands/` directory removed. Per DX-47:
- `/review` command → renamed to `/audit` (or eliminated)
- Command functionality merged into skill with mode selection

### manifest.toml

```toml
# Template manifest - defines all generation behaviors

[meta]
version = "5.0"
workflow = "USBV"

[variables]
# Available variables for templates
syntax = ["cli", "mcp"]  # Command syntax variant
project_name = "string"  # Project name placeholder

# =============================================================================
# Direct Copy (no variables)
# =============================================================================

[copy]
# Files copied without modification
files = [
    { src = "protocol/INVAR.md", dest = "INVAR.md" },
    { src = "examples/", dest = ".invar/examples/" },
]

# =============================================================================
# Template Generation (with variables)
# =============================================================================

[generate.config]
# Configuration files with user-editable regions
files = [
    { src = "config/CLAUDE.md.jinja", dest = "CLAUDE.md" },
    { src = "config/context.md.jinja", dest = ".invar/context.md" },
    { src = "config/pre-commit.yaml.jinja", dest = ".pre-commit-config.yaml" },
]

[generate.skills]
# Skills with syntax variants
files = [
    { src = "skills/develop.md.jinja", dest = ".claude/skills/develop/SKILL.md" },
    { src = "skills/investigate.md.jinja", dest = ".claude/skills/investigate/SKILL.md" },
    { src = "skills/propose.md.jinja", dest = ".claude/skills/propose/SKILL.md" },
    { src = "skills/review.md.jinja", dest = ".claude/skills/review/SKILL.md" },
]

# =============================================================================
# Optional Generation (flag-triggered)
# =============================================================================

[optional]
"--cursor" = { src = "integrations/cursor.rules.jinja", dest = ".cursorrules" }
"--aider" = { src = "integrations/aider.conf.jinja", dest = ".aider.conf.yml" }
"--mcp" = { syntax = "mcp" }  # Use MCP syntax for skills

# =============================================================================
# Update Behavior
# =============================================================================

[update]
# How invar update handles existing files
overwrite = ["INVAR.md", ".invar/examples/"]
merge = ["CLAUDE.md", ".claude/skills/"]  # Preserve user regions
skip = [".invar/context.md"]  # Never overwrite user content
```

### Template Syntax (Jinja2)

#### Skills Template Example

```jinja
{# skills/develop.md.jinja #}
---
name: develop
description: Implementation phase following USBV workflow.
---

# Development Mode

## Entry Actions (REQUIRED)

{% if syntax == "mcp" %}
```python
invar_guard(changed=true)
invar_map(top=10)
```
{% else %}
```bash
invar guard --changed
invar map --top 10
```
{% endif %}

**Display:**
```
✓ Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
```

Then read `.invar/context.md` for project state.

## USBV Workflow

### 1. UNDERSTAND
- **Intent:** What exactly needs to be done?
- **Inspect:** Use `{{ commands.sig }}` to see existing contracts
- **Context:** Read relevant code, understand patterns

### 2. SPECIFY
- **Contracts FIRST:** Write `@pre`/`@post` before implementation

### 3. BUILD
- Follow contracts
- Run `{{ commands.guard_changed }}` frequently

### 4. VALIDATE
- Run `{{ commands.guard }}` (full verification)

{% if syntax == "mcp" %}
## Claude Code Extensions

### Plan Mode Integration
**For complex tasks:** Enter Plan Mode first, get user approval.

### Commit Format
```bash
git add . && git commit -m "feat: [description]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Timeout Handling
| Threshold | Duration | Action |
|-----------|----------|--------|
| Warning | 3 hours | Soft warning with options |
| Hard stop | 4 hours | Save state, exit |
{% endif %}
```

#### CLAUDE.md Template Example

```jinja
{# config/CLAUDE.md.jinja #}
# Project Development Guide

<!--invar:managed:start-->
> **Protocol:** Follow [INVAR.md](./INVAR.md) — Check-In, USBV workflow, Task Completion.

## Check-In / Final

**First message:**
```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

**Last message:**
```
✓ Final: guard PASS | 0 errors, N warnings
```

Then read `.invar/context.md` for project state.

## Project Structure

```
src/{project}/
├── core/    # Pure logic (@pre/@post, doctests, no I/O)
└── shell/   # I/O operations (Result[T, E] return type)
```
<!--invar:managed:end-->

---

<!--invar:user:start-->
## Project-Specific Rules

<!-- Add your team conventions below -->

## Overrides

<!-- Document any exceptions to INVAR.md rules -->
<!--invar:user:end-->

---

*Generated by Invar v{{ version }}. Edit user sections freely.*
```

### Unified INVAR.md (~130 lines)

```markdown
<!--invar:version=5.0-->
# The Invar Protocol v5.0

> **"Trade structure for safety."**

## Six Laws

| Law | Principle |
|-----|-----------|
| 1. Separation | Core (pure logic) / Shell (I/O) physically separate |
| 2. Contract Complete | @pre/@post + doctests uniquely determine implementation |
| 3. Context Economy | map → sig → code (only read what's needed) |
| 4. Decompose First | Break into sub-functions before implementing |
| 5. Verify Reflectively | Fail → Reflect (why?) → Fix → Verify |
| 6. Integrate Fully | Local correct ≠ Global correct; verify all paths |

## Core/Shell Architecture

| Zone | Location | Requirements |
|------|----------|--------------|
| Core | `**/core/**` | @pre/@post, pure (no I/O), doctests |
| Shell | `**/shell/**` | `Result[T, E]` return type |

**Forbidden in Core:** `os`, `sys`, `subprocess`, `pathlib`, `open`, `requests`

## Core Example

```python
from deal import pre, post

@pre(lambda price, discount: price > 0 and 0 <= discount <= 1)
@post(lambda result: result >= 0)
def discounted_price(price: float, discount: float) -> float:
    """
    >>> discounted_price(100, 0.2)
    80.0
    """
    return price * (1 - discount)
```

## Shell Example

```python
from returns.result import Result, Success, Failure

def read_config(path: Path) -> Result[dict, str]:
    try:
        return Success(json.loads(path.read_text()))
    except FileNotFoundError:
        return Failure(f"Not found: {path}")
```

## Check-In / Final

**First message:**
```
✓ Check-In: guard PASS | top: <entry1>, <entry2>
```

**Last message:**
```
✓ Final: guard PASS | 0 errors, 2 warnings
```

## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Key Actions |
|-------|---------|-------------|
| Understand | Know context | Intent, Inspect (sig/map), Constraints |
| Specify | Define boundaries | @pre/@post FIRST, Doctests, Design |
| Build | Implement | Follow contracts, Compose |
| Validate | Confirm | invar guard, Review if triggered |

## Commands

```bash
invar guard              # Full verification (default)
invar guard --changed    # Modified files only
invar guard --static     # Quick static check (~0.5s)
invar sig <file>         # Show contracts + signatures
invar map --top 10       # Most-referenced symbols
```

## Markers

```python
# @shell:entry              — Framework callback (exempt from Result)
# @shell_complexity: reason — Justified shell complexity
# @invar:allow rule: reason — Rule exemption with justification
```

## Size Limits

| Limit | Value |
|-------|-------|
| File | 500 lines |
| Function | 50 lines |

---

*Protocol v5.0 | [Guide](https://tefx.github.io/invar) | Examples: `.invar/examples/`*
```

## Delete sections/

Per unified source principle, sections/ content merges into skills/:

| Current | Action |
|---------|--------|
| sections/develop.md | → skills/develop.md.jinja |
| sections/investigate.md | → skills/investigate.md.jinja |
| sections/propose.md | → skills/propose.md.jinja |
| sections/review.md | → skills/review.md.jinja |
| sections/reference.md | → INVAR.md (Markers section) |

**Delete sections/ directory after merge.**

## Delete commands/

Per DX-47 resolution:

| Current | Action |
|---------|--------|
| commands/review.md | Delete (functionality in skill with mode flag) |

**Note:** If DX-47 chooses Option B (rename command to /audit), create skills/audit.md.jinja instead.

## Protocol Constants

```python
# src/invar/core/protocol.py

"""Protocol constants - referenced by templates and CLI."""

PROTOCOL_VERSION = "5.0"
WORKFLOW_NAME = "USBV"
WORKFLOW_PHASES = ["Understand", "Specify", "Build", "Validate"]

# Command syntax variants
CLI_COMMANDS = {
    "guard": "invar guard",
    "guard_changed": "invar guard --changed",
    "guard_static": "invar guard --static",
    "sig": "invar sig <file>",
    "map": "invar map --top 10",
}

MCP_COMMANDS = {
    "guard": "invar_guard()",
    "guard_changed": "invar_guard(changed=true)",
    "guard_static": "invar_guard(static=true)",
    "sig": 'invar_sig(target="<file>")',
    "map": "invar_map(top=10)",
}

# Formats
CHECKIN_FORMAT = "✓ Check-In: guard {status} | top: {entries}"
FINAL_FORMAT = "✓ Final: guard {status} | {errors} errors, {warnings} warnings"

# Limits
FILE_MAX_LINES = 500
FUNCTION_MAX_LINES = 50
```

## Command Interface

### invar init

```bash
$ invar init

Created:
  INVAR.md                    ← copied from templates/protocol/
  CLAUDE.md                   ← generated from templates/config/
  .invar/context.md           ← generated
  .invar/examples/            ← copied
  .claude/skills/             ← generated (CLI syntax)
  .pre-commit-config.yaml     ← generated

$ invar init --mcp

Created:
  ...
  .claude/skills/             ← generated (MCP syntax)

$ invar init --cursor

Created:
  ...
  .cursorrules                ← generated
```

### invar update

```bash
$ invar update

Checking versions...
  Current: v5.0
  Latest:  v5.1

Updating:
  ✓ INVAR.md overwritten
  ✓ .invar/examples/ overwritten
  ✓ CLAUDE.md merged (user regions preserved)
  ✓ .claude/skills/ merged
  ⊘ .invar/context.md skipped (user-owned)

Run 'invar guard' to verify.
```

### invar sync-self (Invar developers only)

```bash
$ invar sync-self

Syncing Invar project from templates...
  ✓ INVAR.md ← templates/protocol/INVAR.md
  ✓ CLAUDE.md ← templates/config/ + .invar/invar-additions.md
  ✓ .claude/skills/ ← templates/skills/ (MCP syntax)

Invar project synced.
```

## Invar Project Additions

For Invar-specific content not in templates:

```
.invar/
├── context.md              # Project state (user-owned)
├── invar-additions.md      # Invar-specific CLAUDE.md content
└── examples/               # Copied from templates
```

`.invar/invar-additions.md`:
```markdown
## Invar Project Specifics

### Key Documents
| Document | Purpose |
|----------|---------|
| [docs/proposals/](./docs/proposals/) | Development proposals |
| [.invar/context.md](./.invar/context.md) | Project state |

### Dependencies
```bash
pip install -e ".[dev]"
pip install -e runtime/
```
```

When `invar sync-self` runs:
1. Generate CLAUDE.md from template
2. Inject invar-additions.md into user region
3. Result: complete Invar CLAUDE.md

## Implementation Plan

### Phase 1: Restructure templates/ (Day 1)

1. Create new directory structure
2. Create manifest.toml
3. Convert existing templates to Jinja2 format
4. Add syntax variant support

### Phase 2: Unified INVAR.md (Day 1)

1. Merge project INVAR.md (93 lines) with template (208 lines)
2. Target: ~130 lines, self-contained
3. Move to templates/protocol/INVAR.md
4. Delete project root INVAR.md (will be regenerated)

### Phase 3: Template Engine (Day 2)

1. Implement Jinja2 renderer with manifest.toml
2. Implement merge logic for user regions
3. Add CLI/MCP syntax switching

### Phase 4: Commands (Day 2)

1. Implement `invar init` with new templates
2. Implement `invar update` with merge logic
3. Implement `invar sync-self` for Invar developers

### Phase 5: Cleanup (Day 3)

1. Delete sections/ (after merging to skills/)
2. Delete commands/ (per DX-47)
3. Update CLAUDE.md links
4. Run `invar sync-self` to regenerate project files

### Phase 6: Validation (Day 3)

1. Run `invar guard` on all generated files
2. Test `invar init` on clean directory
3. Test `invar update` on existing project
4. Verify MCP/CLI syntax variants

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `src/invar/templates/manifest.toml` | Template behavior definitions |
| `src/invar/templates/protocol/INVAR.md` | Unified protocol (~130 lines) |
| `src/invar/templates/config/*.jinja` | Config templates |
| `src/invar/templates/skills/*.jinja` | Skill templates |
| `src/invar/templates/integrations/*.jinja` | Optional integrations |
| `src/invar/core/protocol.py` | Protocol constants |
| `src/invar/shell/template_engine.py` | Jinja2 renderer |
| `.invar/invar-additions.md` | Invar-specific content |

### Modified Files

| File | Change |
|------|--------|
| `src/invar/shell/init_cmd.py` | Use new template system |
| `src/invar/shell/cli.py` | Add `sync-self`, update `init` |

### Deleted Files

| File | Reason |
|------|--------|
| `/INVAR.md` | Regenerated from templates |
| `/CLAUDE.md` | Regenerated from templates |
| `/.claude/skills/*.md` | Regenerated from templates |
| `/sections/*.md` | Merged into templates/skills/ |
| `templates/commands/` | Per DX-47 |
| `templates/INVAR.md` | Moved to templates/protocol/ |
| `templates/CLAUDE.md.template` | Moved to templates/config/ |
| `templates/skills/*.md` | Converted to .jinja |

## Success Criteria

- [ ] templates/ is the only source for all managed files
- [ ] Invar project files generated via `invar sync-self`
- [ ] New projects work with `invar init`
- [ ] Existing projects update with `invar update` (user content preserved)
- [ ] MCP/CLI syntax switching works correctly
- [ ] No sections/ directory
- [ ] No commands/ directory (per DX-47)

## Dependencies

- **DX-47:** Must resolve command/skill naming before deleting commands/
- **Jinja2:** New dependency for template rendering

## Related Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-45 | **Superseded** - template consistency now built-in |
| DX-46 | **Scope reduced** - now covers docs/ only; INVAR.md/CLAUDE.md/sections handled here |
| DX-47 | **Dependency** - determines commands/ handling |
| DX-48 | **Independent** - can proceed in parallel |
