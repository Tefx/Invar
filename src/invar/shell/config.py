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

import fnmatch
import tomllib
from pathlib import Path
from typing import Any, Literal

from deal import post, pre
from returns.result import Failure, Result, Success

from invar.core.models import RuleConfig


ConfigSource = Literal["pyproject", "invar", "invar_dir", "default"]


def _find_config_source(project_root: Path) -> tuple[Path | None, ConfigSource]:
    """
    Find the first available config file.

    Returns:
        Tuple of (config_path, source_type)

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir)
        ...     path, source = _find_config_source(root)
        ...     source
        'default'
    """
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        return (pyproject, "pyproject")

    invar_toml = project_root / "invar.toml"
    if invar_toml.exists():
        return (invar_toml, "invar")

    invar_config = project_root / ".invar" / "config.toml"
    if invar_config.exists():
        return (invar_config, "invar_dir")

    return (None, "default")


def _read_toml(path: Path) -> Result[dict[str, Any], str]:
    """Read and parse a TOML file."""
    try:
        content = path.read_text(encoding="utf-8")
        return Success(tomllib.loads(content))
    except tomllib.TOMLDecodeError as e:
        return Failure(f"Invalid TOML in {path.name}: {e}")
    except OSError as e:
        return Failure(f"Failed to read {path.name}: {e}")


@pre(lambda data, source: isinstance(data, dict) and source in ("pyproject", "invar", "invar_dir", "default"))
@post(lambda result: isinstance(result, dict))
def _extract_guard_section(data: dict[str, Any], source: ConfigSource) -> dict[str, Any]:
    """Extract guard config section based on source type."""
    if source == "pyproject":
        return data.get("tool", {}).get("invar", {}).get("guard", {})
    # invar.toml and .invar/config.toml use [guard] directly
    return data.get("guard", {})


@pre(lambda guard_config: isinstance(guard_config, dict))
@post(lambda result: isinstance(result, RuleConfig))
def _parse_config(guard_config: dict[str, Any]) -> RuleConfig:
    """Parse configuration from guard section."""
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

    # Phase 3: Guard Enhancement
    if "strict_pure" in guard_config:
        kwargs["strict_pure"] = guard_config["strict_pure"]

    if "use_code_lines" in guard_config:
        kwargs["use_code_lines"] = guard_config["use_code_lines"]

    return RuleConfig(**kwargs)


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
    config_path, source = _find_config_source(project_root)

    if source == "default":
        return Success(RuleConfig())

    assert config_path is not None  # satisfy type checker
    result = _read_toml(config_path)

    if isinstance(result, Failure):
        return result

    data = result.unwrap()
    guard_config = _extract_guard_section(data, source)

    # For pyproject.toml, if no [tool.invar.guard] section, use defaults
    if source == "pyproject" and not guard_config:
        return Success(RuleConfig())

    return Success(_parse_config(guard_config))


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


def _get_classification_config(project_root: Path) -> dict[str, Any]:
    """Get classification-related config (paths and patterns)."""
    config_path, source = _find_config_source(project_root)

    if source == "default":
        return {}

    assert config_path is not None
    result = _read_toml(config_path)

    if isinstance(result, Failure):
        return {}

    data = result.unwrap()
    return _extract_guard_section(data, source)


def get_path_classification(project_root: Path) -> tuple[list[str], list[str]]:
    """
    Get Core and Shell path prefixes from configuration.

    Returns:
        Tuple of (core_paths, shell_paths)
    """
    guard_config = _get_classification_config(project_root)

    core_paths = guard_config.get("core_paths", _DEFAULT_CORE_PATHS)
    shell_paths = guard_config.get("shell_paths", _DEFAULT_SHELL_PATHS)

    return (core_paths, shell_paths)


def get_pattern_classification(project_root: Path) -> tuple[list[str], list[str]]:
    """
    Get Core and Shell glob patterns from configuration.

    Returns:
        Tuple of (core_patterns, shell_patterns)
    """
    guard_config = _get_classification_config(project_root)

    core_patterns = guard_config.get("core_patterns", [])
    shell_patterns = guard_config.get("shell_patterns", [])

    return (core_patterns, shell_patterns)


def get_exclude_paths(project_root: Path) -> list[str]:
    """
    Get paths to exclude from checking.

    Returns:
        List of path patterns to exclude
    """
    guard_config = _get_classification_config(project_root)
    return guard_config.get("exclude_paths", _DEFAULT_EXCLUDE_PATHS.copy())


@pre(lambda file_path, patterns: isinstance(file_path, str) and isinstance(patterns, list))
def matches_pattern(file_path: str, patterns: list[str]) -> bool:
    """
    Check if a file path matches any of the glob patterns.

    Args:
        file_path: Relative file path to check
        patterns: List of glob patterns

    Returns:
        True if file matches any pattern

    Examples:
        >>> matches_pattern("src/domain/models.py", ["**/domain/**"])
        True
        >>> matches_pattern("src/api/views.py", ["**/domain/**"])
        False
        >>> matches_pattern("src/core/logic.py", ["src/core/**", "**/models/**"])
        True
    """
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
        # Also check with leading path component for ** patterns
        if pattern.startswith("**/"):
            # Match anywhere in path
            if fnmatch.fnmatch(file_path, pattern[3:]):
                return True
            # Try matching each subpath
            parts = file_path.split("/")
            for i in range(len(parts)):
                subpath = "/".join(parts[i:])
                if fnmatch.fnmatch(subpath, pattern[3:]):
                    return True
    return False


@pre(lambda file_path, prefixes: isinstance(file_path, str) and isinstance(prefixes, list))
def _matches_path_prefix(file_path: str, prefixes: list[str]) -> bool:
    """Check if file_path starts with any of the given prefixes."""
    return any(file_path.startswith(p) for p in prefixes)


def classify_file(file_path: str, project_root: Path) -> tuple[bool, bool]:
    """
    Classify a file as Core, Shell, or neither.

    Priority: patterns > paths > uncategorized.

    Examples:
        >>> import tempfile
        >>> from pathlib import Path
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir)
        ...     is_core, is_shell = classify_file("src/core/logic.py", root)
        ...     is_core
        True
    """
    core_patterns, shell_patterns = get_pattern_classification(project_root)
    core_paths, shell_paths = get_path_classification(project_root)

    # Priority 1: Pattern-based classification
    if core_patterns and matches_pattern(file_path, core_patterns):
        return (True, False)
    if shell_patterns and matches_pattern(file_path, shell_patterns):
        return (False, True)

    # Priority 2: Path-based classification
    if _matches_path_prefix(file_path, core_paths):
        return (True, False)
    if _matches_path_prefix(file_path, shell_paths):
        return (False, True)

    return (False, False)
