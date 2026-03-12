# Fixture: missing-file-fallback-partial-repo

Protects: missing-file fallback behavior for partially initialized repos.

Expected:
- Migration succeeds when optional files are absent.
- Only existing optional files are backed up.
- Required managed outputs are still produced.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.4
