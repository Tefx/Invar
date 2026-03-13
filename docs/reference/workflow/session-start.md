# Session Start Guidance (DX-91)

> Status: **active DX-91 guidance** with explicit archive classification for pre-DX-91 ceremony.

## What Is Current

- The only mandatory workflow rule is contracts-first in Core code (`@pre`/`@post` + doctest before implementation).
- Verification is performed with `invar guard` (or MCP `invar_guard`) at appropriate checkpoints.
- Session formatting conventions such as "Check-In" / "Final" are team-level communication preferences, not runtime command requirements.

## Runtime-Aligned Surface

Use runtime help output as the authority for active commands:

- `invar guard`
- `invar init`
- `invar dev sync`
- `invar doc ...`
- `invar map`, `invar sig`, `invar refs`, `invar rules`, `invar version`, `invar mcp`

## Important DX-91 Clarifications

- Fresh `invar init` does not generate `.invar/context.md`.
- `invar dev sync` updates managed `CLAUDE.md` + `INVAR.md`; it does not manage `.invar/context.md`.
- `invar update` is a historical command reference, not part of the active DX-91 command surface.

## Historical/Archive References

The following remain for historical context only:

- USBV ceremony document: `docs/reference/workflow/usbv.md`
- Older context-file-centric workflow records in completed proposals (for example DX-54/LX-07)

If these historical pages conflict with runtime help output, runtime help output wins.
