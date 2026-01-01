# DX-49: Protocol Distribution Unification

> **"One source, one truth, everywhere."**

**Status:** Complete
**Created:** 2025-12-26
**Updated:** 2025-12-26
**Completed:** 2025-12-26
**Implementation Notes:** Skill templates use `skill/extensions` region naming (semantic, not `managed/user`)
**Effort:** 8.5 days
**Risk:** Medium
**Dependencies:** DX-47 (command/skill naming) - Complete

---

## Problem Statement

Current state violates Single Source of Truth (SSOT):

| File Type | Project Version | Template Version | Problem |
|-----------|-----------------|------------------|---------|
| INVAR.md | 93 lines | 208 lines | Different content |
| CLAUDE.md | 97 lines | 133 lines | Different structure |
| skills/*.md | MCP syntax | CLI syntax | Syntax differs, no sync |
| sections/*.md | Exists | N/A | Duplicates skills/ |

**Root cause:** Multiple sources, inconsistent flow direction.

---

## Design Principles

| Priority | Principle | Requirement |
|----------|-----------|-------------|
| 1 | **Single Source** | templates/ is the ONLY source for managed content |
| 2 | **Preserve User Content** | Never overwrite user-owned regions or files |
| 3 | **No Choice** | `invar init` has one mode, no decisions needed |

---

## Content Ownership Model

### Ownership Classification

```
+---------------------------------------------------------------------+
|                    Content Ownership Classification                   |
+---------------------------------------------------------------------+
|  Invar 100% Managed    |  Invar Partial        |  Never Touch        |
|  -------------------   |  -----------------    |  ----------------   |
|  INVAR.md              |  CLAUDE.md            |  settings*.json     |
|  .invar/examples/      |  .claude/skills/      |  .mcp.json          |
|                        |  .claude/commands/    |  Other tool files   |
+---------------------------------------------------------------------+
```

### Three-Region Architecture for Partial Files

Files with partial Invar ownership use region markers:

```markdown
<!--invar:managed version="5.0"-->
[Invar-generated content - overwritten on update]
<!--/invar:managed-->

<!--invar:project-->
[Project-specific content - injected from .invar/project-additions.md]
[Only used by sync-self for Invar project]
<!--/invar:project-->

<!--invar:user-->
[User-defined content - NEVER overwritten]
<!--/invar:user-->

[Unmarked content below - preserved as-is, may be from other tools]
```

### manifest.toml Ownership Rules

```toml
# templates/manifest.toml

[meta]
version = "5.0"
workflow = "USBV"

[ownership]
# Fully managed - safe to overwrite completely
fully_managed = [
    "INVAR.md",
    ".invar/examples/**",
]

# Partially managed - only update marked regions
partially_managed = [
    "CLAUDE.md",
    ".claude/skills/*/SKILL.md",
    ".claude/commands/*.md",
]

# Never touch - other tools or user private files
never_touch = [
    ".claude/settings*.json",
    ".mcp.json",
    ".cursorrules",           # Unless --cursor flag used
    ".aider*",                # Unless --aider flag used
]

[regions]
# Region behavior for partially managed files
"CLAUDE.md" = [
    { name = "managed", action = "overwrite" },
    { name = "project", action = "inject", source = ".invar/project-additions.md" },
    { name = "user", action = "preserve" },
]

".claude/skills/*/SKILL.md" = [
    { name = "skill", action = "overwrite" },
    { name = "extensions", action = "preserve" },
]
```

---

## Solution: Unified Source in templates/

### Core Principle

```
+---------------------------------------------------------------------+
|                 templates/ = Single Source of Truth                  |
|                                                                      |
|  Everything flows FROM templates, never TO templates                 |
+---------------------------------------------------------------------+
                              |
         +--------------------+--------------------+
         v                    v                    v
  +--------------+     +--------------+      +--------------+
  | invar        |     | invar init   |      | invar        |
  | sync-self    |     | (new proj)   |      | update       |
  +--------------+     +--------------+      +--------------+
         |                    |                    |
         v                    v                    v
  +--------------+     +--------------+      +--------------+
  | Invar proj   |     | New project  |      | Existing     |
  | + MCP syntax |     | + CLI syntax |      | project      |
  | + additions  |     | + defaults   |      | + preserve   |
  +--------------+     +--------------+      +--------------+
