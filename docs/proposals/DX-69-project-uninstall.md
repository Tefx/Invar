# DX-69: Project Uninstall Command

**Status:** ✅ Complete
**Created:** 2024-12-30
**Author:** Claude

## Problem Statement

When users want to remove Invar from a project, there is no `invar uninstall` command. Users must manually identify and delete Invar-generated files, risking:

1. **Incomplete removal** - Missing files or leaving orphaned configurations
2. **Data loss** - Deleting files that contain user content mixed with Invar content
3. **Broken configurations** - Removing entire config files instead of just Invar sections

### Evidence

User request: "是否有命令可以从项目卸载 invar"

Current situation:
- No uninstall command exists
- Manual deletion risks user data loss
- Files like CLAUDE.md contain both Invar-managed and user regions

## Solution

### Design Principles

1. **Preserve user content** - Never delete user-added content
2. **Use markers for detection** - Only remove content with Invar markers
3. **Safe by default** - Require `--force` for destructive operations
4. **Dry-run support** - Show what would be removed without removing

### File Classification

| File | Detection Method | Removal Strategy |
|------|------------------|------------------|
| `.invar/` | Directory | Delete entirely |
| `invar.toml` | File | Delete entirely |
| `INVAR.md` | File | Delete entirely |
| `CLAUDE.md` | Region markers | Remove `<!--invar:critical-->`, `<!--invar:managed-->`, `<!--invar:project-->` regions, keep `<!--invar:user-->` |
| `.claude/skills/*/SKILL.md` | `_invar:` in YAML frontmatter | Delete if has marker |
| `.claude/commands/*.md` | `_invar:` in YAML frontmatter | Delete if has marker (need to add markers first) |
| `.claude/hooks/*.sh` | `# invar:hook` comment | Delete if has marker |
| `.mcp.json` | JSON structure | Remove `mcpServers.invar` key only |
| `.cursorrules` | `# invar:begin/end` markers | Remove marked region |
| `.aider.conf.yml` | `# invar:begin/end` markers | Remove marked region |
| `.pre-commit-config.yaml` | `# invar:begin/end` markers | Remove marked region |
| `src/core/`, `src/shell/` | Empty check | Delete if empty |

### Implementation Phases

#### Phase 1: Add Missing Markers

**Commands templates** - Add `_invar:` frontmatter:
```yaml
---
_invar:
  version: "5.0"
  type: command
---
# Audit
...
```

**Agent config templates** - Add region markers:
```yaml
# invar:begin
# Invar Protocol Configuration
...
# invar:end
```

#### Phase 2: Implement Uninstall Command

```python
@app.command()
def uninstall(
    path: Path = typer.Argument(Path("."), help="Project path"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be removed"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    keep_claude_md: bool = typer.Option(False, "--keep-claude-md", help="Don't touch CLAUDE.md"),
) -> None:
    """Remove Invar from a project."""
```

#### Phase 3: Region Removal Logic

```python
def remove_invar_regions(content: str) -> str:
    """Remove <!--invar:xxx-->...<!--/invar:xxx--> regions except user region."""
    patterns = [
        (r'<!--invar:critical-->.*?<!--/invar:critical-->\n?', ''),
        (r'<!--invar:managed[^>]*-->.*?<!--/invar:managed-->\n?', ''),
        (r'<!--invar:project-->.*?<!--/invar:project-->\n?', ''),
        (r'# invar:begin\n.*?# invar:end\n?', ''),
    ]
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    return content
```

### CLI Interface

```bash
# Preview what would be removed
invar uninstall --dry-run

# Perform uninstall with confirmation
invar uninstall

# Skip confirmation
invar uninstall --force

# Keep CLAUDE.md intact
invar uninstall --keep-claude-md
```

### Output Format

```
Invar Uninstall Preview
=======================

Will DELETE:
  .invar/                    (directory)
  invar.toml                 (config)
  INVAR.md                   (protocol)
  .claude/skills/develop/    (skill, has _invar marker)
  .claude/skills/review/     (skill, has _invar marker)
  .claude/commands/audit.md  (command, has _invar marker)
  .claude/hooks/*.sh         (hooks, has invar:hook marker)

Will MODIFY:
  CLAUDE.md                  (remove 3 invar regions, keep user region)
  .mcp.json                  (remove mcpServers.invar)
  .cursorrules               (remove invar:begin..end block)
  .aider.conf.yml            (remove invar:begin..end block)

Will SKIP:
  .claude/skills/custom/     (no _invar marker)
  .claude/commands/my-cmd.md (no _invar marker)

Proceed? [y/N]
```

## Alternatives Considered

### Alternative 1: Delete everything with "invar" in name
Rejected: Would miss CLAUDE.md regions, would delete user files containing "invar" string.

### Alternative 2: Track installed files in manifest
Rejected: Requires maintaining state file, complex when files are manually edited.

### Alternative 3: Marker-based detection (chosen)
Pros: Self-describing, no external state, works with manual edits.
Cons: Requires adding markers to templates first.

## Implementation Checklist

- [ ] Add `_invar:` marker to command templates (audit.md, guard.md)
- [ ] Add `# invar:begin/end` markers to agent config templates
- [ ] Implement `uninstall` command in `src/invar/shell/commands/`
- [ ] Add `--dry-run`, `--force`, `--keep-claude-md` options
- [ ] Handle JSON (`.mcp.json`) partial removal
- [ ] Handle YAML (`.aider.conf.yml`) partial removal
- [ ] Handle Markdown (`.cursorrules`) partial removal
- [ ] Clean empty directories (`src/core/`, `src/shell/`, `.claude/skills/`, etc.)
- [ ] Add tests
- [ ] Update `invar --help` and documentation

## Dependencies

None - standalone feature.

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Accidental data loss | `--dry-run` default preview, require `--force` or confirmation |
| Incomplete marker coverage | Phase 1 adds all missing markers before implementing uninstall |
| Edge cases in regex parsing | Comprehensive test coverage for region parsing |
