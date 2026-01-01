# DX-71: Skill Command Simplification

**Status:** Implemented
**Priority:** Low
**Category:** Developer Experience
**Created:** 2026-01-02

## Problem

Current `invar skill` commands are inconsistent with `invar init`:

| Command | Not Exists | Already Exists |
|---------|------------|----------------|
| `init` | Create | **Merge** (idempotent) |
| `skill add` | Install | **Error** |
| `skill update` | **Error** | Overwrite (loses user content) |

Issues:
1. Not idempotent — different commands for install vs update
2. `update` overwrites user customizations in `<!--invar:extensions-->` region
3. Inconsistent with `init`'s merge behavior

## Solution

### 1. Make `add` idempotent

```bash
invar skill add <name>      # Install OR update (merge)
invar skill remove <name>   # Remove
invar skill list            # List available/installed
```

### 2. Use region merge for .md files

Preserve `<!--invar:extensions-->` region, only update `<!--invar:skill-->`:

```markdown
<!--invar:skill-->
... Invar managed content (updated) ...
<!--/invar:skill-->

<!--invar:extensions-->
... User customizations (preserved) ...
<!--/invar:extensions-->
```

### 3. Deprecate `update` command

Keep as alias with deprecation notice for backward compatibility.

### 4. Safe `remove` with custom content check

If skill has custom extensions content, require `--force` (no confirmation dialog):

```bash
# Skill with custom extensions - warns and requires --force
$ invar skill remove security
Warning: Skill 'security' has custom extensions content that will be lost.
Use --force to confirm removal, or backup extensions first.

$ invar skill remove security --force
Removing skill: security
Skill 'security' removed successfully

# Skill without custom extensions - simple confirmation dialog
$ invar skill remove acceptance
Remove skill 'acceptance'? [y/N]: y
Removing skill: acceptance
Skill 'acceptance' removed successfully
```

### 5. `invar uninstall` preserves extensions

Default behavior: only remove core skills, preserve extension skills.

```bash
$ invar uninstall --dry-run
Will DELETE:
  .claude/skills/develop/    (core skill)
  .claude/skills/review/     (core skill)
  ...

Will PRESERVE (extension skills):
  .claude/skills/security/   (extension skill)

Use --remove-extensions to also remove extension skills
```

Use `--remove-extensions` to also delete extension skills.

## Implementation

### Changes to `skill_manager.py`

1. Import `parse_invar_regions`, `reconstruct_file` from `core/template_parser`
2. Add `_merge_md_file()` helper for region-preserving updates
3. Modify `add_skill()`:
   - If skill exists → merge update
   - If skill doesn't exist → fresh install
4. For `.md` files: use region merge
5. For other files (`.yaml`, directories): overwrite
6. Add `_has_user_extensions()` to detect custom content
7. Modify `remove_skill()` to warn about custom content

### Changes to `skill.py` (CLI)

1. Modify `add` command to handle existing skills
2. Deprecate `update` command (alias to `add`)
3. Add `--force` option to `remove` command

### Changes to `uninstall.py`

1. Add `CORE_SKILLS` set to distinguish core vs extension skills
2. Add `--remove-extensions` option
3. Default: preserve extension skills in `.claude/skills/`
4. Show preserved extensions in preview with hint

## User Experience

```bash
# First install
$ invar skill add security
Adding skill: security
  Copied: SKILL.md
  Copied: patterns/
Skill 'security' installed successfully

# Update (same command)
$ invar skill add security
Updating skill: security
  Merged: SKILL.md (extensions preserved)
  Updated: patterns/
Skill 'security' updated successfully

# Deprecated command still works
$ invar skill update security
Note: 'update' is deprecated, use 'add' instead
Updating skill: security
...
```

## Success Criteria

- [x] `skill add` works on non-installed skill (install)
- [x] `skill add` works on installed skill (merge update)
- [x] `<!--invar:extensions-->` region preserved on update
- [x] `skill update` shows deprecation notice
- [x] `skill remove` warns if custom extensions exist
- [x] `skill remove --force` bypasses warning
- [x] `invar uninstall` preserves extension skills by default
- [x] `invar uninstall --remove-extensions` removes all skills
- [x] Consistent with `init` behavior
