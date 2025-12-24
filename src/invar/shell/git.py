"""
Git operations for Guard (Phase 8).

Shell module: handles git I/O for changed file detection.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from pathlib import Path


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
    # Verify git repo
    check = _run_git(["rev-parse", "--git-dir"], project_root)
    if isinstance(check, Failure):
        return Failure(f"Not a git repository: {project_root}")

    changed: set[Path] = set()

    # Staged changes
    staged = _run_git(["diff", "--cached", "--name-only"], project_root)
    if isinstance(staged, Success):
        changed.update(_parse_py_files(staged.unwrap(), project_root))

    # Unstaged changes
    unstaged = _run_git(["diff", "--name-only"], project_root)
    if isinstance(unstaged, Success):
        changed.update(_parse_py_files(unstaged.unwrap(), project_root))

    # Untracked files
    untracked = _run_git(["ls-files", "--others", "--exclude-standard"], project_root)
    if isinstance(untracked, Success):
        changed.update(_parse_py_files(untracked.unwrap(), project_root))

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
