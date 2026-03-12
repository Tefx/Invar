"""DX-91 regression coverage for retired TypeScript surfaces."""

from __future__ import annotations

from pathlib import Path


def test_dx91_typescript_compiler_module_is_retired() -> None:
    """TypeScript compiler bridge is not part of DX-91 runtime."""
    project_root = Path(__file__).resolve().parents[2]
    assert not (project_root / "src" / "invar" / "shell" / "ts_compiler.py").exists()


def test_dx91_pi_tools_template_is_retired() -> None:
    """Pi TypeScript tool template was removed in Python-only mode."""
    project_root = Path(__file__).resolve().parents[2]
    assert not (
        project_root / "src" / "invar" / "templates" / "pi-tools" / "invar" / "index.ts"
    ).exists()


def test_dx91_typescript_workspace_is_retired() -> None:
    """Standalone TypeScript workspace is not shipped in DX-91 path."""
    project_root = Path(__file__).resolve().parents[2]
    assert not (project_root / "typescript").exists()
