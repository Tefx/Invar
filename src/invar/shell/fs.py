"""
File system operations.

Shell module: performs file I/O operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

from invar.core.models import FileInfo
from invar.core.parser import parse_source
from invar.shell.config import classify_file, get_exclude_paths

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


# @shell_orchestration: Helper for file discovery, co-located with I/O functions
def _is_excluded(relative_str: str, exclude_patterns: list[str]) -> bool:
    """Check if a relative path should be excluded.

    Matches patterns as whole path components, not as prefixes:
    - "dist" matches "dist", "dist/file.py", "src/dist/file.py"
    - "dist" does NOT match "distribute" or "mydist" (prefix/suffix matching)

    Note: A file literally named "some/dist" (not a directory) would not match
    pattern "dist" - this is intentional as patterns target directory names.

    Unix path assumption: Uses "/" separator. On Windows, paths should be
    normalized before calling (Python's pathlib handles this).
    """
    for pattern in exclude_patterns:
        # Match whole path component, not prefix
        if relative_str == pattern or relative_str.startswith(pattern + "/") or f"/{pattern}/" in f"/{relative_str}":
            return True
    return False


# @shell_complexity: Recursive file discovery with gitignore and exclusions
def discover_python_files(
    project_root: Path,
    exclude_patterns: list[str] | None = None,
) -> Iterator[Path]:
    """
    Discover all Python files in a project.

    Args:
        project_root: Root directory to search
        exclude_patterns: Patterns to exclude (uses config defaults if None)

    Yields:
        Path objects for each Python file found
    """
    if exclude_patterns is None:
        exclude_result = get_exclude_paths(project_root)
        exclude_patterns = exclude_result.unwrap() if isinstance(exclude_result, Success) else []

    for py_file in project_root.rglob("*.py"):
        # Check exclusions using shared helper
        relative_str = str(py_file.relative_to(project_root))
        if not _is_excluded(relative_str, exclude_patterns):
            yield py_file


# @shell_complexity: Recursive TypeScript file discovery with exclusions
def discover_typescript_files(
    project_root: Path,
    exclude_patterns: list[str] | None = None,
) -> Iterator[Path]:
    """
    Discover all TypeScript files in a project (LX-06).

    Args:
        project_root: Root directory to search
        exclude_patterns: Patterns to exclude (uses config defaults if None)

    Yields:
        Path objects for each TypeScript file found
    """
    if exclude_patterns is None:
        exclude_result = get_exclude_paths(project_root)
        exclude_patterns = exclude_result.unwrap() if isinstance(exclude_result, Success) else []

    # Always exclude node_modules and common build directories
    default_ts_excludes = ["node_modules", "dist", "build", ".next", "out"]
    all_excludes = list(set(list(exclude_patterns) + default_ts_excludes))

    for ext in ("*.ts", "*.tsx"):
        for ts_file in project_root.rglob(ext):
            # Check exclusions using shared helper (DX review: deduplicate)
            relative_str = str(ts_file.relative_to(project_root))
            if not _is_excluded(relative_str, all_excludes):
                yield ts_file


# @shell_complexity: File reading with AST parsing and error handling
def read_and_parse_file(file_path: Path, project_root: Path) -> Result[FileInfo, str]:
    """
    Read a Python file and parse it into FileInfo.

    Args:
        file_path: Path to the Python file
        project_root: Project root for relative path calculation

    Returns:
        Result containing FileInfo or error message
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return Failure(f"Failed to read {file_path}: {e}")

    relative_path = str(file_path.relative_to(project_root))

    # Skip empty files (e.g., __init__.py) - return empty FileInfo
    if not content.strip():
        return Success(FileInfo(path=relative_path, lines=0, symbols=[], imports=[], source=""))

    file_info = parse_source(content, relative_path)

    if file_info is None:
        return Failure(f"Syntax error in {file_path}")

    # Classify as Core or Shell based on patterns, paths, and content (DX-22 Part 5)
    classify_result = classify_file(relative_path, project_root, file_info.source)
    file_info.is_core, file_info.is_shell = (
        classify_result.unwrap() if isinstance(classify_result, Success) else (False, False)
    )

    return Success(file_info)


# @shell_complexity: Project scanning with exclusions and error handling
def scan_project(
    project_root: Path,
    only_files: set[Path] | None = None,
) -> Iterator[Result[FileInfo, str]]:
    """
    Scan a project and yield FileInfo for each Python file.

    Args:
        project_root: Root directory of the project
        only_files: If provided, only scan these files (for --changed mode)

    Yields:
        Result containing FileInfo or error message for each file
    """
    # Get exclusion patterns once
    exclude_result = get_exclude_paths(project_root)
    exclude_patterns = exclude_result.unwrap() if isinstance(exclude_result, Success) else []

    if only_files is not None:
        # Phase 8.1: --changed mode - only scan specified files (with exclusions)
        for py_file in only_files:
            if py_file.exists() and py_file.suffix == ".py":
                # Apply exclusions even in --changed mode
                try:
                    relative_str = str(py_file.relative_to(project_root))
                except ValueError:
                    relative_str = str(py_file)
                if not _is_excluded(relative_str, exclude_patterns):
                    yield read_and_parse_file(py_file, project_root)
    else:
        for py_file in discover_python_files(project_root, exclude_patterns):
            yield read_and_parse_file(py_file, project_root)
