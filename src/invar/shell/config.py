"""
Configuration loading from pyproject.toml.

Shell module: performs file I/O to load configuration.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from returns.result import Failure, Result, Success

from invar.core.rules import RuleConfig


def load_config(project_root: Path) -> Result[RuleConfig, str]:
    """
    Load Invar configuration from pyproject.toml.

    Args:
        project_root: Path to project root directory

    Returns:
        Result containing RuleConfig or error message
    """
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return Success(RuleConfig())  # Use defaults

    try:
        content = pyproject_path.read_text(encoding="utf-8")
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        return Failure(f"Invalid TOML in pyproject.toml: {e}")

    return Success(_parse_config(data))


def _parse_config(data: dict[str, Any]) -> RuleConfig:
    """Parse configuration from TOML data."""
    guard_config = data.get("tool", {}).get("invar", {}).get("guard", {})

    kwargs: dict[str, Any] = {}

    if "max_file_lines" in guard_config:
        kwargs["max_file_lines"] = guard_config["max_file_lines"]

    if "max_function_lines" in guard_config:
        kwargs["max_function_lines"] = guard_config["max_function_lines"]

    if "forbidden_imports" in guard_config:
        kwargs["forbidden_imports"] = tuple(guard_config["forbidden_imports"])

    if "require_contracts" in guard_config:
        kwargs["require_contracts"] = guard_config["require_contracts"]

    if "require_doctests" in guard_config:
        kwargs["require_doctests"] = guard_config["require_doctests"]

    return RuleConfig(**kwargs)


def get_path_classification(project_root: Path) -> tuple[list[str], list[str]]:
    """
    Get Core and Shell path patterns from configuration.

    Returns:
        Tuple of (core_paths, shell_paths)
    """
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return (["src/core", "core"], ["src/shell", "shell"])

    try:
        content = pyproject_path.read_text(encoding="utf-8")
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return (["src/core", "core"], ["src/shell", "shell"])

    guard_config = data.get("tool", {}).get("invar", {}).get("guard", {})

    core_paths = guard_config.get("core_paths", ["src/core", "core"])
    shell_paths = guard_config.get("shell_paths", ["src/shell", "shell"])

    return (core_paths, shell_paths)


_DEFAULT_EXCLUDE_PATHS = [
    "tests", "test", "scripts",
    ".venv", "venv", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".git", ".hg", ".svn",
    "node_modules", "dist", "build", ".tox",
]


def get_exclude_paths(project_root: Path) -> list[str]:
    """
    Get paths to exclude from checking.

    Returns:
        List of path patterns to exclude
    """
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return _DEFAULT_EXCLUDE_PATHS.copy()

    try:
        content = pyproject_path.read_text(encoding="utf-8")
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return _DEFAULT_EXCLUDE_PATHS.copy()

    guard_config = data.get("tool", {}).get("invar", {}).get("guard", {})

    return guard_config.get("exclude_paths", _DEFAULT_EXCLUDE_PATHS.copy())
