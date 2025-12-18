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
from invar.core.models import GuardReport, Severity
from invar.core.rules import RuleConfig, check_all_rules
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
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check project against Invar architecture rules."""
    config_result = load_config(path)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)

    report = _scan_and_check(path, config_result.unwrap())
    _output_json(report) if json_output else _output_rich(report)
    raise typer.Exit(_get_exit_code(report, strict))


def _output_rich(report: GuardReport) -> None:
    """Output report using Rich formatting."""
    console.print()
    console.print("[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    console.print()

    if not report.violations:
        console.print("[green]No violations found.[/green]")
    else:
        # Group violations by file
        by_file: dict[str, list[tuple[str, str, int | None, str]]] = {}
        for v in report.violations:
            if v.file not in by_file:
                by_file[v.file] = []
            icon = "[red]ERROR[/red]" if v.severity == Severity.ERROR else "[yellow]WARN[/yellow]"
            by_file[v.file].append((icon, v.rule, v.line, v.message))

        for file_path, violations in sorted(by_file.items()):
            console.print(f"[bold]{file_path}[/bold]")
            for icon, rule, line, message in violations:
                line_str = f":{line}" if line else ""
                console.print(f"  {icon} [{rule}]{line_str} {message}")
            console.print()

    # Summary
    console.print("-" * 40)
    console.print(f"Files checked: {report.files_checked}")
    console.print(f"Errors: {report.errors}")
    console.print(f"Warnings: {report.warnings}")

    if report.passed:
        console.print("\n[green]Guard passed.[/green]")
    else:
        console.print("\n[red]Guard failed.[/red]")

    console.print()
    console.print(
        "[dim]Note: Guard performs static analysis only. "
        "Dynamic imports and runtime behavior are not checked.[/dim]"
    )


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


_DEFAULT_INVAR_CONFIG = '''\n# Invar Configuration
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


@app.command()
def init(path: Path = typer.Argument(Path("."), help="Project root directory")) -> None:
    """Initialize Invar configuration in a project."""
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        console.print("[red]Error:[/red] pyproject.toml not found")
        raise typer.Exit(1)

    config_added = False
    if "[tool.invar]" not in pyproject.read_text():
        with pyproject.open("a") as f:
            f.write(_DEFAULT_INVAR_CONFIG)
        console.print("[green]Added[/green] [tool.invar.guard] to pyproject.toml")
        config_added = True

    if _copy_template("INVAR.md", path):
        console.print("[green]Created[/green] INVAR.md (Invar Protocol)")

    if _copy_template("CLAUDE.md.template", path, "CLAUDE.md"):
        console.print("[green]Created[/green] CLAUDE.md (customize for your project)")

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

    invar_dir = path / ".invar"
    if not invar_dir.exists():
        invar_dir.mkdir()
        if _copy_template("context.md.template", invar_dir, "context.md"):
            console.print("[green]Created[/green] .invar/context.md (context management)")

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")


if __name__ == "__main__":
    app()
