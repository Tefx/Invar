# Fixture: stale-legacy-vs-new-state-precedence

Protects: stale-definition vs new-state precedence when both legacy and new files are present.

Expected:
- Any v1 detection signal forces migration behavior.
- Stale v2 managed content is replaced by regenerated managed content.
- User-owned text outside managed markers is preserved byte-for-byte.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.1
- `docs/proposals/DX-91-migration-semantics.md` section 4.1
