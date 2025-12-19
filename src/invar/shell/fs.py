"""
File system operations.

Shell module: performs file I/O operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from returns.result import Failure, Result, Success

from invar.core.models import FileInfo
from invar.core.parser import parse_source
from invar.shell.config import classify_file, get_exclude_paths


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
        # Check exclusions
        relative = py_file.relative_to(project_root)
        relative_str = str(relative)

        excluded = False
        for pattern in exclude_patterns:
            if relative_str.startswith(pattern) or f"/{pattern}/" in f"/{relative_str}":
                excluded = True
                break

        if not excluded:
            yield py_file


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
    file_info = parse_source(content, relative_path)

    if file_info is None:
        return Failure(f"Syntax error in {file_path}")

    # Classify as Core or Shell based on patterns and paths
    classify_result = classify_file(relative_path, project_root)
    file_info.is_core, file_info.is_shell = classify_result.unwrap() if isinstance(classify_result, Success) else (False, False)

    return Success(file_info)


def scan_project(project_root: Path) -> Iterator[Result[FileInfo, str]]:
    """
    Scan a project and yield FileInfo for each Python file.

    Args:
        project_root: Root directory of the project

    Yields:
        Result containing FileInfo or error message for each file
    """
    for py_file in discover_python_files(project_root):
        yield read_and_parse_file(py_file, project_root)
