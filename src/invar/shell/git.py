"""
Git operations for Guard (Phase 8).

Shell module: handles git I/O for changed file detection.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from returns.result import Failure, Result, Success


def _run_git(args: list[str], cwd: Path) -> Result[str, str]:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            return Failure(result.stderr.strip() or f"git {args[0]} failed")
        return Success(result.stdout)
    except FileNotFoundError:
        return Failure("git command not found")
    except Exception as e:
        return Failure(f"Git error: {e}")


def matches_path_prefix(rel: str, prefixes: list[str]) -> bool:
    """Check if a relative path matches any of the given prefixes."""
    normalized = os.path.normpath(rel)
    for prefix in prefixes:
        prefix_norm = os.path.normpath(prefix)
        if normalized == prefix_norm or normalized.startswith(prefix_norm + os.sep):
            return True
    return False


def _is_core_file(file_path: Path, repo_root: Path, core_paths: list[str]) -> bool:
    """Check if a file is under a Core path prefix."""
    try:
        rel = str(file_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel = str(file_path)
    return matches_path_prefix(rel, core_paths)


def _parse_hunk_header(header: str) -> tuple[int, int] | None:
    """Parse a git hunk header like '@@ -12,3 +14,4 @@' into (start, end).

    Returns 1-indexed line range (start, end) or None if unparseable.
    Zero-context hunks have ',0' omitted before the comma.
    """
    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@", header.strip())
    if not m:
        return None
    start = int(m.group(1))
    # Zero-context means deleted/added count was 0
    count = int(m.group(2)) if m.group(2) else 1
    end = start + count - 1
    return (start, end)


def _extract_hunks_from_diff(diff_output: str) -> list[tuple[int, int]]:
    """Extract line ranges from 'git diff' output with hunks.

    Returns list of (start, end) 1-indexed line ranges.

    .. warning::
        This extracts ALL hunks regardless of file boundaries.
        For per-file hunk attribution, use ``_extract_hunks_per_file``.
    """
    hunks: list[tuple[int, int]] = []
    for line in diff_output.splitlines():
        if line.startswith("@@"):
            parsed = _parse_hunk_header(line)
            if parsed:
                hunks.append(parsed)
    return hunks


def _extract_hunks_per_file(
    diff_output: str,
) -> dict[str, list[tuple[int, int]]]:
    """Extract line ranges from diff output, grouped by file path.

    Handles multi-file diffs correctly: each file's hunks are attributed
    to that file only.

    Args:
        diff_output: Full output from ``git diff`` or ``git diff --cached``.

    Returns:
        Dict mapping file path (relative, as in the diff) to list of
        (start, end) 1-indexed line ranges.

    Examples:
        >>> diff = "diff --git a/foo.py b/foo.py\\n--- a/foo.py\\n+++ b/foo.py\\n@@ -1,3 +1,3 @@\\nline\\n"
        >>> hunks = _extract_hunks_per_file(diff)
        >>> "foo.py" in hunks
        True
        >>> hunks["foo.py"]
        [(1, 3)]
        >>> # Multi-file diff: hunks are attributed to correct file
        >>> multi = (
        ...     "diff --git a/foo.py b/foo.py\\n"
        ...     "--- a/foo.py\\n+++ b/foo.py\\n"
        ...     "@@ -1,3 +1,3 @@\\nline\\n"
        ...     "diff --git a/bar.py b/bar.py\\n"
        ...     "--- a/bar.py\\n+++ b/bar.py\\n"
        ...     "@@ -10,2 +10,2 @@\\nline\\n"
        ... )
        >>> hunks_multi = _extract_hunks_per_file(multi)
        >>> len(hunks_multi)
        2
        >>> hunks_multi["foo.py"]
        [(1, 3)]
        >>> hunks_multi["bar.py"]
        [(10, 11)]
    """
    result: dict[str, list[tuple[int, int]]] = {}
    current_file: str | None = None

    for line in diff_output.splitlines():
        # File header: "--- a/path" starts a new file section
        if line.startswith("--- a/"):
            # Extract path from "--- a/path"
            current_file = line[6:]  # Remove "--- a/"
        elif line.startswith("@@"):
            parsed = _parse_hunk_header(line)
            if parsed and current_file is not None:
                if current_file not in result:
                    result[current_file] = []
                result[current_file].append(parsed)

    return result


def get_changed_lines(
    project_root: Path,
    core_paths: list[str] | None = None,
) -> Result[dict[Path, list[tuple[int, int]] | None], str]:
    """
    Get changed-line spans for Core Python files across staged/unstaged/untracked.

    - Staged and unstaged: parses hunks to extract line ranges.
    - Untracked Core Python files: treated as whole-file changed (None = whole file).
    - Deleted and non-Core files: excluded.
    - Zero-context hunks: handled correctly (off-by-one prevention).

    Args:
        project_root: Project root directory.
        core_paths: List of Core path prefixes. Defaults to ["src/core", "core"].

    Returns:
        Dict mapping file Path -> list of (start, end) 1-indexed line spans.
        None span means whole file changed (used for untracked files).

    Examples:
        >>> from pathlib import Path
        >>> result = get_changed_lines(Path("."))
        >>> isinstance(result, (Success, Failure))
        True
    """
    if core_paths is None:
        core_paths = ["src/core", "core"]

    check = _run_git(["rev-parse", "--git-dir"], project_root)
    if isinstance(check, Failure):
        return Failure(f"Not a git repository: {project_root}")

    repo_root_result = _run_git(["rev-parse", "--show-toplevel"], project_root)
    if isinstance(repo_root_result, Failure):
        return Failure(repo_root_result.failure())

    repo_root = Path(repo_root_result.unwrap().strip())

    result: dict[Path, list[tuple[int, int]] | None] = {}

    # --- Staged (cached) diff ---
    cached_diff = _run_git(["diff", "--cached"], project_root)
    if isinstance(cached_diff, Success):
        file_hunks = _extract_hunks_per_file(cached_diff.unwrap())
        for file_path, hunks in file_hunks.items():
            if not hunks:
                continue
            fpath = repo_root / file_path
            if (
                fpath.exists()
                and file_path.endswith(".py")
                and _is_core_file(fpath, repo_root, core_paths)
            ):
                result[fpath] = hunks

    # --- Unstaged diff ---
    unstaged_diff = _run_git(["diff"], project_root)
    if isinstance(unstaged_diff, Success):
        file_hunks = _extract_hunks_per_file(unstaged_diff.unwrap())
        for file_path, hunks in file_hunks.items():
            if not hunks:
                continue
            fpath = repo_root / file_path
            if (
                fpath.exists()
                and file_path.endswith(".py")
                and _is_core_file(fpath, repo_root, core_paths)
            ):
                # Merge with staged hunks if present
                if fpath in result and result[fpath] is not None:
                    merged = sorted(set(result[fpath] + hunks))  # type: ignore[operator]
                    result[fpath] = merged
                else:
                    result[fpath] = hunks

    # --- Untracked files ---
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], project_root)
    if isinstance(untracked, Success):
        for line in untracked.unwrap().strip().splitlines():
            if not line:
                continue
            fpath = repo_root / line
            # Untracked: whole file changed, exclude non-Core
            if (
                fpath.exists()
                and line.endswith(".py")
                and _is_core_file(fpath, repo_root, core_paths)
            ):
                result[fpath] = None  # None = whole file

    return Success(result)


# @shell_orchestration: Helper for git output parsing, tightly coupled to Shell
def _parse_py_files(output: str, project_root: Path) -> set[Path]:
    """Parse git output and return Python file paths."""
    files: set[Path] = set()
    for line in output.strip().split("\n"):
        if line and line.endswith(".py"):
            files.add(project_root / line)
    return files


# @shell_complexity: Git operations require multiple subprocess calls with error handling
def get_changed_files(project_root: Path) -> Result[set[Path], str]:
    """
    Get Python files modified according to git (staged, unstaged, untracked).

    Examples:
        >>> from pathlib import Path
        >>> result = get_changed_files(Path("."))
        >>> isinstance(result, (Success, Failure))
        True
    """
    check = _run_git(["rev-parse", "--git-dir"], project_root)
    if isinstance(check, Failure):
        return Failure(f"Not a git repository: {project_root}")

    repo_root_result = _run_git(["rev-parse", "--show-toplevel"], project_root)
    if isinstance(repo_root_result, Failure):
        return Failure(repo_root_result.failure())

    repo_root = Path(repo_root_result.unwrap().strip())

    changed: set[Path] = set()

    staged = _run_git(["diff", "--cached", "--name-only"], project_root)
    if isinstance(staged, Success):
        changed.update(_parse_py_files(staged.unwrap(), repo_root))

    unstaged = _run_git(["diff", "--name-only"], project_root)
    if isinstance(unstaged, Success):
        changed.update(_parse_py_files(unstaged.unwrap(), repo_root))

    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], project_root)
    if isinstance(untracked, Success):
        changed.update(_parse_py_files(untracked.unwrap(), repo_root))

    return Success(changed)


def is_git_repo(path: Path) -> bool:
    """
    Check if a path is inside a git repository.

    Examples:
        >>> from pathlib import Path
        >>> isinstance(is_git_repo(Path(".")), bool)
        True
    """
    result = _run_git(["rev-parse", "--git-dir"], path)
    return isinstance(result, Success)
