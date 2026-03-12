# Fixture: interrupted-partial-migration-recovery

Protects: partial-write/interrupted migration behavior.

Expected:
- Mixed partial state is treated as recoverable migration input.
- Final output is consistent v2 layout with one managed block.
- Recovery path does not duplicate managed sections or backup entries.

Spec links:
- `docs/proposals/DX-91-migration-semantics.md` section 4.3
- `docs/proposals/DX-91-migration-semantics.md` section 4.5