```

### Templates Directory Structure

```
src/invar/templates/
+-- manifest.toml              # Ownership and behavior definitions
|
+-- protocol/
|   +-- INVAR.md               # Protocol (~200 lines, self-contained)
|
+-- config/
|   +-- CLAUDE.md.jinja        # Only managed region content
|   +-- context.md.jinja       # .invar/context.md template
|   +-- pre-commit.yaml.jinja
|
+-- skills/                    # MCP/CLI syntax switching
|   +-- develop.md.jinja
|   +-- investigate.md.jinja
|   +-- propose.md.jinja
|   +-- review.md.jinja
|
+-- commands/                  # User-invokable commands
|   +-- audit.md
|   +-- guard.md
|
+-- examples/                  # Direct copy
|   +-- README.md
|   +-- contracts.py
|   +-- core_shell.py
|
+-- integrations/              # Optional (--cursor, --aider)
    +-- cursorrules.jinja
    +-- aider.conf.yml.jinja
```

---

## Region Update Algorithm

```python
def update_file_with_regions(path: Path, new_content: dict[str, str]) -> str:
    """
    Update file preserving non-Invar content.

    Args:
        path: Target file path
        new_content: {"managed": "...", "project": "..."}

    Returns:
        Updated file content
    """
    if not path.exists():
        return render_new_file(new_content)

    content = path.read_text()

    # Parse existing regions
    regions = parse_invar_regions(content)
    # regions = {
    #     "managed": {"start": 0, "end": 100, "content": "..."},
    #     "project": {"start": 102, "end": 150, "content": "..."},
    #     "user": {"start": 152, "end": 200, "content": "..."},
    #     "unmanaged": ["...before first marker...", "...after last marker..."]
    # }

    # Replace managed region only
    if "managed" in regions:
        regions["managed"]["content"] = new_content["managed"]
    else:
        # No managed region = first-time adoption, insert at top
        return insert_at_top(content, new_content["managed"])

    # Replace project region (sync-self only)
    if "project" in new_content and "project" in regions:
        regions["project"]["content"] = new_content["project"]

    # user region and unmanaged content: ALWAYS preserved

    return reconstruct_file(regions)


def validate_before_update(path: Path) -> Result[None, str]:
    """Validate before update to prevent accidental overwrites."""
    if not path.exists():
        return Success(None)

    content = path.read_text()

    if "<!--invar:" not in content and path.name == "CLAUDE.md":
        return Failure(
            f"{path} has no Invar markers. "
            "Run 'invar init --adopt' to add markers."
        )

    return Success(None)
```

---

## Command Behaviors

### Command Comparison

| Operation | INVAR.md | CLAUDE.md managed | CLAUDE.md project | CLAUDE.md user | Skills | .mcp.json |
|-----------|----------|-------------------|-------------------|----------------|--------|-----------|
| `invar init` | Create | Create | -- | Create empty | Create (CLI) | Never |
| `invar update` | Overwrite | Overwrite | -- | **Preserve** | Overwrite skill region | Never |
| `invar sync-self` | Overwrite | Overwrite | Inject from additions | **Preserve** | Overwrite (MCP) | Never |

### invar init

```bash
$ invar init

Created:
  INVAR.md                    <- copied from templates/protocol/
  CLAUDE.md                   <- generated from templates/config/
  .invar/context.md           <- generated
  .invar/examples/            <- copied
  .claude/skills/             <- generated (CLI syntax)
  .claude/commands/           <- copied
  .pre-commit-config.yaml     <- generated

Preserved (not touched):
  .mcp.json                   <- existing file preserved
  .claude/settings.local.json <- existing file preserved
```

### invar update

```bash
$ invar update

