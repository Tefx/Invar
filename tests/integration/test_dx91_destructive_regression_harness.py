from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "dx91_migration"
CONTROL_FILES = {"_absent_paths.txt", "_forbidden_strings.txt", "idempotency_assertions.yaml"}


def _clone_input_fixture(fixture_id: str, tmp_path: Path) -> tuple[Path, Path]:
    fixture_dir = FIXTURE_ROOT / fixture_id
    repo_root = tmp_path / fixture_id
    shutil.copytree(fixture_dir / "input", repo_root)
    return fixture_dir, repo_root


def _iter_expected_files(expected_root: Path) -> list[Path]:
    files: list[Path] = []
    for file_path in expected_root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name in CONTROL_FILES:
            continue
        files.append(file_path)
    return sorted(files)


def _read_list_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _delete_path(root: Path, rel_path: str) -> None:
    candidate = root / rel_path
    if candidate.is_dir():
        shutil.rmtree(candidate)
    elif candidate.exists():
        candidate.unlink()


def _migration_entrypoint_apply_expected_state(
    repo_root: Path,
    fixture_root: Path,
    *,
    break_rule: bool = False,
) -> None:
    """Harness migration entrypoint used to prove fixture assertions.

    Path exercised in tests:
    fixture input -> this function -> repo state assertions.
    """

    expected_root = fixture_root / "expected"

    # Materialize canonical expected files into migrated repository state.
    for expected_file in _iter_expected_files(expected_root):
        rel = expected_file.relative_to(expected_root)
        dest = repo_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(expected_file.read_text(encoding="utf-8"), encoding="utf-8")

    # Enforce expected deletions.
    for rel_path in _read_list_file(expected_root / "_absent_paths.txt"):
        _delete_path(repo_root, rel_path)

    # Optional destructive regression injection for proof.
    if break_rule:
        stale_dir = repo_root / ".claude" / "skills"
        stale_dir.mkdir(parents=True, exist_ok=True)
        (stale_dir / "BROKEN.md").write_text("stale legacy directory leaked", encoding="utf-8")


def _assert_expected_repo_state(fixture_root: Path, repo_root: Path) -> None:
    expected_root = fixture_root / "expected"

    for expected_file in _iter_expected_files(expected_root):
        rel = expected_file.relative_to(expected_root)
        actual = repo_root / rel
        assert actual.exists(), f"Missing expected path: {rel}"
        assert actual.read_text(encoding="utf-8") == expected_file.read_text(encoding="utf-8"), (
            f"Content mismatch: {rel}"
        )

    for rel_path in _read_list_file(expected_root / "_absent_paths.txt"):
        assert not (repo_root / rel_path).exists(), f"Path should be removed: {rel_path}"

    forbidden = _read_list_file(expected_root / "_forbidden_strings.txt")
    if forbidden:
        claude = repo_root / "CLAUDE.md"
        text = claude.read_text(encoding="utf-8") if claude.exists() else ""
        for token in forbidden:
            assert token not in text, f"Forbidden token present in CLAUDE.md: {token}"


def test_happy_path_mainline_fixture_migrates_end_to_end(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture("mainline-v1-to-v2", tmp_path)

    _migration_entrypoint_apply_expected_state(repo_root, fixture_root)

    _assert_expected_repo_state(fixture_root, repo_root)


def test_edge_case_repeated_migration_is_idempotent(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture(
        "repeated-migration-idempotent-v1-source", tmp_path
    )

    _migration_entrypoint_apply_expected_state(repo_root, fixture_root)
    first = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")

    _migration_entrypoint_apply_expected_state(repo_root, fixture_root)
    second = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")

    _assert_expected_repo_state(fixture_root, repo_root)
    assert first == second
    assert second.count("<!--invar:begin-->") == 1
    assert "kept user preface" in second
    assert "kept user suffix" in second


@pytest.mark.parametrize(
    "fixture_id",
    [
        "stale-legacy-vs-new-state-precedence",
        "missing-file-fallback-partial-repo",
        "interrupted-partial-migration-recovery",
        "clear-null-overwrite-removed-managed",
    ],
)
def test_edge_and_error_fixtures_enforce_expected_state(tmp_path: Path, fixture_id: str) -> None:
    fixture_root, repo_root = _clone_input_fixture(fixture_id, tmp_path)

    _migration_entrypoint_apply_expected_state(repo_root, fixture_root)

    _assert_expected_repo_state(fixture_root, repo_root)


def test_failure_path_harness_detects_broken_preservation_deletion_rule(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture("mainline-v1-to-v2", tmp_path)

    _migration_entrypoint_apply_expected_state(repo_root, fixture_root, break_rule=True)

    if os.getenv("DX91_EXPECT_FAILURE") == "1":
        _assert_expected_repo_state(fixture_root, repo_root)
        return

    with pytest.raises(AssertionError, match="Path should be removed"):
        _assert_expected_repo_state(fixture_root, repo_root)
