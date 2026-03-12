from __future__ import annotations

"""DX-91 destructive uninstall+sync regression harness.

This module validates stale-asset cleanup and state convergence for the
uninstall+template-sync path. Migration-preservation semantics (backup creation
and byte-identical retained originals) are proven by public init migration tests
in test_dx91_init_entrypoints.py.
"""

import os
import shutil
from pathlib import Path

import pytest
import yaml
from returns.result import Failure

from invar.core.sync_helpers import SyncConfig
from invar.shell.commands.template_sync import sync_templates
from invar.shell.commands.uninstall import collect_removal_targets, execute_removal

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "dx91_migration"
CONTROL_FILES = {
    "_absent_paths.txt",
    "_forbidden_strings.txt",
    "idempotency_assertions.yaml",
    "_allowlist_paths.txt",
}
ENTRYPOINT_SKIP_PATTERNS = [
    ".claude/skills/*",
    ".claude/commands/*",
    ".pre-commit-config.yaml",
    ".invar/examples/*",
]


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


def _uninstall_then_sync_harness_apply_expected_state(
    repo_root: Path,
    fixture_root: Path,
    *,
    break_rule: bool = False,
) -> None:
    """Run real uninstall + sync APIs (not init migration proof)."""

    # v1 cleanup phase (public uninstall command helpers)
    targets = collect_removal_targets(repo_root, remove_extensions=True)
    execute_removal(repo_root, targets)

    # v2 materialization phase (public template sync engine)
    result = sync_templates(
        repo_root,
        SyncConfig(
            syntax="mcp",
            language="python",
            inject_project_additions=(repo_root / ".invar" / "project-additions.md").exists(),
            force=False,
            check=False,
            reset=False,
            skip_patterns=ENTRYPOINT_SKIP_PATTERNS,
        ),
    )
    if isinstance(result, Failure):
        pytest.fail(f"Migration entrypoint failed: {result.failure()}")
    if result.unwrap().errors:
        pytest.fail(f"Migration entrypoint errors: {result.unwrap().errors}")

    # Optional destructive regression injection for proof.
    if break_rule:
        leaked = repo_root / "_unexpected_leak.txt"
        leaked.write_text("unexpected leaked file", encoding="utf-8")


def _iter_repo_files(repo_root: Path) -> set[str]:
    return {str(path.relative_to(repo_root)) for path in repo_root.rglob("*") if path.is_file()}


def _read_idempotency_assertions(expected_root: Path) -> dict[str, int | bool]:
    path = expected_root / "idempotency_assertions.yaml"
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    assertions: dict[str, int | bool] = {}
    run_count = data.get("run_count")
    if isinstance(run_count, int):
        assertions["run_count"] = run_count

    items = data.get("assertions", [])
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            for key, value in item.items():
                if isinstance(value, (int, bool)):
                    assertions[str(key)] = value

    return assertions


def _assert_expected_repo_state(fixture_root: Path, repo_root: Path) -> None:
    expected_root = fixture_root / "expected"
    expected_files = {
        str(expected_file.relative_to(expected_root))
        for expected_file in _iter_expected_files(expected_root)
    }
    allowlisted = set(_read_list_file(expected_root / "_allowlist_paths.txt"))
    actual_files = _iter_repo_files(repo_root)

    missing = sorted(expected_files - actual_files)
    assert not missing, f"Missing expected paths: {missing}"

    unexpected = sorted(actual_files - expected_files - allowlisted)
    assert not unexpected, f"Unexpected repo files: {unexpected}"

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


def test_happy_path_mainline_fixture_uninstall_sync_converges_end_to_end(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture("mainline-v1-to-v2", tmp_path)

    _uninstall_then_sync_harness_apply_expected_state(repo_root, fixture_root)

    _assert_expected_repo_state(fixture_root, repo_root)


def test_edge_case_repeated_uninstall_sync_runs_are_idempotent(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture(
        "repeated-migration-idempotent-v1-source", tmp_path
    )
    assertions = _read_idempotency_assertions(fixture_root / "expected")
    run_count = int(assertions.get("run_count", 2))
    assert run_count >= 2

    _uninstall_then_sync_harness_apply_expected_state(repo_root, fixture_root)
    first = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")

    second = first
    for _ in range(run_count - 1):
        _uninstall_then_sync_harness_apply_expected_state(repo_root, fixture_root)
        second = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")

    _assert_expected_repo_state(fixture_root, repo_root)
    if assertions.get("managed_block_byte_identical_on_second_run") is True:
        assert first == second
    if assertions.get("managed_block_count") is not None:
        managed_count = second.count("<!--invar:managed") + second.count("<!--invar:begin-->")
        assert managed_count == int(assertions["managed_block_count"])
    if assertions.get("user_content_outside_markers_byte_identical") is True:
        assert "kept user preface" in second
        assert "kept user suffix" in second


@pytest.mark.parametrize(
    "fixture_id",
    [
        "stale-legacy-vs-new-state-precedence",
        "missing-file-fallback-partial-repo",
        "interrupted-partial-migration-recovery",
        "clear-null-overwrite-removed-managed",
        "relative-vs-absolute-template-path",
    ],
)
def test_edge_and_error_fixtures_enforce_expected_state_after_uninstall_sync(
    tmp_path: Path, fixture_id: str
) -> None:
    fixture_root, repo_root = _clone_input_fixture(fixture_id, tmp_path)

    _uninstall_then_sync_harness_apply_expected_state(repo_root, fixture_root)

    _assert_expected_repo_state(fixture_root, repo_root)


def test_failure_path_harness_detects_broken_preservation_deletion_rule(tmp_path: Path) -> None:
    fixture_root, repo_root = _clone_input_fixture("mainline-v1-to-v2", tmp_path)

    _uninstall_then_sync_harness_apply_expected_state(repo_root, fixture_root, break_rule=True)

    if os.getenv("DX91_EXPECT_FAILURE") == "1":
        with pytest.raises(AssertionError, match="Unexpected repo files"):
            _assert_expected_repo_state(fixture_root, repo_root)
        pytest.fail("DX91_EXPECT_FAILURE=1 forced the expected Unexpected repo files assertion")
        return

    with pytest.raises(AssertionError, match="Unexpected repo files"):
        _assert_expected_repo_state(fixture_root, repo_root)
