"""
CLI commands using Typer.

Shell module: handles user interaction and file I/O.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from returns.result import Failure, Success

from invar import __version__
from invar.core.models import GuardReport, RuleConfig, Severity
from invar.core.rules import check_all_rules
from invar.shell.config import load_config
from invar.shell.fs import scan_project

app = typer.Typer(
    name="invar",
    help="AI-native software engineering framework",
    add_completion=False,
)
console = Console()


def _scan_and_check(path: Path, config: RuleConfig) -> GuardReport:
    """Scan project files and check against rules."""
    report = GuardReport(files_checked=0)
    for file_result in scan_project(path):
        if isinstance(file_result, Failure):
            console.print(f"[yellow]Warning:[/yellow] {file_result.failure()}")
            continue
        file_info = file_result.unwrap()
        report.files_checked += 1
        for violation in check_all_rules(file_info, config):
            report.add_violation(violation)
    return report


def _get_exit_code(report: GuardReport, strict: bool) -> int:
    """Determine exit code based on report and strict mode."""
    if report.errors > 0:
        return 1
    if strict and report.warnings > 0:
        return 1
    return 0


@app.command()
def guard(
    path: Path = typer.Argument(Path("."), help="Project root directory",
                                 exists=True, file_okay=False, dir_okay=True),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    strict_pure: bool = typer.Option(False, "--strict-pure",
                                      help="Enable strict purity checks (internal imports, impure calls)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check project against Invar architecture rules."""
    config_result = load_config(path)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)

    config = config_result.unwrap()
    # Override strict_pure if specified on command line
    if strict_pure:
        config.strict_pure = True

    report = _scan_and_check(path, config)
    _output_json(report) if json_output else _output_rich(report, config.strict_pure)
    raise typer.Exit(_get_exit_code(report, strict))


def _output_rich(report: GuardReport, strict_pure: bool = False) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    if strict_pure:
        console.print("[cyan](strict-pure mode enabled)[/cyan]")
    console.print()

    if not report.violations:
        console.print("[green]No violations found.[/green]")
    else:
        by_file: dict[str, list] = {}
        for v in report.violations:
            by_file.setdefault(v.file, []).append(v)
        for fp, vs in sorted(by_file.items()):
            console.print(f"[bold]{fp}[/bold]")
            for v in vs:
                icon = "[red]ERROR[/red]" if v.severity == Severity.ERROR else "[yellow]WARN[/yellow]"
                ln = f":{v.line}" if v.line else ""
                console.print(f"  {icon} {ln} {v.message}")
            console.print()

    console.print("-" * 40)
    console.print(f"Files checked: {report.files_checked}\nErrors: {report.errors}\nWarnings: {report.warnings}")
    console.print(f"\n[{'green' if report.passed else 'red'}]Guard {'passed' if report.passed else 'failed'}.[/]")
    console.print("\n[dim]Note: Guard performs static analysis only. Dynamic imports and runtime behavior are not checked.[/dim]")


def _output_json(report: GuardReport) -> None:
    """Output report as JSON."""
    import json

    output = {
        "files_checked": report.files_checked,
        "errors": report.errors,
        "warnings": report.warnings,
        "passed": report.passed,
        "violations": [v.model_dump() for v in report.violations],
    }
    console.print(json.dumps(output, indent=2))


@app.command()
def version() -> None:
    """Show Invar version."""
    console.print(f"invar {__version__}")


@app.command("map")
def map_command(
    path: Path = typer.Argument(Path("."), help="Project root directory"),
    top: int = typer.Option(0, "--top", help="Show top N most-referenced symbols"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate symbol map with reference counts."""
    from invar.shell.perception import run_map

    result = run_map(path, top, json_output)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


@app.command("sig")
def sig_command(
    target: str = typer.Argument(..., help="File or file::symbol path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Extract signatures from a file or symbol."""
    from invar.shell.perception import run_sig

    result = run_sig(target, json_output)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


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


def _get_template_path(name: str) -> Path:
    """Get path to a template file."""
    import importlib.resources as resources
    return Path(str(resources.files("invar.templates").joinpath(name)))


def _copy_template(template_name: str, dest: Path, dest_name: str | None = None) -> bool:
    """Copy a template file to destination. Returns True if copied."""
    if dest_name is None:
        dest_name = template_name.replace(".template", "")
    dest_file = dest / dest_name
    if dest_file.exists():
        return False
    template_path = _get_template_path(template_name)
    if template_path.exists():
        dest_file.write_text(template_path.read_text())
        return True
    return False


def _add_config(path: Path) -> bool:
    """Add configuration to project. Returns True if config was added."""
    pyproject = path / "pyproject.toml"
    invar_toml = path / "invar.toml"

    # If pyproject.toml exists, add config there
    if pyproject.exists():
        content = pyproject.read_text()
        if "[tool.invar]" not in content:
            with pyproject.open("a") as f:
                f.write(_DEFAULT_PYPROJECT_CONFIG)
            console.print("[green]Added[/green] [tool.invar.guard] to pyproject.toml")
            return True
        return False

    # Otherwise create invar.toml
    if not invar_toml.exists():
        invar_toml.write_text(_DEFAULT_INVAR_TOML)
        console.print("[green]Created[/green] invar.toml")
        return True

    return False


def _create_directories(path: Path) -> None:
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


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Project root directory"),
    dirs: bool = typer.Option(None, "--dirs/--no-dirs", help="Create src/core and src/shell directories"),
) -> None:
    """
    Initialize Invar configuration in a project.

    Works with or without pyproject.toml:
    - If pyproject.toml exists: adds [tool.invar.guard] section
    - Otherwise: creates invar.toml

    Use --dirs to always create directories, --no-dirs to skip.
    """
    config_added = _add_config(path)

    if _copy_template("INVAR.md", path):
        console.print("[green]Created[/green] INVAR.md (Invar Protocol)")

    if _copy_template("CLAUDE.md.template", path, "CLAUDE.md"):
        console.print("[green]Created[/green] CLAUDE.md (customize for your project)")

    # Handle directory creation based on --dirs flag
    if dirs is True:
        _create_directories(path)
    elif dirs is False:
        pass  # Skip directory creation
    else:
        # Default: create directories (for backwards compatibility)
        _create_directories(path)

    invar_dir = path / ".invar"
    if not invar_dir.exists():
        invar_dir.mkdir()
        if _copy_template("context.md.template", invar_dir, "context.md"):
            console.print("[green]Created[/green] .invar/context.md (context management)")

    # Create proposals directory for protocol governance
    proposals_dir = invar_dir / "proposals"
    if not proposals_dir.exists():
        proposals_dir.mkdir()
        if _copy_template("proposal.md.template", proposals_dir, "TEMPLATE.md"):
            console.print("[green]Created[/green] .invar/proposals/TEMPLATE.md")

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")


if __name__ == "__main__":
    app()
