# Fixture: repeated-migration-idempotent-v1-source

Protects: repeated migration from v1 fixtures yields stable v2 layout without duplicate sections.

Expected:
- First migration reaches v2 layout shown in `expected/`.
- Second migration from first output is byte-identical for managed region.
- User-owned content outside managed region remains byte-stable.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.5
- `docs/proposals/DX-91-migration-semantics.md` section 4.4
