from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import typer

from invar.shell.commands import init as init_cmd

if TYPE_CHECKING:
    from pathlib import Path


def _run_init(tmp_path: Path, *, file: str = "CLAUDE.md", preview: bool = False) -> None:
    init_cmd.init(path=tmp_path, file=file, preview=preview)


def test_main_path_writes_minimal_dx91_file_set(tmp_path: Path) -> None:
    _run_init(tmp_path)

    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "INVAR.md").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()

    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".claude" / "hooks").exists()
    assert not (tmp_path / ".invar" / "examples").exists()
    assert not (tmp_path / ".mcp.json").exists()

    claude_text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "<!--invar:begin-->" in claude_text
    assert "<!--invar:end-->" in claude_text


def test_target_file_supports_relative_and_absolute_paths(tmp_path: Path) -> None:
    _run_init(tmp_path, file="AGENTS.md")
    assert (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()

    absolute_target = tmp_path / "docs" / "agent" / "RULES.md"
    _run_init(tmp_path, file=str(absolute_target))
    assert absolute_target.exists()


def test_migration_handles_missing_optional_preserved_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text(
        "<!--invar:critical-->legacy<!--/invar:critical-->", encoding="utf-8"
    )
    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    _run_init(tmp_path)

    assert not (tmp_path / ".claude" / "skills").exists()
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "INVAR.md").exists()


def test_migration_explicitly_deletes_removed_generated_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for rel in [
        ".claude/skills/old",
        ".claude/hooks",
        ".pi/hooks",
        ".pi/tools",
        ".invar/examples/python",
    ]:
        p = tmp_path / rel
        p.mkdir(parents=True)
        (p / "sentinel.txt").write_text("legacy", encoding="utf-8")

    (tmp_path / "CLAUDE.md").write_text("legacy", encoding="utf-8")
    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    _run_init(tmp_path)

    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".claude" / "hooks").exists()
    assert not (tmp_path / ".pi" / "hooks").exists()
    assert not (tmp_path / ".pi" / "tools").exists()
    assert not (tmp_path / ".invar" / "examples").exists()


def test_stale_legacy_detection_takes_precedence_over_existing_v2_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text(
        "\n".join(
            [
                "preface",
                "<!--invar:begin-->",
                "stale-managed-content",
                "<!--invar:end-->",
                "suffix",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    _run_init(tmp_path)

    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "stale-managed-content" not in claude
    assert "preface" in claude
    assert "suffix" in claude
    assert claude.count("<!--invar:begin-->") == 1
    assert not (tmp_path / ".claude" / "skills").exists()


def test_interrupted_write_can_be_recovered_with_second_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text(
        "<!--invar:critical-->legacy<!--/invar:critical-->", encoding="utf-8"
    )
    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    original_atomic_write = init_cmd._atomic_write
    state = {"calls": 0}

    def fail_once(path: Path, content: str) -> None:
        state["calls"] += 1
        if state["calls"] == 2:
            raise OSError("simulated interrupted write")
        original_atomic_write(path, content)

    monkeypatch.setattr("invar.shell.commands.init._atomic_write", fail_once)
    with pytest.raises(typer.Exit):
        _run_init(tmp_path)

    monkeypatch.setattr("invar.shell.commands.init._atomic_write", original_atomic_write)
    _run_init(tmp_path)

    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count("<!--invar:begin-->") == 1
    assert (tmp_path / "INVAR.md").exists()


def test_repeated_init_on_migrated_repo_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / "CLAUDE.md").write_text(
        "user-prefix\n<!--invar:critical-->legacy<!--/invar:critical-->", encoding="utf-8"
    )
    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    _run_init(tmp_path)
    first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    _run_init(tmp_path)
    second = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    assert first == second
    assert second.count("<!--invar:begin-->") == 1
    assert "user-prefix" in second


def test_migration_backs_up_both_preserved_files_and_keeps_originals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".pi" / "hooks").mkdir(parents=True)
    (tmp_path / ".pi" / "tools").mkdir(parents=True)
    (tmp_path / ".invar" / "examples").mkdir(parents=True)

    (tmp_path / "CLAUDE.md").write_text(
        "legacy-prefix\n<!--invar:critical-->legacy<!--/invar:critical-->",
        encoding="utf-8",
    )
    context_path = tmp_path / ".invar" / "context.md"
    additions_path = tmp_path / ".invar" / "project-additions.md"
    context_path.write_bytes(b"ctx line 1\nctx line 2\n")
    additions_path.write_bytes(b"# additions\nkeep this exact text\n")

    original_context = context_path.read_bytes()
    original_additions = additions_path.read_bytes()

    monkeypatch.setattr("invar.shell.commands.init.typer.confirm", lambda *_args, **_kwargs: True)

    _run_init(tmp_path)

    context_backup = tmp_path / ".invar" / "backup" / "v1-context.md"
    additions_backup = tmp_path / ".invar" / "backup" / "v1-project-additions.md"
    assert context_backup.exists()
    assert additions_backup.exists()
    assert context_backup.read_bytes() == original_context
    assert additions_backup.read_bytes() == original_additions

    assert context_path.read_bytes() == original_context
    assert additions_path.read_bytes() == original_additions

    assert not (tmp_path / ".claude" / "skills").exists()
    assert not (tmp_path / ".claude" / "hooks").exists()
    assert not (tmp_path / ".pi" / "hooks").exists()
    assert not (tmp_path / ".pi" / "tools").exists()
    assert not (tmp_path / ".invar" / "examples").exists()

    first_claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    _run_init(tmp_path)
    second_claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert first_claude == second_claude
    assert second_claude.count("<!--invar:begin-->") == 1

    assert context_backup.read_bytes() == original_context
    assert additions_backup.read_bytes() == original_additions
