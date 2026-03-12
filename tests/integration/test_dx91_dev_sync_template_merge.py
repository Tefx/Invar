from __future__ import annotations

from pathlib import Path

from returns.result import Failure, Success

from invar.core.sync_helpers import SyncConfig
from invar.shell.commands import template_sync
from invar.shell.commands.template_sync import sync_templates


def _v2_template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "invar" / "templates"


def test_main_path_preserves_user_content_and_rewrites_managed(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "preface\n<!--invar:begin-->\nOLD_MANAGED\n<!--invar:end-->\nsuffix\n",
        encoding="utf-8",
    )

    result = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )

    assert isinstance(result, Success)
    content = target.read_text(encoding="utf-8")
    assert "OLD_MANAGED" not in content
    assert content.count("<!--invar:begin-->") == 1
    assert "preface" in content
    assert "suffix" in content
    assert (tmp_path / "INVAR.md").exists()


def test_relative_and_absolute_template_root_produce_identical_output(tmp_path: Path) -> None:
    absolute_repo = tmp_path / "abs"
    relative_repo = tmp_path / "rel"
    absolute_repo.mkdir()
    relative_repo.mkdir()

    absolute_root = _v2_template_root()
    relative_templates = relative_repo / "templates"
    relative_templates.mkdir(parents=True)
    (relative_templates / "config").mkdir(parents=True)
    (relative_templates / "protocol").mkdir(parents=True)
    (relative_templates / "config" / "CLAUDE.md.v2.jinja").write_text(
        (absolute_root / "config" / "CLAUDE.md.v2.jinja").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (relative_templates / "protocol" / "INVAR.md.v2.jinja").write_text(
        (absolute_root / "protocol" / "INVAR.md.v2.jinja").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    relative_template_root = "templates"

    abs_result = sync_templates(
        absolute_repo,
        SyncConfig(template_root=str(absolute_root), syntax="mcp"),
    )
    rel_result = sync_templates(
        relative_repo,
        SyncConfig(template_root=relative_template_root, syntax="mcp"),
    )

    assert isinstance(abs_result, Success)
    assert isinstance(rel_result, Success)
    assert (absolute_repo / "CLAUDE.md").read_text(encoding="utf-8") == (
        relative_repo / "CLAUDE.md"
    ).read_text(encoding="utf-8")
    assert str(absolute_root) not in (absolute_repo / "CLAUDE.md").read_text(encoding="utf-8")


def test_missing_target_files_are_created_for_older_repo(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("legacy repo", encoding="utf-8")

    result = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )

    assert isinstance(result, Success)
    report = result.unwrap()
    assert "CLAUDE.md" in report.created
    assert "INVAR.md" in report.created


def test_create_only_context_file_is_created_from_templates(tmp_path: Path) -> None:
    result = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )

    assert isinstance(result, Success)
    report = result.unwrap()
    context_file = tmp_path / ".invar" / "context.md"
    assert context_file.exists()
    assert ".invar/context.md" in report.created
    assert "## Current State" in context_file.read_text(encoding="utf-8")


def test_existing_context_file_is_preserved_as_create_only(tmp_path: Path) -> None:
    context_file = tmp_path / ".invar" / "context.md"
    context_file.parent.mkdir(parents=True, exist_ok=True)
    context_file.write_text("legacy context stays", encoding="utf-8")

    result = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )

    assert isinstance(result, Success)
    report = result.unwrap()
    assert context_file.read_text(encoding="utf-8") == "legacy context stays"
    assert ".invar/context.md" in report.skipped


def test_clear_overwrite_semantics_remove_stale_managed_content(tmp_path: Path) -> None:
    custom_templates = tmp_path / "templates"
    (custom_templates / "config").mkdir(parents=True)
    (custom_templates / "protocol").mkdir(parents=True)

    (custom_templates / "config" / "CLAUDE.md.v2.jinja").write_text(
        "<!--invar:begin-->\n<!--invar:end-->\n",
        encoding="utf-8",
    )
    (custom_templates / "protocol" / "INVAR.md.v2.jinja").write_text(
        "# INVAR\n",
        encoding="utf-8",
    )

    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "before\n<!--invar:begin-->\nSHOULD_BE_REMOVED\n<!--invar:end-->\nafter\n",
        encoding="utf-8",
    )

    result = sync_templates(
        tmp_path,
        SyncConfig(template_root=str(custom_templates), syntax="mcp"),
    )

    assert isinstance(result, Success)
    content = target.read_text(encoding="utf-8")
    assert "SHOULD_BE_REMOVED" not in content
    assert content.count("<!--invar:begin-->") == 1


def test_stale_legacy_signal_takes_precedence_over_existing_v2_block(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "prefix\n<!--invar:begin-->\nSTALE_V2\n<!--invar:end-->\n"
        "<!--invar:critical-->legacy trigger<!--/invar:critical-->\nsuffix\n",
        encoding="utf-8",
    )

    result = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )

    assert isinstance(result, Success)
    content = target.read_text(encoding="utf-8")
    assert "STALE_V2" not in content
    assert "legacy trigger" not in content
    assert content.count("<!--invar:begin-->") == 1
    assert "prefix" in content
    assert "suffix" in content


def test_partial_write_returns_failure_and_second_run_recovers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    original_atomic_write = template_sync._atomic_write
    state = {"calls": 0}

    def fail_once(path: Path, content: str) -> None:
        state["calls"] += 1
        if state["calls"] == 2:
            raise OSError("simulated interrupted write")
        original_atomic_write(path, content)

    monkeypatch.setattr(template_sync, "_atomic_write", fail_once)

    failed = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )
    assert isinstance(failed, Failure)
    assert "interrupted" in failed.failure().lower()

    monkeypatch.setattr(template_sync, "_atomic_write", original_atomic_write)
    recovered = sync_templates(
        tmp_path,
        SyncConfig(syntax="mcp", template_root=str(_v2_template_root())),
    )
    assert isinstance(recovered, Success)
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count("<!--invar:begin-->") == 1
    assert (tmp_path / "INVAR.md").exists()


def test_sync_target_accepts_absolute_path(tmp_path: Path) -> None:
    absolute_target = tmp_path / "docs" / "agent" / "RULES.md"

    result = sync_templates(
        tmp_path,
        SyncConfig(
            syntax="mcp",
            template_root=str(_v2_template_root()),
            target_file=str(absolute_target),
        ),
    )

    assert isinstance(result, Success)
    assert absolute_target.exists()
    assert (tmp_path / "INVAR.md").exists()