Checking versions...
  Current: v5.0
  Latest:  v5.1

Updating:
  * INVAR.md overwritten
  * .invar/examples/ overwritten
  * CLAUDE.md merged (user region preserved)
  * .claude/skills/ merged (extensions preserved)
  o .invar/context.md skipped (user-owned)
  o .mcp.json skipped (never-touch)

Run 'invar guard' to verify.
```

### invar sync-self (Invar Project Only)

```bash
$ invar sync-self

Syncing Invar project from templates...
  * INVAR.md <- templates/protocol/INVAR.md
  * CLAUDE.md <- templates/config/ + .invar/project-additions.md
  * .claude/skills/ <- templates/skills/ (MCP syntax)

Preserved:
  o .claude/settings.local.json (never-touch)
  o .mcp.json (never-touch)
  o CLAUDE.md user region (preserved)

Invar project synced.
```

---

## Invar Project Specifics

### .invar/project-additions.md

For Invar project-specific content not in templates:

```markdown
## Invar Project Specifics

### Key Documents

| Document | Purpose |
|----------|---------|
| [docs/proposals/](./docs/proposals/) | Development proposals |
| [.invar/context.md](./.invar/context.md) | Project state |

### Project Structure

\`\`\`
src/invar/
+-- core/           # Pure logic, @pre/@post required, no I/O
+-- shell/          # I/O operations, Result[T, E] required
    +-- commands/   # CLI commands (guard, init)
    +-- prove/      # Verification (crosshair, hypothesis)
\`\`\`

### Dependencies

\`\`\`bash
pip install -e ".[dev]"    # Development mode
pip install -e runtime/    # Runtime in dev mode
\`\`\`

### PyPI Packages

| Package | Purpose |
|---------|---------|
| `invar-tools` | Dev tools (guard, sig, map) |
| `invar-runtime` | Runtime contracts (@pre, @post) |
```

### sync-self Flow

```
1. Generate CLAUDE.md managed region from template
2. Read .invar/project-additions.md
3. Inject into project region
4. Preserve user region
5. Preserve unmarked content (e.g., from claude init)
6. Write result
```

---

## Template Syntax (Jinja2)

### Skills Template Example

```jinja
{# skills/develop.md.jinja #}
---
name: develop
description: Implementation phase following USBV workflow.
---

<!--invar:skill-->
# Development Mode

## Entry Actions (REQUIRED)

{% if syntax == "mcp" %}
\`\`\`python
invar_guard(changed=true)
invar_map(top=10)
\`\`\`
{% else %}
\`\`\`bash
invar guard --changed
invar map --top 10
\`\`\`
{% endif %}

**Display:**
\`\`\`
Check-In: guard [PASS/FAIL] | top: [entry1], [entry2], [entry3]
\`\`\`

Then read `.invar/context.md` for project state.

## USBV Workflow

[... rest of skill content ...]
<!--/invar:skill-->

<!--invar:extensions-->
## Custom Extensions

<!-- Users can add project-specific extensions here -->
<!--/invar:extensions-->
```

### CLAUDE.md Template Example

