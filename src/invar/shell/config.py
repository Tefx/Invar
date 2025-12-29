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

import ast
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


# I/O libraries that indicate Shell module (for AST import checking)
_IO_LIBRARIES = frozenset([
    "os", "sys", "subprocess", "pathlib", "shutil", "io", "socket",
    "requests", "aiohttp", "httpx", "urllib", "sqlite3", "psycopg2",
    "pymongo", "sqlalchemy", "typer", "click",
])

# Contract decorator names
_CONTRACT_DECORATORS = frozenset(["pre", "post", "invariant"])

# Result monad types
_RESULT_TYPES = frozenset(["Result", "Success", "Failure"])


# @shell_orchestration: AST analysis
# @shell_complexity: AST branches
def _has_contract_decorators(tree: ast.Module) -> bool:
    """
    Check if AST contains @pre/@post contract decorators.

    Uses AST to only detect real decorators, not strings in docstrings.

    Examples:
        >>> import ast
        >>> tree = ast.parse("@pre(lambda x: x > 0)\\ndef foo(x): pass")
        >>> _has_contract_decorators(tree)
        True
        >>> tree = ast.parse("def foo():\\n    '''>>> @pre(x)'''\\n    pass")
        >>> _has_contract_decorators(tree)
        False
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for decorator in node.decorator_list:
                # @pre(...) or @post(...)
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Name) and func.id in _CONTRACT_DECORATORS:
                        return True
                    if isinstance(func, ast.Attribute) and func.attr in _CONTRACT_DECORATORS:
                        return True
                # @pre (without call - rare but possible)
                elif isinstance(decorator, ast.Name) and decorator.id in _CONTRACT_DECORATORS:
                    return True
    return False


# @shell_orchestration: AST analysis
# @shell_complexity: AST branches
def _has_io_imports(tree: ast.Module) -> bool:
    """
    Check if AST contains imports of I/O libraries.

    Examples:
        >>> import ast
        >>> tree = ast.parse("import os")
        >>> _has_io_imports(tree)
        True
        >>> tree = ast.parse("from pathlib import Path")
        >>> _has_io_imports(tree)
        True
        >>> tree = ast.parse("import json")
        >>> _has_io_imports(tree)
        False
        >>> tree = ast.parse("def foo():\\n    '''import os'''\\n    pass")
        >>> _has_io_imports(tree)
        False
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lib = alias.name.split(".")[0]
                if lib in _IO_LIBRARIES:
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            lib = node.module.split(".")[0]
            if lib in _IO_LIBRARIES:
                return True
    return False


# @shell_orchestration: AST analysis
# @shell_complexity: AST branches
def _has_result_types(tree: ast.Module) -> bool:
    """
    Check if AST contains Result/Success/Failure usage.

    Checks:
    - Return type annotations: -> Result[T, E]
    - Imports: from returns.result import Success
    - Function calls: Success(...), Failure(...)

    Examples:
        >>> import ast
        >>> tree = ast.parse("from returns.result import Success")
        >>> _has_result_types(tree)
        True
        >>> tree = ast.parse("def foo() -> Result[int, str]: pass")
        >>> _has_result_types(tree)
        True
        >>> tree = ast.parse("return Success(42)")
        >>> _has_result_types(tree)
        True
        >>> tree = ast.parse("def foo():\\n    '''Success'''\\n    pass")
        >>> _has_result_types(tree)
        False
    """
    for node in ast.walk(tree):
        # Check imports: from returns.result import Success
        if isinstance(node, ast.ImportFrom):
            if node.module and "returns" in node.module:
                for alias in node.names:
                    if alias.name in _RESULT_TYPES:
                        return True
        # Check function calls: Success(...), Failure(...)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _RESULT_TYPES:
                return True
        # Check type annotations: -> Result[T, E]
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.returns:
                ann = node.returns
                if isinstance(ann, ast.Subscript):
                    if isinstance(ann.value, ast.Name) and ann.value.id == "Result":
                        return True
                elif isinstance(ann, ast.Name) and ann.id in _RESULT_TYPES:
                    return True
    return False


