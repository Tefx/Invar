"""
Configuration loading from multiple sources.

Shell module: performs file I/O to load configuration.

Configuration sources (priority order):
1. pyproject.toml [tool.invar.guard]
2. invar.toml [guard]
3. .invar/config.toml [guard]
4. Built-in defaults
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from returns.result import Failure, Result, Success

from invar.core.models import RuleConfig
from invar.core.utils import extract_guard_section, matches_path_prefix, matches_pattern, parse_guard_config


ConfigSource = Literal["pyproject", "invar", "invar_dir", "default"]


def _find_config_source(project_root: Path) -> Result[tuple[Path | None, ConfigSource], str]:
    """
    Find the first available config file.

    Returns:
        Result containing tuple of (config_path, source_type)

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir)
        ...     result = _find_config_source(root)
        ...     result.unwrap()[1]
        'default'
    """
    try:
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            return Success((pyproject, "pyproject"))

        invar_toml = project_root / "invar.toml"
        if invar_toml.exists():
            return Success((invar_toml, "invar"))

        invar_config = project_root / ".invar" / "config.toml"
        if invar_config.exists():
            return Success((invar_config, "invar_dir"))

        return Success((None, "default"))
    except OSError as e:
        return Failure(f"Failed to find config: {e}")


def _read_toml(path: Path) -> Result[dict[str, Any], str]:
    """Read and parse a TOML file."""
    try:
        content = path.read_text(encoding="utf-8")
        return Success(tomllib.loads(content))
    except tomllib.TOMLDecodeError as e:
        return Failure(f"Invalid TOML in {path.name}: {e}")
    except OSError as e:
        return Failure(f"Failed to read {path.name}: {e}")


def load_config(project_root: Path) -> Result[RuleConfig, str]:
    """
    Load Invar configuration from available sources.

    Tries sources in priority order:
    1. pyproject.toml [tool.invar.guard]
    2. invar.toml [guard]
    3. .invar/config.toml [guard]
    4. Built-in defaults

    Args:
        project_root: Path to project root directory

    Returns:
        Result containing RuleConfig or error message
    """
    find_result = _find_config_source(project_root)
    if isinstance(find_result, Failure):
        return find_result
    config_path, source = find_result.unwrap()

    if source == "default":
        return Success(RuleConfig())

    assert config_path is not None  # source != "default" guarantees path exists
    result = _read_toml(config_path)

    if isinstance(result, Failure):
        return result

    data = result.unwrap()
    guard_config = extract_guard_section(data, source)

    # For pyproject.toml, if no [tool.invar.guard] section, use defaults
    if source == "pyproject" and not guard_config:
        return Success(RuleConfig())

    return Success(parse_guard_config(guard_config))


# Default paths for Core/Shell classification
_DEFAULT_CORE_PATHS = ["src/core", "core"]
_DEFAULT_SHELL_PATHS = ["src/shell", "shell"]

# Default exclude paths
_DEFAULT_EXCLUDE_PATHS = [
    "tests", "test", "scripts",
    ".venv", "venv", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", ".hg", ".svn",
    "node_modules", "dist", "build", ".tox",
]


def _get_classification_config(project_root: Path) -> Result[dict[str, Any], str]:
    """Get classification-related config (paths and patterns)."""
    find_result = _find_config_source(project_root)
    if isinstance(find_result, Failure):
        return Success({})  # Return empty on error
    config_path, source = find_result.unwrap()

    if source == "default":
        return Success({})

    assert config_path is not None
    result = _read_toml(config_path)

    if isinstance(result, Failure):
        return Success({})  # Return empty on error

    data = result.unwrap()
    return Success(extract_guard_section(data, source))


def get_path_classification(project_root: Path) -> Result[tuple[list[str], list[str]], str]:
    """
    Get Core and Shell path prefixes from configuration.

    Returns:
        Result containing tuple of (core_paths, shell_paths)
    """
    config_result = _get_classification_config(project_root)
    guard_config = config_result.unwrap() if isinstance(config_result, Success) else {}

    core_paths = guard_config.get("core_paths", _DEFAULT_CORE_PATHS)
    shell_paths = guard_config.get("shell_paths", _DEFAULT_SHELL_PATHS)

    return Success((core_paths, shell_paths))


def get_pattern_classification(project_root: Path) -> Result[tuple[list[str], list[str]], str]:
    """
    Get Core and Shell glob patterns from configuration.

    Returns:
        Result containing tuple of (core_patterns, shell_patterns)
    """
    config_result = _get_classification_config(project_root)
    guard_config = config_result.unwrap() if isinstance(config_result, Success) else {}

    core_patterns = guard_config.get("core_patterns", [])
    shell_patterns = guard_config.get("shell_patterns", [])

    return Success((core_patterns, shell_patterns))


def get_exclude_paths(project_root: Path) -> Result[list[str], str]:
    """
    Get paths to exclude from checking.

    Returns:
        Result containing list of path patterns to exclude
    """
    config_result = _get_classification_config(project_root)
    guard_config = config_result.unwrap() if isinstance(config_result, Success) else {}
    return Success(guard_config.get("exclude_paths", _DEFAULT_EXCLUDE_PATHS.copy()))


def classify_file(file_path: str, project_root: Path) -> Result[tuple[bool, bool], str]:
    """
    Classify a file as Core, Shell, or neither.

    Priority: patterns > paths > uncategorized.

    Examples:
        >>> import tempfile
        >>> from pathlib import Path
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir)
        ...     result = classify_file("src/core/logic.py", root)
        ...     result.unwrap()[0]
        True
    """
    pattern_result = get_pattern_classification(project_root)
    core_patterns, shell_patterns = pattern_result.unwrap() if isinstance(pattern_result, Success) else ([], [])

    path_result = get_path_classification(project_root)
    core_paths, shell_paths = path_result.unwrap() if isinstance(path_result, Success) else (_DEFAULT_CORE_PATHS, _DEFAULT_SHELL_PATHS)

    # Priority 1: Pattern-based classification
    if core_patterns and matches_pattern(file_path, core_patterns):
        return Success((True, False))
    if shell_patterns and matches_pattern(file_path, shell_patterns):
        return Success((False, True))

    # Priority 2: Path-based classification
    if matches_path_prefix(file_path, core_paths):
        return Success((True, False))
    if matches_path_prefix(file_path, shell_paths):
        return Success((False, True))

    return Success((False, False))
