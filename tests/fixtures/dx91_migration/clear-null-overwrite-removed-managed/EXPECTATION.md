# Fixture: clear-null-overwrite-removed-managed

Protects: explicit clear/null overwrite semantics for removed managed content.

Expected:
- Legacy managed fragments are fully removed from managed output.
- Only regenerated v2 managed region remains.
- User content outside managed region stays unchanged.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 3.3
- `docs/proposals/DX-91-migration-semantics.md` section 4.4