# @shell_complexity: Classification decision tree requires multiple conditions
def auto_detect_module_type(source: str, file_path: str = "") -> ModuleType:
    """
    Automatically detect module type from source content using AST.

    DX-22: Content-based classification when path-based is inconclusive.
    Uses AST parsing to avoid false positives from docstrings/comments.

    Priority:
    1. Path convention (**/core/** or **/shell/**)
    2. Content features via AST (contracts, Result types, I/O imports)

    Args:
        source: Python source code as string
        file_path: Optional file path for path-based hints

    Returns:
        ModuleType indicating Core, Shell, or Unknown

    Examples:
        >>> auto_detect_module_type("@pre(lambda x: x > 0)\\ndef foo(x): pass")
        <ModuleType.CORE: 'core'>
        >>> auto_detect_module_type("from returns.result import Success\\ndef load(): return Success('ok')")
        <ModuleType.SHELL: 'shell'>
        >>> auto_detect_module_type("def helper(): pass")
        <ModuleType.UNKNOWN: 'unknown'>
        >>> auto_detect_module_type("def foo():\\n    '''>>> @pre(x)'''\\n    pass")
        <ModuleType.UNKNOWN: 'unknown'>
    """
    # Priority 1: Path convention
    if file_path:
        path_lower = file_path.lower()
        if "/core/" in path_lower or path_lower.endswith("/core"):
            return ModuleType.CORE
        if "/shell/" in path_lower or path_lower.endswith("/shell"):
            return ModuleType.SHELL

    # Priority 2: Content features via AST
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ModuleType.UNKNOWN

    has_contracts = _has_contract_decorators(tree)
    has_io = _has_io_imports(tree)
    has_result = _has_result_types(tree)

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


# @shell_complexity: Project root discovery requires checking multiple markers
def find_project_root(start_path: "Path") -> "Path":  # noqa: UP037
    """
    Find project root by walking up from start_path looking for config files.

    Looks for (in order): pyproject.toml, invar.toml, .invar/, .git/

    Args:
        start_path: Starting path (file or directory)

    Returns:
        Project root directory (absolute path), or start_path's parent if no markers found

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir).resolve()
        ...     (root / "pyproject.toml").touch()
        ...     subdir = root / "src" / "core"
        ...     subdir.mkdir(parents=True)
        ...     found = find_project_root(subdir / "file.py")
        ...     found == root
        True
    """
    from pathlib import Path

    current = Path(start_path).resolve()  # Resolve to absolute path
    if current.is_file():
        current = current.parent

    # Walk up looking for project markers
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
        if (parent / "invar.toml").exists():
            return parent
        if (parent / ".invar").is_dir():
            return parent
        if (parent / ".git").exists():
            return parent

    # Fallback to the starting directory
    return current


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
    # Templates and examples are documentation, not enforced code
    "templates",
    ".invar/examples",
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


# @shell_complexity: Classification decision tree requires multiple config lookups and priority checks
# @invar:allow entry_point_too_thick: False positive - .get() matches router.get pattern
def classify_file(
    file_path: str, project_root: Path, source: str = ""
) -> Result[tuple[bool, bool], str]:
    """
    Classify a file as Core, Shell, or neither.

    DX-22 Part 5: Priority order is patterns > paths > content > uncategorized.

    Args:
        file_path: Relative path to the file
        project_root: Project root directory
        source: Optional source content for content-based detection

    Examples:
        >>> import tempfile
        >>> from pathlib import Path
        >>> with tempfile.TemporaryDirectory() as tmpdir:
        ...     root = Path(tmpdir)
        ...     result = classify_file("src/core/logic.py", root)
        ...     result.unwrap()[0]
        True
        >>> classify_file("lib/utils.py", Path("."), "@pre(lambda x: x > 0)\\ndef foo(x): pass").unwrap()
        (True, False)
        >>> classify_file("lib/io.py", Path("."), "def read() -> Result[str, str]: return Success('ok')").unwrap()
        (False, True)
    """
    pattern_result = get_pattern_classification(project_root)
    if isinstance(pattern_result, Success):
        core_patterns, shell_patterns = pattern_result.unwrap()
    else:
        # Log warning about config error, use defaults
        import logging
        logging.getLogger(__name__).debug(
            "Pattern classification failed: %s, using defaults", pattern_result.failure()
        )
        core_patterns, shell_patterns = ([], [])

    path_result = get_path_classification(project_root)
    if isinstance(path_result, Success):
        core_paths, shell_paths = path_result.unwrap()
    else:
        # Log warning about config error, use defaults
        import logging
        logging.getLogger(__name__).debug(
            "Path classification failed: %s, using defaults", path_result.failure()
        )
        core_paths, shell_paths = (_DEFAULT_CORE_PATHS, _DEFAULT_SHELL_PATHS)

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

    # Priority 3: Content-based auto-detection (DX-22 Part 5)
    if source:
        module_type = auto_detect_module_type(source, file_path)
        if module_type == ModuleType.CORE:
            return Success((True, False))
        if module_type == ModuleType.SHELL:
            return Success((False, True))

    return Success((False, False))
