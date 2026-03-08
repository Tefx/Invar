"""Subprocess environment preparation with PYTHONPATH injection.

DX-52: Enable uvx-based invar to access project dependencies.

This module provides three phases of dependency injection:
- Phase 1: PYTHONPATH injection for immediate compatibility
- Phase 2: Re-spawn detection for perfect compatibility
- Phase 3: Version mismatch detection for smart upgrade prompts
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from importlib import metadata
from pathlib import Path
from urllib.parse import unquote, urlparse

from deal import post, pre

__all__ = [
    "build_subprocess_env",
    "check_version_mismatch",
    "detect_local_invar_source",
    "detect_project_python_with_invar",
    "detect_project_venv",
    "find_site_packages",
    "get_uvx_respawn_command",
    "get_venv_python_version",
    "maybe_show_upgrade_prompt",
    "should_respawn",
    "should_suppress_prompt",
]


# =============================================================================
# Phase 1: PYTHONPATH Injection
# =============================================================================


VENV_NAMES: tuple[str, ...] = (".venv", "venv", ".env", "env")


@post(lambda result: result is None or result.exists())
def detect_local_invar_source(
    module_file: Path | None = None,
    project_root: Path | None = None,
) -> Path | None:
    """Detect local Invar source checkout root from module location.

    Returns repository root when running from a source checkout (contains
    ``src/invar`` and ``pyproject.toml`` with ``name = "invar-tools"``).
    Returns None for wheel/site-packages installs.

    Args:
        module_file: Optional module path override for testing.
        project_root: Optional cwd/project-root hint used when module_file points to
            site-packages and source checkout is nearby.

    Examples:
        >>> detect_local_invar_source(Path('/tmp/nope/site-packages/invar/x.py')) is None
        True
    """

    def _find_checkout_root(candidate: Path) -> Path | None:
        for parent in (candidate, *candidate.parents):
            pyproject = parent / "pyproject.toml"
            src_pkg = parent / "src" / "invar"

            if not pyproject.exists() or not src_pkg.exists():
                continue

            try:
                content = pyproject.read_text(encoding="utf-8")
            except OSError:
                continue

            if 'name = "invar-tools"' in content:
                return parent

        return None

    candidate = (module_file or Path(__file__)).resolve()
    if (direct_match := _find_checkout_root(candidate)) is not None:
        return direct_match

    if project_root is not None:
        if (cwd_match := _find_checkout_root(project_root.resolve())) is not None:
            return cwd_match

    return None


@pre(lambda cwd: isinstance(cwd, Path))
@post(lambda result: result is None or result.exists())
def detect_project_venv(cwd: Path) -> Path | None:
    """Detect project's virtual environment.

    Searches for common venv directory names with pyvenv.cfg marker.

    Args:
        cwd: Current working directory (project root)

    Returns:
        Path to venv directory, or None if not found

    Examples:
        >>> from pathlib import Path
        >>> detect_project_venv(Path("/nonexistent")) is None
        True
    """
    for name in VENV_NAMES:
        venv_path = cwd / name
        if (venv_path / "pyvenv.cfg").exists():
            return venv_path

    return None


# @shell_complexity: Cross-platform venv layout detection (Unix vs Windows)
@pre(lambda venv_path: isinstance(venv_path, Path))
@post(lambda result: result is None or result.exists())
def find_site_packages(venv_path: Path) -> Path | None:
    """Find site-packages directory within a venv.

    Handles both Unix and Windows layouts.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to site-packages, or None if not found

    Examples:
        >>> from pathlib import Path
        >>> find_site_packages(Path("/nonexistent")) is None
        True
    """
    if not venv_path.exists():
        return None

    # Unix layout: lib/pythonX.Y/site-packages
    lib_path = venv_path / "lib"
    if lib_path.exists():
        for python_dir in lib_path.glob("python*"):
            site_packages = python_dir / "site-packages"
            if site_packages.exists():
                return site_packages

    # Windows layout: Lib/site-packages
    lib_path_win = venv_path / "Lib" / "site-packages"
    if lib_path_win.exists():
        return lib_path_win

    return None


# @shell_complexity: Environment construction with optional PYTHONPATH injection
@post(lambda result: isinstance(result, dict))
def build_subprocess_env(cwd: Path | None = None) -> dict[str, str]:
    """Build environment dict with project's site-packages in PYTHONPATH.

    This enables uvx-based invar to import project dependencies
    when running doctests, property tests, and CrossHair.

    Args:
        cwd: Project root directory (defaults to current directory)

    Returns:
        Environment dict suitable for subprocess.run(env=...)

    Examples:
        >>> env = build_subprocess_env()
        >>> isinstance(env, dict)
        True
        >>> "PATH" in env  # Inherits from current env
        True
    """
    env = os.environ.copy()
    project_root = cwd or Path.cwd()

    venv = detect_project_venv(project_root)
    if venv is None:
        return env

    site_packages = find_site_packages(venv)
    if site_packages is None:
        return env

    current = env.get("PYTHONPATH", "")
    separator = ";" if os.name == "nt" else ":"

    src_dir = project_root / "src"
    prefix_parts: list[str] = []
    if src_dir.exists():
        prefix_parts.append(str(src_dir))
    prefix_parts.append(str(site_packages))

    prefix = separator.join(prefix_parts)
    env["PYTHONPATH"] = f"{prefix}{separator}{current}" if current else prefix

    return env


# =============================================================================
# Phase 2: Smart Re-spawn
# =============================================================================


# @shell_complexity: Cross-platform Python detection with subprocess check
@pre(lambda cwd: isinstance(cwd, Path))
@post(lambda result: result is None or result.exists())
def detect_project_python_with_invar(cwd: Path) -> Path | None:
    """Detect project Python that has invar installed.

    Used by MCP server to decide whether to re-spawn with project Python.

    Args:
        cwd: Project root directory

    Returns:
        Path to Python executable if invar is installed, None otherwise

    Examples:
        >>> from pathlib import Path
        >>> detect_project_python_with_invar(Path("/nonexistent")) is None
        True
    """
    venv = detect_project_venv(cwd)
    if venv is None:
        return None

    # Find Python executable (Unix vs Windows)
    python_path = venv / "bin" / "python"
    if not python_path.exists():
        python_path = venv / "Scripts" / "python.exe"
    if not python_path.exists():
        return None

    # Check if invar is installed in this venv
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import invar"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return python_path
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def _detect_venv_python(venv: Path) -> Path | None:
    python_path = venv / "bin" / "python"
    if not python_path.exists():
        python_path = venv / "Scripts" / "python.exe"
    return python_path if python_path.exists() else None


def detect_running_invar_source() -> Path | None:
    """Detect source path for currently running invar-tools package.

    When launched via `uvx --from /path/to/repo`, package metadata includes
    direct_url.json pointing to that local source path.
    """
    try:
        distribution = metadata.distribution("invar-tools")
        direct_url_raw = distribution.read_text("direct_url.json")
    except metadata.PackageNotFoundError:
        return None

    if not direct_url_raw:
        return None

    try:
        direct_url = json.loads(direct_url_raw)
    except json.JSONDecodeError:
        return None

    url = direct_url.get("url")
    if not isinstance(url, str):
        return None

    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None

    raw_path = parsed.path
    if parsed.netloc:
        raw_path = f"//{parsed.netloc}{parsed.path}"
    source_root = Path(unquote(raw_path)).resolve()

    pyproject = source_root / "pyproject.toml"
    src_pkg = source_root / "src" / "invar"
    if not (pyproject.exists() and src_pkg.exists()):
        return None

    try:
        pyproject_text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return None
    if 'name = "invar-tools"' not in pyproject_text:
        return None

    return source_root


def _can_resolve_uvx_source(
    uvx_path: str,
    python_path: Path,
    source_spec: str,
    tool_name: str,
) -> bool:
    """Check whether uvx can resolve source_spec for target Python.

    Uses a lightweight `version` probe so guard can gracefully skip respawn
    when the pinned artifact cannot be resolved for the project interpreter.
    """
    probe_cmd = [
        uvx_path,
        "--python",
        str(python_path),
        "--from",
        source_spec,
        tool_name,
        "version",
    ]
    try:
        probe = subprocess.run(probe_cmd, capture_output=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


# @shell_complexity: Guardrails for respawn loop, venv detection, version mismatch, and uvx availability
def get_uvx_respawn_command(
    project_root: Path,
    argv: list[str],
    tool_name: str,
    invar_tools_version: str,
) -> list[str] | None:
    if os.environ.get("INVAR_UVX_RESPAWNED") == "1":
        return None

    uvx_path = shutil.which("uvx")
    if uvx_path is None:
        return None

    local_source = detect_local_invar_source(project_root=project_root)
    running_source = detect_local_invar_source() or detect_running_invar_source()
    if local_source is not None and tool_name in {"invar", "invar-tools"}:
        venv = detect_project_venv(project_root)
        project_python = _detect_venv_python(venv) if venv is not None else None
        python_for_uvx = project_python or Path(sys.executable)
        return [
            uvx_path,
            "--python",
            str(python_for_uvx),
            "--from",
            str(local_source),
            tool_name,
            *argv,
        ]

    venv = detect_project_venv(project_root)
    if venv is None:
        return None

    venv_version = get_venv_python_version(venv)
    if venv_version is None:
        return None

    current_version = (sys.version_info.major, sys.version_info.minor)
    if venv_version == current_version:
        return None

    project_python = _detect_venv_python(venv)
    if project_python is None:
        return None

    preferred_source = local_source or running_source
    if preferred_source is not None:
        return [
            uvx_path,
            "--python",
            str(project_python),
            "--from",
            str(preferred_source),
            tool_name,
            *argv,
        ]

    source_spec = f"invar-tools=={invar_tools_version}"
    if not _can_resolve_uvx_source(uvx_path, project_python, source_spec, tool_name):
        return None

    return [
        uvx_path,
        "--python",
        str(project_python),
        "--from",
        source_spec,
        tool_name,
        *argv,
    ]


@pre(lambda cwd: isinstance(cwd, Path))
def should_respawn(cwd: Path) -> tuple[bool, Path | None]:
    """Check if MCP server should re-spawn with project Python.

    Returns:
        (should_respawn, project_python_path)

    Examples:
        >>> from pathlib import Path
        >>> should, python = should_respawn(Path("/nonexistent"))
        >>> should
        False
    """
    project_python = detect_project_python_with_invar(cwd)

    if project_python is None:
        return (False, None)

    # Don't respawn if already running with project Python
    if str(project_python.resolve()) == str(Path(sys.executable).resolve()):
        return (False, None)

    return (True, project_python)


# =============================================================================
# Phase 3: Smart Upgrade Prompt
# =============================================================================


# @shell_complexity: Config file parsing with error handling
@pre(lambda venv_path: isinstance(venv_path, Path))
def get_venv_python_version(venv_path: Path) -> tuple[int, int] | None:
    """Read Python version from venv's pyvenv.cfg.

    Avoids spawning a subprocess by parsing the config file directly.

    Args:
        venv_path: Path to virtual environment

    Returns:
        (major, minor) version tuple, or None if not found

    Examples:
        >>> from pathlib import Path
        >>> get_venv_python_version(Path("/nonexistent")) is None
        True
    """
    cfg_path = venv_path / "pyvenv.cfg"
    if not cfg_path.exists():
        return None

    try:
        for line in cfg_path.read_text().splitlines():
            # Look for "version = X.Y.Z" or "version_info = X.Y.Z"
            if line.startswith("version"):
                # version = 3.11.5 or version_info = 3.11.5
                parts = line.split("=")
                if len(parts) != 2:
                    continue
                version_str = parts[1].strip()
                version_parts = version_str.split(".")
                if len(version_parts) >= 2:
                    return (int(version_parts[0]), int(version_parts[1]))
    except (ValueError, OSError):
        pass

    return None


@pre(lambda cwd: isinstance(cwd, Path))
def check_version_mismatch(cwd: Path) -> tuple[bool, str]:
    """Check if Python versions mismatch between venv and current interpreter.

    Args:
        cwd: Project root directory

    Returns:
        (is_mismatched, warning_message)

    Examples:
        >>> from pathlib import Path
        >>> mismatch, msg = check_version_mismatch(Path("/nonexistent"))
        >>> mismatch
        False
    """
    venv = detect_project_venv(cwd)
    if venv is None:
        return (False, "")

    venv_version = get_venv_python_version(venv)
    if venv_version is None:
        return (False, "")

    current_version = (sys.version_info.major, sys.version_info.minor)

    if venv_version != current_version:
        msg = f"""
