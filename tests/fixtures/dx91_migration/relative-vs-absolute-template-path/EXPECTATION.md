# Fixture: relative-vs-absolute-template-path

Protects: relative vs absolute template path behavior.

Expected:
- Managed output bytes are identical regardless of whether template root metadata is relative or absolute.
- No absolute host path leaks into generated files.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.3
