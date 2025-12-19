"""
CLI commands using Typer.

Shell module: handles user interaction and file I/O.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from returns.result import Failure, Result, Success

from invar import __version__
from invar.core.formatter import format_guard_agent
from invar.core.models import GuardReport, RuleConfig, Severity
from invar.core.rules import check_all_rules
from invar.core.utils import get_exit_code
from invar.shell.config import load_config
from invar.shell.fs import scan_project
from invar.shell.git import get_changed_files, is_git_repo
from invar.shell.templates import add_config, copy_template, create_directories

app = typer.Typer(
    name="invar",
    help="AI-native software engineering framework",
    add_completion=False,
)
console = Console()


def _scan_and_check(
    path: Path, config: RuleConfig, only_files: set[Path] | None = None
) -> Result[GuardReport, str]:
    """Scan project files and check against rules."""
    report = GuardReport(files_checked=0)
    for file_result in scan_project(path, only_files):
        if isinstance(file_result, Failure):
            console.print(f"[yellow]Warning:[/yellow] {file_result.failure()}")
            continue
        file_info = file_result.unwrap()
        report.files_checked += 1
        for violation in check_all_rules(file_info, config):
            report.add_violation(violation)
    return Success(report)


@app.command()
def guard(
    path: Path = typer.Argument(Path("."), help="Project root directory",
                                 exists=True, file_okay=False, dir_okay=True),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    strict_pure: bool = typer.Option(False, "--strict-pure",
                                      help="Enable strict purity checks (internal imports, impure calls)"),
    changed: bool = typer.Option(False, "--changed",
                                  help="Only check git-modified files (Phase 8.1)"),
    agent: bool = typer.Option(False, "--agent",
                                help="Output JSON with fix instructions for agents (Phase 8.2)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check project against Invar architecture rules."""
    config_result = load_config(path)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)

    config = config_result.unwrap()
    if strict_pure:
        config.strict_pure = True

    # Phase 8.1: --changed mode
    only_files: set[Path] | None = None
    if changed:
        if not is_git_repo(path):
            console.print("[red]Error:[/red] --changed requires a git repository")
            raise typer.Exit(1)
        changed_result = get_changed_files(path)
        if isinstance(changed_result, Failure):
            console.print(f"[red]Error:[/red] {changed_result.failure()}")
            raise typer.Exit(1)
        only_files = changed_result.unwrap()
        if not only_files:
            console.print("[green]No changed Python files.[/green]")
            raise typer.Exit(0)

    scan_result = _scan_and_check(path, config, only_files)
    if isinstance(scan_result, Failure):
        console.print(f"[red]Error:[/red] {scan_result.failure()}")
        raise typer.Exit(1)
    report = scan_result.unwrap()

    # Phase 8.2: --agent mode takes precedence over --json
    if agent:
        _output_agent(report)
    elif json_output:
        _output_json(report)
    else:
        _output_rich(report, config.strict_pure, changed)
    raise typer.Exit(get_exit_code(report, strict))


def _output_rich(
    report: GuardReport, strict_pure: bool = False, changed_mode: bool = False
) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    mode_info = []
    if strict_pure:
        mode_info.append("strict-pure")
    if changed_mode:
        mode_info.append("changed-only")
    if mode_info:
        console.print(f"[cyan]({', '.join(mode_info)} mode)[/cyan]")
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
                if v.severity == Severity.ERROR:
                    icon = "[red]ERROR[/red]"
                elif v.severity == Severity.WARNING:
                    icon = "[yellow]WARN[/yellow]"
                else:
                    icon = "[blue]INFO[/blue]"
                ln = f":{v.line}" if v.line else ""
                console.print(f"  {icon} {ln} {v.message}")
            console.print()

    console.print("-" * 40)
    summary = f"Files checked: {report.files_checked}\nErrors: {report.errors}\nWarnings: {report.warnings}"
    if report.infos > 0:
        summary += f"\nInfos: {report.infos}"
    console.print(summary)
    console.print(f"\n[{'green' if report.passed else 'red'}]Guard {'passed' if report.passed else 'failed'}.[/]")
    console.print("\n[dim]Note: Guard performs static analysis only. Dynamic imports and runtime behavior are not checked.[/dim]")


def _output_json(report: GuardReport) -> None:
    """Output report as JSON."""
    import json

    output = {
        "files_checked": report.files_checked,
        "errors": report.errors,
        "warnings": report.warnings,
        "infos": report.infos,
        "passed": report.passed,
        "violations": [v.model_dump() for v in report.violations],
    }
    console.print(json.dumps(output, indent=2))


def _output_agent(report: GuardReport) -> None:
    """Output report in Agent-optimized JSON format (Phase 8.2)."""
    import json

    output = format_guard_agent(report)
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
    config_result = add_config(path, console)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)
    config_added = config_result.unwrap()

    result = copy_template("INVAR.md", path)
    if isinstance(result, Success) and result.unwrap():
        console.print("[green]Created[/green] INVAR.md (Invar Protocol)")

    result = copy_template("CLAUDE.md.template", path, "CLAUDE.md")
    if isinstance(result, Success) and result.unwrap():
        console.print("[green]Created[/green] CLAUDE.md (customize for your project)")

    # Handle directory creation based on --dirs flag
    if dirs is not False:
        create_directories(path, console)

    invar_dir = path / ".invar"
    if not invar_dir.exists():
        invar_dir.mkdir()
        result = copy_template("context.md.template", invar_dir, "context.md")
        if isinstance(result, Success) and result.unwrap():
            console.print("[green]Created[/green] .invar/context.md (context management)")

    # Create proposals directory for protocol governance
    proposals_dir = invar_dir / "proposals"
    if not proposals_dir.exists():
        proposals_dir.mkdir()
        result = copy_template("proposal.md.template", proposals_dir, "TEMPLATE.md")
        if isinstance(result, Success) and result.unwrap():
            console.print("[green]Created[/green] .invar/proposals/TEMPLATE.md")

    if not config_added and not (path / "INVAR.md").exists():
        console.print("[yellow]Invar already configured.[/yellow]")


if __name__ == "__main__":
    app()