```jinja
{# config/CLAUDE.md.jinja #}
<!--invar:managed version="{{ version }}"-->
# Project Development Guide

> **Protocol:** Follow [INVAR.md](./INVAR.md) for Check-In, USBV workflow, Task Completion.

## Check-In / Final

**First message:**
\`\`\`
Check-In: guard PASS | top: <entry1>, <entry2>
\`\`\`

**Last message:**
\`\`\`
Final: guard PASS | 0 errors, N warnings
\`\`\`

Then read `.invar/context.md` for project state.

## Project Structure

\`\`\`
src/{project}/
+-- core/    # Pure logic (@pre/@post, doctests, no I/O)
+-- shell/   # I/O operations (Result[T, E] return type)
\`\`\`

## Commands & Skills

| Type | Name | Purpose |
|------|------|---------|
| Command | `/audit` | Read-only code review |
| Command | `/guard` | Run Invar verification |
| Skill | `/investigate` | Research mode, no code changes |
| Skill | `/propose` | Decision facilitation |
| Skill | `/develop` | USBV implementation workflow |
| Skill | `/review` | Adversarial review with fix loop |

## Workflow Routing (MANDATORY)

| Trigger Words | Skill | Notes |
|---------------|-------|-------|
| "review", "review and fix" | `/review` | Adversarial review with fix loop |
| "implement", "add", "fix", "update" | `/develop` | Unless in review context |
| "why", "explain", "investigate" | `/investigate` | Research mode, no code changes |
| "compare", "should we", "design" | `/propose` | Decision facilitation |

**Violation check (before writing ANY code):**
- "Am I in a workflow?"
- "Did I invoke the correct skill?"
<!--/invar:managed-->

<!--invar:project-->
<!-- Injected from .invar/project-additions.md by sync-self -->
<!--/invar:project-->

<!--invar:user-->
## Project-Specific Rules

<!-- Add your team conventions below -->

## Overrides

<!-- Document any exceptions to INVAR.md rules -->
<!--/invar:user-->

---

*Generated by Invar v{{ version }}. Edit user sections freely.*
```

---

## Unified INVAR.md (~200 lines)

Target: Self-contained protocol document, no external references.

Key sections:
- Six Laws
- Core/Shell Architecture with examples
- Check-In / Final format
- USBV Workflow
- Commands reference
- Markers reference
- Size limits

See `templates/protocol/INVAR.md` for full content.

---

## Delete sections/

Per unified source principle, sections/ content merges into skills/:

| Current | Action |
|---------|--------|
| sections/develop.md | -> skills/develop.md.jinja |
| sections/investigate.md | -> skills/investigate.md.jinja |
| sections/propose.md | -> skills/propose.md.jinja |
| sections/review.md | -> skills/review.md.jinja |
| sections/reference.md | -> INVAR.md (Markers section) |

**Delete sections/ directory after merge.**

---

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
    "sig": "invar sig <file>",
    "map": "invar map --top 10",
}

MCP_COMMANDS = {
    "guard": "invar_guard()",
    "guard_changed": "invar_guard(changed=true)",
    "sig": 'invar_sig(target="<file>")',
    "map": "invar_map(top=10)",
}

# Formats
CHECKIN_FORMAT = "Check-In: guard {status} | top: {entries}"
FINAL_FORMAT = "Final: guard {status} | {errors} errors, {warnings} warnings"

