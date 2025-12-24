"""
Configuration loading from multiple sources.

Shell module: performs file I/O to load configuration.

Configuration sources (priority order):
1. pyproject.toml [tool.invar.guard]
2. invar.toml [guard]
3. .invar/config.toml [guard]
4. Built-in defaults

DX-22: Added content-based auto-detection for Core/Shell classification.
"""

from __future__ import annotations

import tomllib
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from returns.result import Failure, Result, Success

from invar.core.models import RuleConfig
from invar.core.utils import (
    extract_guard_section,
    matches_path_prefix,
    matches_pattern,
    parse_guard_config,
)


class ModuleType(Enum):
    """DX-22: Module type for auto-detection."""

    CORE = "core"
    SHELL = "shell"
    UNKNOWN = "unknown"


# I/O indicators that suggest Shell module
_IO_INDICATORS = frozenset(
    [
        # File operations
        ".read(",
        ".write(",
        ".read_text(",
        ".write_text(",
        "open(",
        "Path(",
        # Subprocess
        "subprocess.",
        "os.system(",
        # Network
        "requests.",
        "aiohttp.",
        "httpx.",
        # Console output
        "print(",
        "console.",
        "typer.",
        # Result monad (Shell pattern)
        "Success(",
        "Failure(",
        "Result[",
    ]
)

# Contract indicators that suggest Core module
_CONTRACT_INDICATORS = frozenset(
    [
        "@pre(",
        "@post(",
        "@invariant(",
    ]
)


# @shell_complexity: Classification decision tree requires multiple conditions
def auto_detect_module_type(source: str, file_path: str = "") -> ModuleType:
    """
    Automatically detect module type from source content.

    DX-22: Content-based classification when path-based is inconclusive.

    Priority:
    1. Path convention (**/core/** or **/shell/**)
    2. Content features (contracts, Result types, I/O operations)

    Args:
        source: Python source code as string
        file_path: Optional file path for path-based hints

    Returns:
        ModuleType indicating Core, Shell, or Unknown

    Examples:
        >>> auto_detect_module_type("@pre(lambda x: x > 0)\\ndef foo(x): pass")
        <ModuleType.CORE: 'core'>
        >>> auto_detect_module_type("def load() -> Result[str, str]: return Success('ok')")
        <ModuleType.SHELL: 'shell'>
        >>> auto_detect_module_type("def helper(): pass")
        <ModuleType.UNKNOWN: 'unknown'>
    """
    # Priority 1: Path convention
    if file_path:
        path_lower = file_path.lower()
        if "/core/" in path_lower or path_lower.endswith("/core"):
            return ModuleType.CORE
        if "/shell/" in path_lower or path_lower.endswith("/shell"):
            return ModuleType.SHELL

    # Priority 2: Content features
    has_contracts = any(indicator in source for indicator in _CONTRACT_INDICATORS)
    has_io = any(indicator in source for indicator in _IO_INDICATORS)
    has_result = "Result[" in source or "Success(" in source or "Failure(" in source

    # Core: has contracts AND no I/O
    if has_contracts and not has_io:
        return ModuleType.CORE

    # Shell: has I/O or Result types
    if has_io or has_result:
        return ModuleType.SHELL

    # Unknown: neither clear pattern
    return ModuleType.UNKNOWN

if TYPE_CHECKING:
    from pathlib import Path

ConfigSource = Literal["pyproject", "invar", "invar_dir", "default"]


# @shell_complexity: Config cascade checks multiple sources with fallback
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


# @shell_complexity: Config loading with multiple sources and parse error handling
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
    "tests",
    "test",
    "scripts",
    ".venv",
    "venv",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".tox",
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


# @invar:allow entry_point_too_thick: False positive - .get() matches router.get pattern
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
    core_patterns, shell_patterns = (
        pattern_result.unwrap() if isinstance(pattern_result, Success) else ([], [])
    )

    path_result = get_path_classification(project_root)
    core_paths, shell_paths = (
        path_result.unwrap()
        if isinstance(path_result, Success)
        else (_DEFAULT_CORE_PATHS, _DEFAULT_SHELL_PATHS)
    )

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
