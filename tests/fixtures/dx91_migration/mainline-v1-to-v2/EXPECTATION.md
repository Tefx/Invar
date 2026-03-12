# Fixture: mainline-v1-to-v2

Protects: main path v1 -> v2 migration.

Expected:
- v1 multi-region CLAUDE markers are replaced with one v2 managed block.
- User content outside managed block remains unchanged.
- `.invar/context.md` and `.invar/project-additions.md` are backed up.
- Legacy agent-era directories are deleted.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.3
- `docs/proposals/DX-91-migration-semantics.md` section 4.4