[yellow]Python version mismatch detected[/yellow]
  Project venv: {venv_version[0]}.{venv_version[1]}
  uvx invar:    {current_version[0]}.{current_version[1]}

  C extension modules (numpy, pandas, etc.) may fail to load.

  To fix, install invar in your project:
    [cyan]pip install invar-tools[/cyan]

  This enables automatic Python version matching.
"""
        return (True, msg)

    return (False, "")


# @shell_complexity: File system checks with timestamp handling
@pre(lambda project_root: isinstance(project_root, Path))
def should_suppress_prompt(project_root: Path) -> bool:
    """Check if upgrade prompt should be suppressed (pure check, no side effects).

    Strategies:
    - Per-project daily limit (avoid spam)
    - User can permanently disable via .invar/no-upgrade-prompt

    Args:
        project_root: Project root directory

    Returns:
        True if prompt should be suppressed

    Examples:
        >>> from pathlib import Path
        >>> should_suppress_prompt(Path("/nonexistent"))
        False
    """
    invar_dir = project_root / ".invar"

    # Permanent disable file
    if (invar_dir / "no-upgrade-prompt").exists():
        return True

    # Daily limit per project
    marker = invar_dir / ".last-upgrade-prompt"
    if marker.exists():
        try:
            last_time = datetime.fromtimestamp(marker.stat().st_mtime)
            if datetime.now() - last_time < timedelta(days=1):
                return True
        except OSError:
            pass

    return False


def _update_prompt_marker(project_root: Path) -> None:
    """Update the prompt marker timestamp (called after showing prompt).

    Args:
        project_root: Project root directory
    """
    invar_dir = project_root / ".invar"
    marker = invar_dir / ".last-upgrade-prompt"
    try:
        invar_dir.mkdir(exist_ok=True)
        marker.touch()
    except OSError:
        pass


@pre(lambda project_root, console: isinstance(project_root, Path))
def maybe_show_upgrade_prompt(project_root: Path, console: object | None) -> None:
    """Show upgrade prompt if conditions are met.

    Args:
        project_root: Project root directory
        console: Rich console for output

    Examples:
        >>> from pathlib import Path
        >>> # No-op for non-existent paths
        >>> maybe_show_upgrade_prompt(Path("/nonexistent"), None)
    """
    is_mismatched, msg = check_version_mismatch(project_root)

    if not is_mismatched:
        return  # Versions match, no prompt needed

    if should_suppress_prompt(project_root):
        return  # Already prompted recently

    # Update marker before showing (prevents spam on failures)
    _update_prompt_marker(project_root)

    # Print warning if console is available
    printer = getattr(console, "print", None)
    if callable(printer):
        printer(msg)
