# Agent Information Hierarchy (DX-91)

> This page documents the **active** DX-91 hierarchy. Pre-DX-91 skill/context hierarchy is archival.

## Active Hierarchy

1. `CLAUDE.md` (project-level operating guidance + managed invar block)
2. `INVAR.md` (protocol-level rules and architecture constraints)
3. `README.md` and `docs/reference/**` (supporting explanations and command reference)

## Command-Surface Source of Truth

When docs and examples disagree, resolve against runtime help output:

```bash
uv run invar --help
uv run invar init --help
uv run invar dev --help
```

Active DX-91 CLI surface is:

- `guard`, `version`, `map`, `sig`, `refs`, `rules`, `init`, `mcp`, `doc`, `dev sync`

## Generated-Surface Notes

- Fresh `invar init` writes `CLAUDE.md`, `INVAR.md`, and `.pre-commit-config.yaml`.
- Fresh `invar init` does not generate `.invar/context.md`, `.mcp.json`, `.claude/commands/`, or skills/hooks directories.
- `invar dev sync` manages `CLAUDE.md` + `INVAR.md` output only.

## Archive Classification

The following concepts are retained only as historical references and are not part of the active DX-91 surface:

- Check-In/Final ceremony as a required protocol
- USBV four-phase workflow as mandatory process
- Skill/hook/command trees such as `.claude/commands/`, `invar skill`, and `/invar-onboard`
- Context-file-first hierarchy centered on `.invar/context.md`

Historical material remains in proposal and archive docs for traceability.
