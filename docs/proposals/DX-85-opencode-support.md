# DX-85: OpenCode Agent Support

**Status**: Draft
**Created**: 2026-01-05
**Priority**: Medium
**Type**: Enhancement

---

## Problem

### Current Limitation

Invar currently supports:
- ✅ Claude Code (native: hooks + MCP + skills)
- ✅ Pi (native: TypeScript hooks + skill sharing)
- ❌ **OpenCode** (not supported)

**User Experience Gap:**
```bash
$ invar init
# Options: Claude Code, Pi, Other (AGENT.md)
# ❌ No "OpenCode" option
```

### Real-World Scenarios

#### Scenario 1: OpenCode Users
**Context:**
- Users want to use Invar with OpenCode agent
- Need native setup like Claude Code and Pi
- Currently must use "Other (AGENT.md)" manual approach

**Current Workaround (Manual):**
1. Run `invar init` → select "Other (AGENT.md)"
2. Manually copy AGENT.md content
3. Configure MCP if OpenCode supports it
4. No hooks, no automation

**Problems:**
- ❌ Not native experience
- ❌ Missing pytest blocking hooks
- ❌ No protocol injection for long conversations
- ❌ Missing automation

#### Scenario 2: Multi-Agent Projects
**Context:**
- Team uses Claude Code, Pi, and OpenCode
- Need unified setup
- Current DX-81 supports Claude + Pi only

**Current Limitation:**
```bash
$ invar init --claude --pi --openode  # ❌ Not supported
Error: Unknown option: --openode
```

---

## Analysis

### OpenCode Agent Capabilities

**Required Research:**
- [ ] Does OpenCode support MCP servers?
- [ ] Does OpenCode have hooks system?
  - If yes, what type (Shell, Python, TypeScript, JSON)?
  - How to register hooks?
- [ ] Does OpenCode have custom tools system?
  - If yes, how to register tools (directory-based or config-based)?
- [ ] What instruction file format does OpenCode use?
  - CLAUDE.md compatible?
  - Custom format (e.g., .opencoderules)?
