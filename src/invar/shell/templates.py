"""
Template management for invar init.

Shell module: handles file I/O for template operations.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

from returns.result import Failure, Result, Success

_DEFAULT_PYPROJECT_CONFIG = '''\n# Invar Configuration
[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "scripts", ".venv"]
'''

_DEFAULT_INVAR_TOML = '''# Invar Configuration
# For projects without pyproject.toml

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "scripts", ".venv"]

# Pattern-based classification (optional, takes priority over paths)
# core_patterns = ["**/domain/**", "**/models/**"]
# shell_patterns = ["**/api/**", "**/cli/**"]
'''


def get_template_path(name: str) -> Result[Path, str]:
    """Get path to a template file."""
    try:
        path = Path(str(resources.files("invar.templates").joinpath(name)))
        if not path.exists():
            return Failure(f"Template '{name}' not found")
        return Success(path)
    except Exception as e:
        return Failure(f"Failed to get template path: {e}")


def copy_template(template_name: str, dest: Path, dest_name: str | None = None) -> Result[bool, str]:
    """Copy a template file to destination. Returns Success(True) if copied, Success(False) if skipped."""
    if dest_name is None:
        dest_name = template_name.replace(".template", "")
    dest_file = dest / dest_name
    if dest_file.exists():
        return Success(False)
    template_result = get_template_path(template_name)
    if isinstance(template_result, Failure):
        return template_result
    template_path = template_result.unwrap()
    try:
        dest_file.write_text(template_path.read_text())
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to copy template: {e}")


def add_config(path: Path, console) -> Result[bool, str]:
    """Add configuration to project. Returns Success(True) if added, Success(False) if skipped."""
    pyproject = path / "pyproject.toml"
    invar_toml = path / "invar.toml"

    try:
        if pyproject.exists():
            content = pyproject.read_text()
            if "[tool.invar]" not in content:
                with pyproject.open("a") as f:
                    f.write(_DEFAULT_PYPROJECT_CONFIG)
                console.print("[green]Added[/green] [tool.invar.guard] to pyproject.toml")
                return Success(True)
            return Success(False)

        if not invar_toml.exists():
            invar_toml.write_text(_DEFAULT_INVAR_TOML)
            console.print("[green]Created[/green] invar.toml")
            return Success(True)

        return Success(False)
    except OSError as e:
        return Failure(f"Failed to add config: {e}")


def create_directories(path: Path, console) -> None:
    """Create src/core and src/shell directories."""
    core_path = path / "src" / "core"
    shell_path = path / "src" / "shell"

    if not core_path.exists():
        core_path.mkdir(parents=True)
        (core_path / "__init__.py").touch()
        console.print("[green]Created[/green] src/core/")

    if not shell_path.exists():
        shell_path.mkdir(parents=True)
        (shell_path / "__init__.py").touch()
        console.print("[green]Created[/green] src/shell/")


def install_hooks(path: Path, console) -> Result[bool, str]:
    """Install pre-commit hooks configuration and activate them."""
    import subprocess

    pre_commit_config = path / ".pre-commit-config.yaml"

    if pre_commit_config.exists():
        console.print("[yellow]Skipped[/yellow] .pre-commit-config.yaml (already exists)")
        return Success(False)

    result = copy_template("pre-commit-config.yaml.template", path, ".pre-commit-config.yaml")
    if isinstance(result, Failure):
        return result

    if result.unwrap():
        console.print("[green]Created[/green] .pre-commit-config.yaml")

        # Auto-install hooks (Automatic > Opt-in)
        try:
            subprocess.run(
                ["pre-commit", "install"],
                cwd=path,
                check=True,
                capture_output=True,
            )
            console.print("[green]Installed[/green] pre-commit hooks")
        except FileNotFoundError:
            console.print("[dim]Run: pre-commit install (pre-commit not in PATH)[/dim]")
        except subprocess.CalledProcessError:
            console.print("[dim]Run: pre-commit install (not a git repo?)[/dim]")

        return Success(True)

    return Success(False)
