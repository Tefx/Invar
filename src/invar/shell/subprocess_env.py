"""Subprocess environment preparation with PYTHONPATH injection.

DX-52: Enable uvx-based invar to access project dependencies.

This module provides three phases of dependency injection:
- Phase 1: PYTHONPATH injection for immediate compatibility
- Phase 2: Re-spawn detection for perfect compatibility
- Phase 3: Version mismatch detection for smart upgrade prompts
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from deal import post, pre

__all__ = [
    "build_subprocess_env",
    "check_version_mismatch",
    "detect_project_python_with_invar",
    "detect_project_venv",
    "find_site_packages",
    "get_venv_python_version",
    "maybe_show_upgrade_prompt",
    "should_respawn",
    "should_suppress_prompt",
]


# =============================================================================
# Phase 1: PYTHONPATH Injection
# =============================================================================


VENV_NAMES: tuple[str, ...] = (".venv", "venv", ".env", "env")


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

    # Prepend to PYTHONPATH (project packages have priority)
    current = env.get("PYTHONPATH", "")
    separator = ";" if os.name == "nt" else ":"
    if current:
        env["PYTHONPATH"] = f"{site_packages}{separator}{current}"
    else:
        env["PYTHONPATH"] = str(site_packages)

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
def maybe_show_upgrade_prompt(project_root: Path, console: object) -> None:
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
    if console is not None and hasattr(console, "print"):
        console.print(msg)