- [ ] How does OpenCode discover tools/commands?
- [ ] Does OpenCode support protocol injection (like Pi's `pi.send()`)?

**Implementation Decision:**
- **If OpenCode supports MCP** → Minimal changes (like Cursor)
- **If OpenCode requires hooks** → Need hook manager (like Pi)
- **If OpenCode has custom tools** → Need tool wrapper (like Pi's .pi/tools/)

---

## Design Proposal

### Architecture Pattern (Based on DX-81)

**File Categories:**
```python
FILE_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    # ... existing categories ...
    "openode": [  # NEW
        ("CLAUDE.md", "Agent instructions (OpenCode compatible)"),
        (".claude/skills/", "Workflow automation (OpenCode compatible)"),
        (".mcp.json", "MCP server config (if OpenCode supports MCP)"),
        (".opencoderules", "OpenCode-specific rules (if needed)"),  # MAYBE
    ],
}

AGENT_CONFIGS: dict[str, dict[str, str]] = {
    "claude": {"name": "Claude Code", "category": "claude"},
    "pi": {"name": "Pi Coding Agent", "category": "pi"},
    "openode": {"name": "OpenCode", "category": "openode"},  # NEW
    "generic": {"name": "Other (AGENT.md)", "category": "generic"},
}
```

**Command Line Support:**
```bash
# Single agent
invar init --openode

# Multi-agent (DX-81 pattern)
invar init --claude --openode
invar init --pi --openode
invar init --claude --pi --openode  # All three agents

# Interactive mode (checkbox selection)
invar init  # Select with Space key
```

---

### Scenario A: OpenCode Supports MCP (Recommended)

**Assumption:** OpenCode has MCP client support like Cursor, Cline, Continue.

**File Additions:**
1. **Agent Config** (`src/invar/shell/commands/init.py`)
   - Add `openode` to AGENT_CONFIGS
   - Add `openode` category to FILE_CATEGORIES
   - Update `_prompt_agent_selection()` with OpenCode choice

2. **No Hook Files Needed**
   - OpenCode uses MCP directly
   - Hooks managed by OpenCode (if any)
   - No shell scripts or TypeScript needed

**Implementation:**

```python
# src/invar/shell/commands/init.py:60-70 (AGENT_CONFIGS)
AGENT_CONFIGS: dict[str, dict[str, str]] = {
    "claude": {"name": "Claude Code", "category": "claude"},
    "pi": {"name": "Pi Coding Agent", "category": "pi"},
    "openode": {"name": "OpenCode", "category": "openode"},  # NEW
    "generic": {"name": "Other (AGENT.md)", "category": "generic"},
}

# src/invar/shell/commands/init.py:92-110 (FILE_CATEGORIES)
FILE_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    # ... existing categories ...
    "openode": [  # NEW: DX-85
        ("CLAUDE.md", "Agent instructions (OpenCode compatible)"),
        (".claude/skills/", "Workflow automation (OpenCode compatible)"),
        (".mcp.json", "MCP server config (OpenCode compatible)"),
    ],
}

# src/invar/shell/commands/init.py:260-280 (_prompt_agent_selection)
def _prompt_agent_selection(console: Console) -> list[str]:
    """Prompt user to select agents via checkboxes."""
    from questionary import checkbox

    choices = [
        {"name": "Claude Code", "value": "claude"},
        {"name": "Pi Coding Agent", "value": "pi"},
        {"name": "OpenCode", "value": "openode"},  # NEW
        {"name": "Other (AGENT.md)", "value": "generic"},
    ]

    selected = checkbox(
        message="Select agents to install:",
        choices=choices,
        instruction="Press Space to select, Enter to continue",
        validate=lambda x: len(x) > 0 or "Must select at least one",
    ).ask()

    return selected  # Returns list: ["claude", "openode"]
```

**Files Created:**
```
project/
├── CLAUDE.md              # Shared (works with OpenCode)
├── .claude/
│   ├── skills/            # Shared (works with OpenCode)
│   └── commands/          # Shared (works with OpenCode)
├── .invar/                # Shared config
└── .mcp.json             # OpenCode uses MCP (same as Claude)
```

**What's Installed:**
- ✅ CLAUDE.md → OpenCode instruction file
- ✅ .claude/skills/ → Workflow automation (develop, review, investigate, propose)
- ✅ .mcp.json → MCP server config
- ✅ MCP tools: invar_guard, invar_sig, invar_map, invar_doc_*

**What's NOT Installed:**
- ❌ No hooks (OpenCode manages hooks internally)
- ❌ No custom tools (MCP tools auto-discovered)

**Advantages:**
- ✅ Minimal code changes (~50 lines)
- ✅ Fast implementation (2-3 hours)
- ✅ Leverages existing MCP server
- ✅ Works with all MCP tools

**Disadvantages:**
- ❌ No pytest blocking (unless OpenCode has hooks)
- ❌ No protocol injection for long conversations
- ❌ Depends on OpenCode's hook system

---

### Scenario B: OpenCode Requires Custom Hooks

**Assumption:** OpenCode has hook system (like Claude Code's hooks, but different API).

**New Files Needed:**

1. **Hook Manager** (`src/invar/shell/openode_hooks.py`)
   - Copy pattern from `pi_hooks.py`
   - Adapt for OpenCode's hook format

2. **Hook Templates** (`src/invar/shell/templates/hooks/openode/`)
   - Create hook templates based on OpenCode's API
   - Templates: PreToolUse.{ext}, UserPromptSubmit.{ext}, etc.

3. **Hook Directory** (`.opencode/hooks/`)
   - Agent-specific hooks directory
   - No conflicts with .claude/hooks/ and .pi/hooks/

**Implementation:**

```python
# src/invar/shell/openode_hooks.py (NEW FILE - ~200 lines)
"""
OpenCode hooks for Invar.

DX-85: OpenCode agent integration.
- pytest/crosshair blocking via OpenCode hooks
- Protocol injection for long conversations
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader
from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from rich.console import Console

# OpenCode hooks directory
OPENCODE_HOOKS_DIR = ".opencode/hooks"  # NEW: Isolated directory
PROTOCOL_VERSION = "5.0"

def get_opencode_templates_path() -> Path:
    """Get path to OpenCode hook templates."""
    return Path(__file__).parent.parent / "templates" / "hooks" / "openode"

def generate_opencode_hook_content(hook_type: str, project_path: Path) -> Result[str, str]:
    """Generate OpenCode hook content from template."""
    templates_path = get_opencode_templates_path()
    template_file = f"{hook_type}.{ext}.jinja"  # OpenCode file extension

    if not (templates_path / template_file).exists():
        return Failure(f"Template not found: {template_file}")

    try:
        env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            keep_trailing_newline=True,
        )
        template = env.get_template(template_file)

        # Determine guard command based on syntax
        syntax = detect_syntax(project_path)
        guard_cmd = "invar_guard" if syntax == "mcp" else "invar guard"

        # Detect project language
        from invar.core.language import detect_language_from_markers
        markers = frozenset(f.name for f in project_path.iterdir() if f.is_file())
        language = detect_language_from_markers(markers)

        # Build context
        context = {
            "protocol_version": PROTOCOL_VERSION,
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
            "guard_cmd": guard_cmd,
            "language": language,
        }

        # For protocol injection hooks, add INVAR.md content
        if hook_type == "UserPromptSubmit":
            context["invar_protocol"] = get_invar_md_content(project_path)

        content = template.render(**context)
        return Success(content)
    except Exception as e:
        return Failure(f"Failed to generate {hook_type} hook: {e}")

def install_opencode_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Install OpenCode hooks for Invar.

    Creates .opencode/hooks/ with hook files.
    """
    hooks_dir = project_path / OPENCODE_HOOKS_DIR
    hooks_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold]Installing OpenCode hooks (DX-85)...[/bold]")
    console.print("  Hooks will:")
    console.print("    ✓ Block pytest/crosshair → redirect to invar guard")
    console.print("    ✓ Refresh protocol in long conversations")
    console.print("")

    installed: list[str] = []
    failed: list[str] = []

    # OpenCode hook types (based on API research)
    HOOK_TYPES = ["PreToolUse", "UserPromptSubmit", "Stop"]

    for hook_type in HOOK_TYPES:
        result = generate_opencode_hook_content(hook_type, project_path)
        if isinstance(result, Failure):
            console.print(f"  [red]Failed:[/red] {result.failure()}")
            failed.append(hook_type)
            continue

        content = result.unwrap()
        hook_file = hooks_dir / f"invar.{hook_type}.{ext}"  # OpenCode extension
        hook_file.write_text(content)

        console.print(f"  [green]Created[/green] {OPENCODE_HOOKS_DIR}/invar.{hook_type}.{ext}")
        installed.append(f"invar.{hook_type}.{ext}")

    if installed:
        console.print("\n  [bold green]✓ OpenCode hooks installed[/bold green]")
        console.print("  [yellow]⚠ Restart OpenCode session for hooks to take effect[/yellow]")

    if failed:
        return Failure(f"Failed to install hooks: {', '.join(failed)}")

    return Success(installed)

def sync_opencode_hooks(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """Update OpenCode hooks with current INVAR.md content."""
    # Similar to sync_claude_hooks() and sync_pi_hooks()
    hooks_dir = project_path / OPENCODE_HOOKS_DIR

    if not hooks_dir.exists():
        return Success([])

    # Check version
    # ... implementation similar to Claude hooks ...

def remove_opencode_hooks(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """Remove OpenCode hooks."""
    hooks_dir = project_path / OPENCODE_HOOKS_DIR

    if hooks_dir.exists():
        # Remove all invar.* hook files
        # ... implementation similar to Claude hooks ...

        console.print("[bold green]✓ OpenCode hooks removed[/bold green]")
    else:
        console.print("[dim]No OpenCode hooks installed[/dim]")

    return Success(None)
```

**Integration in init.py:**
```python
# src/invar/shell/commands/init.py:624-630 (after Pi hooks)
# Install OpenCode hooks if selected
if "openode" in agents and selected_files.get(".opencode/hooks/", True):
    from invar.shell.openode_hooks import install_opencode_hooks
    result = install_opencode_hooks(path, console)
    if isinstance(result, Failure):
        console.print(f"[yellow]Warning:[/yellow] {result.failure()}")
```

**File Structure:**
```
project/
├── CLAUDE.md
├── .claude/
│   └── skills/            # Shared
├── .opencode/
│   └── hooks/             # OpenCode-specific hooks
│       ├── invar.PreToolUse.{ext}
│       ├── invar.UserPromptSubmit.{ext}
│       └── invar.Stop.{ext}
├── .mcp.json
└── .invar/
```

**Advantages:**
- ✅ Full automation (pytest blocking, protocol injection)
- ✅ Native OpenCode experience
- ✅ Independent from other agents

**Disadvantages:**
- ❌ Requires research into OpenCode hook API
- ❌ More code (~300 lines: hook manager + templates)
- ❌ Longer implementation (8-10 hours)

---

### Scenario C: OpenCode Uses Different Instruction File

**Assumption:** OpenCode doesn't read CLAUDE.md, uses custom format.

**Template Changes:**

1. **Instruction File Template**
   - Create `src/invar/shell/templates/config/OPENCODE.md.jinja`
   - Adapt CLAUDE.md content for OpenCode

2. **Manager Update**
   - `claude_hooks.py::get_invar_md_content()`
   - Check for OPENCODE.md first, fallback to CLAUDE.md

**Implementation:**

```python
# src/invar/shell/templates/config/OPENCODE.md.jinja (NEW)
# OpenCode Agent Instructions

# OpenCode Protocol Integration
# This file contains Invar's USBV workflow, Core/Shell architecture,
# and contract-driven development patterns optimized for OpenCode.

# ... (adapted from CLAUDE.md template)

# OpenCode-Specific Instructions
# MCP Tools: Use invar_guard, invar_sig, invar_map
# CLI Commands: Use `invar guard`, `invar sig`, `invar map`
# Workflow: Follow USBV (Understand → Specify → Build → Validate)
```

```python
# src/invar/shell/claude_hooks.py:62-71 (get_invar_md_content)
def get_invar_md_content(project_path: Path) -> str:
    """Read instruction file content for protocol injection.

    DX-85: Check for OPENCODE.md first (OpenCode-specific).
    Falls back to CLAUDE.md (universal).
    """
    # NEW: Check for OpenCode-specific instruction file
    opencode_md = project_path / "OPENCODE.md"
    if opencode_md.exists():
        return opencode_md.read_text()

    # Existing: Check for CLAUDE.md
    invar_md = project_path / "INVAR.md"
    if invar_md.exists():
        return invar_md.read_text()

    # Fallback to template
    template_path = Path(__file__).parent.parent / "templates" / "protocol" / "INVAR.md"
    if template_path.exists():
        return template_path.read_text()
    return "# INVAR.md not found"
```

**Integration in init.py:**
```python
# src/invar/shell/commands/init.py:92-110 (FILE_CATEGORIES)
FILE_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    # ... existing categories ...
    "openode": [  # NEW
        ("OPENCODE.md", "OpenCode agent instructions"),  # NEW: Custom instruction file
        (".claude/skills/", "Workflow automation (OpenCode compatible)"),
        (".mcp.json", "MCP server config (if supported)"),
        (".opencode/hooks/", "OpenCode-specific hooks (if needed)"),  # MAYBE
    ],
}
```

---

## Implementation Roadmap

### Phase 1: Research (2-4 hours)

**Priority: P0 - Required**

1. **Document OpenCode Agent Capabilities:**
   - [ ] Does OpenCode support MCP?
   - [ ] Hook system (type, API, registration)
   - [ ] Custom tools system (directory-based or config-based?)
   - [ ] Instruction file format (CLAUDE.md or custom?)
   - [ ] Protocol injection mechanism (if any)

2. **Analyze OpenCode Integration Examples:**
   - [ ] Find existing tool integrations with OpenCode
   - [ ] Document hook patterns
   - [ ] Document tool registration patterns

3. **Create Research Document:**
   - [ ] `docs/research/opencode-capabilities.md`
   - [ ] Include code examples
   - [ ] Include API references

---

### Phase 2: Choose Implementation Path (Decision Gate)

**Research Review Meeting:**
- Present findings from Phase 1
- Choose Scenario A, B, or C
- Document decision rationale

**Decision Matrix:**

| Scenario | OpenCode Supports | Code Complexity | Time | Coverage |
|----------|-------------------|------------------|------|----------|
| **A: MCP-only** | ✅ MCP | Low (~50 lines) | 2-3h | High (MCP tools) |
| **B: Custom Hooks** | ✅ Hooks | Medium (~300 lines) | 8-10h | Full (hooks + MCP) |
| **C: Custom Instructions** | ❌ MCP + ❌ Hooks | Low (~100 lines) | 4-5h | Medium (custom file) |

**Recommendation:**
- **If OpenCode supports MCP** → Start with Scenario A (fast, minimal)
- **If OpenCode requires hooks** → Use Scenario B (full automation)
- **If OpenCode uses custom instruction file** → Add Scenario C features

---

### Phase 3: Core Implementation (4-10 hours, depends on scenario)

#### If Scenario A (MCP-only):

1. [ ] Update `AGENT_CONFIGS` in `src/invar/shell/commands/init.py`
2. [ ] Add `openode` category to `FILE_CATEGORIES`
3. [ ] Update `_prompt_agent_selection()` with OpenCode choice
4. [ ] Test `invar init --openode`
5. [ ] Test multi-agent: `invar init --claude --openode`

**Estimated:** 2-3 hours

#### If Scenario B (Custom Hooks):

1. [ ] Create `src/invar/shell/openode_hooks.py`
2. [ ] Create hook templates in `src/invar/shell/templates/hooks/openode/`
3. [ ] Implement `generate_opencode_hook_content()`
4. [ ] Implement `install_opencode_hooks()`
5. [ ] Implement `sync_opencode_hooks()`
6. [ ] Implement `remove_opencode_hooks()`
7. [ ] Add to `FILE_CATEGORIES`
8. [ ] Integrate in `init.py`
9. [ ] Test hook installation
10. [ ] Test hook functionality (pytest blocking, protocol injection)

**Estimated:** 8-10 hours

#### If Scenario C (Custom Instructions):

1. [ ] Create `src/invar/shell/templates/config/OPENCODE.md.jinja`
2. [ ] Update `get_invar_md_content()` to check for OPENCODE.md
3. [ ] Test instruction file rendering
4. [ ] Test protocol injection

**Estimated:** 4-5 hours

---

### Phase 4: Testing (3-4 hours)

**Priority: P0 - Required**

1. [ ] Unit tests for hook generation (if Scenario B)
2. [ ] Integration tests for `invar init --openode`
3. [ ] Multi-agent tests (Claude + Pi + OpenCode)
4. [ ] File deduplication tests
5. [ ] Hook functionality tests (if hooks implemented)
6. [ ] MCP server tests (if Scenario A)
7. [ ] Protocol injection tests (if hooks implemented)

**Test Coverage:**
```bash
# Single agent
pytest tests/integration/test_opencode.py -k "single_agent"

# Multi-agent
pytest tests/integration/test_opencode.py -k "multi_agent"

# File conflicts
pytest tests/integration/test_opencode.py -k "file_deduplication"
```

---

### Phase 5: Documentation (2-3 hours)

**Priority: P1 - Important**

1. [ ] Update `docs/guides/multi-agent.md` with OpenCode
2. [ ] Create OpenCode guide: `docs/guides/opencode.md`
3. [ ] Update `README.md` agent support table
4. [ ] Update `CLAUDE.md` with OpenCode examples
5. [ ] Create design doc: `docs/proposals/DX-85-opencode-support.md` (this file)
6. [ ] Update CHANGELOG.md

**Documentation Content:**

```markdown
# docs/guides/opencode.md (NEW)

## OpenCode Agent Support

### Status: ✅ Coming Soon (DX-85)

### Quick Start

```bash
# Setup for OpenCode
invar init --openode

# Multi-agent setup (Claude + Pi + OpenCode)
invar init --claude --pi --openode
```

### Features

| Feature | Support |
|---------|----------|
| USBV Workflow | ✅ Full |
| Guard via MCP | ✅ Full |
| pytest Blocking | ⚠️ OpenCode hooks (if supported) |
| Protocol Refresh | ⚠️ OpenCode hooks (if supported) |
| Skills Automation | ✅ Full (.claude/skills/) |

### MCP Configuration

OpenCode uses MCP servers (if supported):

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

### Troubleshooting

[... content similar to other agent guides ...]
```

---

### Phase 6: Release (1 hour)

**Priority: P1 - Important**

1. [ ] Update CHANGELOG.md with DX-85
2. [ ] Version bump (v1.18.0)
3. [ ] Release notes
4. [ ] Test release on clean project

**Release Notes:**

```markdown
## [1.18.0] - 2026-01-XX

### Added
- DX-85: OpenCode agent support
  - Native setup via `invar init --openode`
  - Multi-agent support: `invar init --claude --pi --openode`
  - MCP tools integration
  - Shared workflow skills (.claude/skills/)

### Changed
- Updated multi-agent guide with OpenCode
- Updated README.md agent support table

### Fixed
- None
```

---

## Total Effort Estimate

| Phase | Scenario A (MCP) | Scenario B (Hooks) | Scenario C (Instructions) |
|--------|-------------------|-------------------|------------------------|
| Phase 1: Research | 2-4h | 2-4h | 2-4h |
| Phase 2: Decision | 0.5h | 0.5h | 0.5h |
| Phase 3: Implementation | 2-3h | 8-10h | 4-5h |
| Phase 4: Testing | 3-4h | 3-4h | 3-4h |
| Phase 5: Documentation | 2-3h | 2-3h | 2-3h |
| Phase 6: Release | 1h | 1h | 1h |
| **TOTAL** | **10-15 hours** | **17-22 hours** | **13-17 hours** |

---

## Success Criteria

### Functional Requirements

- [ ] User can run `invar init --openode` successfully
- [ ] User can run `invar init --claude --pi --openode` successfully
- [ ] OpenCode agent reads CLAUDE.md or OPENCODE.md
- [ ] MCP tools work in OpenCode (if supported)
- [ ] Hooks work in OpenCode (if supported)

### Integration Requirements

- [ ] No file conflicts with Claude Code and Pi
- [ ] Shared files (CLAUDE.md, skills) work identically
- [ ] Multi-agent mode works correctly
- [ ] File deduplication prevents duplicates

### Documentation Requirements

- [ ] Multi-agent guide updated
- [ ] OpenCode-specific guide created
- [ ] README.md updated
- [ ] CHANGELOG.md updated
- [ ] Design document created

### Quality Requirements

- [ ] All tests passing
- [ ] Guard verification clean (0 errors, 0 warnings)
- [ ] Code follows Invar protocol (@pre/@post, doctests)
- [ ] No shell_orchestration violations

---

## Risks and Mitigations

### Risk 1: OpenCode API Uncertainty

**Risk:** OpenCode's hook/tool API is not documented or changes frequently.

**Mitigation:**
- Start with MCP-only approach (Scenario A) - minimal risk
- Add hooks later if needed (Scenario B)
- Document assumptions clearly

### Risk 2: Instruction File Compatibility

**Risk:** OpenCode doesn't read CLAUDE.md, requires custom format.

**Mitigation:**
- Test with actual OpenCode agent
- Provide OPENCODE.md template (Scenario C)
- Document fallback to CLAUDE.md

### Risk 3: File Conflicts

**Risk:** OpenCode configuration files conflict with existing agents.

**Mitigation:**
- Use isolated directory (`.opencode/`)
- Follow DX-81 multi-agent pattern
- Test all agent combinations

### Risk 4: Breaking Changes

**Risk:** OpenCode updates break Invar integration.

**Mitigation:**
- Use stable APIs (MCP is standard)
- Minimal coupling to OpenCode internals
- Version detection and graceful degradation

---

## Open Questions

1. **OpenCode MCP Support:**
   - Does OpenCode support MCP servers?
   - If yes, what MCP version?
   - Any OpenCode-specific MCP features?

2. **OpenCode Hook System:**
   - Does OpenCode have hooks?
   - What hook types are available?
   - How to register hooks (config file, directory-based)?
   - What file format (Shell, Python, TypeScript, JSON)?

3. **OpenCode Custom Tools:**
   - Does OpenCode support custom tools?
   - How are tools discovered (directory-based, config-based)?
   - What tool protocol (MCP, custom)?

4. **OpenCode Instruction File:**
   - What file format does OpenCode use for instructions?
   - Is CLAUDE.md compatible?
   - If not, what's the custom format?

5. **OpenCode Protocol Injection:**
   - Does OpenCode support protocol injection (like Pi's `pi.send()`)?
   - If yes, what's the API?
   - If no, how to handle long conversations?

---

## Next Steps

1. **Research OpenCode Agent** - Complete Phase 1
2. **Review Research** - Phase 2 decision meeting
3. **Implement Scenario A/B/C** - Phase 3 based on decision
4. **Test Implementation** - Phase 4
5. **Document and Release** - Phase 5-6

**Owner:** @tefx (or assign to contributor)

**Timeline:** 1-2 weeks (depends on research complexity)

---

*Draft created: 2026-01-05*
*Proposal status: Awaiting research and review*
