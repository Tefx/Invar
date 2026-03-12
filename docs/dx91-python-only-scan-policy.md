# DX-91 Python-Only Broad-Scan Policy

This policy defines deterministic classification for regex-based residue scans.

## Classification Rules

1. **Active blocker**
   - Match appears in active runtime/document surfaces used as current behavior contract.
   - Scope: `README.md`, `CLAUDE.md`, `pyproject.toml`, active `.claude/**`, active `.invar/**`, and non-compatibility code under `src/invar/`.
   - Action: remove or rewrite the match.

2. **Classification-only non-blocking residue**
   - Match appears in canonical-protected, historical/archive, or compatibility/template-reference surfaces.
   - Scope:
     - canonical-protected: `INVAR.md`
     - historical/archive: `.invar/archive/**`, `docs/proposals/**`, `docs/test-reports/**`, historical artifact bundles
     - compatibility/template-reference:
       - `.invar/examples/**`
       - `.claude/skills/invar-reflect/**`
       - `src/invar/templates/**`
       - `src/invar/shell/commands/init.py`
       - `src/invar/shell/commands/guard.py`
       - `src/invar/shell/claude_hooks.py`
       - `src/invar/shell/pi_hooks.py`
       - `src/invar/shell/skill_manager.py`
       - `src/invar/shell/templates.py`
       - `src/invar/shell/config.py`
       - `src/invar/shell/pattern_integration.py`
       - `src/invar/mcp/server.py`
       - `src/invar/core/sync_helpers.py`
       - `src/invar/core/property_runner.py`
       - `src/invar/core/review_trigger.py`
       - `src/invar/core/rule_meta.py`
       - `src/invar/core/inspect.py`
       - `src/invar/core/patterns/**`
   - Action: keep, but classify explicitly in verification evidence.

3. **Plan/orchestrator metadata**
   - `plan.yaml` and `.git/vectl/*` may contain historical command text and step IDs.
   - Action: do not edit from isolated worktree tasks unless explicitly requested.

## Deterministic Evaluation Steps

1. Run the required broad scans exactly as specified.
2. For each remaining match, map its path to one of the three classes above.
3. If a path does not match an allowlist class, treat it as an active blocker.