# Limits
FILE_MAX_LINES = 500
FUNCTION_MAX_LINES = 50
```

---

## Implementation Plan

### Phase 1: Create manifest.toml + Region Parser (Day 1)

1. Create `templates/manifest.toml` with ownership rules
2. Implement region parser for `<!--invar:...-->` markers
3. Implement region reconstruction logic
4. Add tests for region parsing

### Phase 2: Jinja2 Template Engine (Day 1)

1. Add Jinja2 dependency
2. Implement template renderer with manifest.toml
3. Add CLI/MCP syntax variable support
4. Add version variable injection

### Phase 3: Update `invar init` (Day 1)

1. Use new template system
2. Generate files with region markers
3. Respect never_touch list
4. Test on clean directory

### Phase 4: Implement `invar update` (Day 1)

1. Implement region-preserving update logic
2. Validate before update (check for markers)
3. Report what was updated/preserved
4. Test on existing project

### Phase 5: Implement `invar sync-self` (Day 1)

1. Detect Invar project (check for specific markers)
2. Read .invar/project-additions.md
3. Inject into project region
4. Use MCP syntax for skills
5. Test on Invar project

### Phase 6: Merge sections/ to skills/ (Day 0.5)

1. Merge content from each section to corresponding skill
2. Update INVAR.md to include reference.md content
3. Delete sections/ directory
4. Update all links

### Phase 7: Unify INVAR.md (Day 0.5)

1. Create unified ~200 line INVAR.md
2. Self-contained, no external references
3. Move to templates/protocol/
4. Run sync-self to update project

### Phase 8: Template System Testing (Day 1)

1. Test `invar init` on clean directory
2. Test `invar update` on existing project
3. Test `invar sync-self` on Invar project
4. Verify MCP/CLI syntax switching
5. Run `invar guard` on all generated files

### Phase 9: Documentation Deep Review (Day 1)

From Agent perspective, review all protocol documents:

#### 9.1 Collect Review Materials
- Export design decisions from proposals/
- Collect Lessons Learned from context.md
- List known documentation issues

#### 9.2 INVAR.md Review
- [ ] Content completeness check
- [ ] Agent usability evaluation
- [ ] Structure optimization
- [ ] Example code verification

#### 9.3 CLAUDE.md Review
- [ ] Region division rationality
- [ ] Project-specific info completeness
- [ ] Consistency with INVAR.md

#### 9.4 Skills Review
- [ ] Unify 4 skills structure
- [ ] Entry/Exit Actions consistency
- [ ] Tool selection table accuracy

#### 9.5 Optimization Execution
Apply patterns:
- **Redundancy elimination**: Cross-reference instead of duplicate
- **Structurization**: Tables > paragraphs
- **Executability**: "Run X after Y" instead of "Consider running X"
- **Layering**: Quick Reference (5 lines) + Full Details (expandable)

#### 9.6 Agent Simulation Verification
- [ ] Simulate new session Check-In
- [ ] Simulate /develop workflow
- [ ] Simulate error handling path

### Phase 10: Final Validation (Day 0.5)

1. Full `invar guard` pass
2. Verify no broken links
3. Verify example code runs
4. Document any remaining issues

**Total: 8.5 days**

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `src/invar/templates/manifest.toml` | Ownership and behavior definitions |
| `src/invar/templates/protocol/INVAR.md` | Unified protocol (~200 lines) |
| `src/invar/templates/config/*.jinja` | Config templates |
| `src/invar/templates/skills/*.jinja` | Skill templates with syntax switching |
| `src/invar/core/protocol.py` | Protocol constants |
| `src/invar/shell/template_engine.py` | Jinja2 renderer + region parser |
| `.invar/project-additions.md` | Invar project-specific content |

### Modified Files

| File | Change |
|------|--------|
| `src/invar/shell/commands/init_cmd.py` | Use new template system |
| `src/invar/shell/cli.py` | Add `sync-self`, update `init` |
| `pyproject.toml` | Add Jinja2 dependency |

### Deleted Files

| File | Reason |
|------|--------|
| `/sections/*.md` | Merged into templates/skills/ |
| `templates/INVAR.md` | Moved to templates/protocol/ |
| `templates/CLAUDE.md.template` | Converted to templates/config/*.jinja |
| `templates/skills/*.md` | Converted to .jinja |

---

## Success Criteria

### Core Requirements
- [ ] templates/ + .invar/project-additions.md are the only sources
- [ ] `sync-self` never overwrites user region or never_touch files
- [ ] `sync-self` correctly injects project-additions.md
- [ ] .claude/settings.local.json etc. are never touched
- [ ] MCP/CLI syntax switching works correctly
- [ ] sections/ directory deleted

### Agent Usability (Phase 9)
- [ ] Agent can execute Check-In correctly after reading INVAR.md
- [ ] All trigger word -> Skill mappings are unambiguous
- [ ] 0 dead links in documentation
- [ ] 100% example code is runnable
- [ ] Total documentation reduced 20%+ (Context Economy)

---

## Dependencies

- **DX-47:** Complete - command/skill naming resolved
- **Jinja2:** New dependency for template rendering

---

## Related Proposals

| Proposal | Relationship |
|----------|--------------|
| DX-45 | **Superseded** - template consistency now built-in |
| DX-46 | **Scope reduced** - now covers docs/ only |
| DX-47 | **Complete** - commands/ handling determined |
| DX-48 | **Complete** - code structure reorganized |
| DX-50 | **Related** - workflow enforcement in CLAUDE.md |
