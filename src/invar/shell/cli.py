"""
CLI commands using Typer.

Shell module: handles user interaction and file I/O.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from returns.result import Failure, Result, Success


def _detect_agent_mode() -> bool:
    """
    Detect if running in agent context (Phase 9 P11).

    Returns True if INVAR_MODE=agent environment variable is set.
    This allows automatic JSON output for all commands when used by AI agents.
    """
    return os.getenv("INVAR_MODE") == "agent"

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
    no_strict_pure: bool = typer.Option(False, "--no-strict-pure",
                                         help="Disable purity checks (internal imports, impure calls)"),
    pedantic: bool = typer.Option(False, "--pedantic",
                                   help="Show all violations including off-by-default rules"),
    explain: bool = typer.Option(False, "--explain",
                                  help="Show detailed explanations and limitations (Phase 9.2 P5)"),
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
    if no_strict_pure:
        config.strict_pure = False
    # Phase 9 P2: --pedantic shows all rules including off-by-default
    if pedantic:
        config.severity_overrides = {}

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

    # Phase 9 P11: Auto-detect agent mode from environment
    use_agent_output = agent or _detect_agent_mode()

    if use_agent_output:
        _output_agent(report)
    elif json_output:
        _output_json(report)
    else:
        _output_rich(report, config.strict_pure, changed, pedantic, explain)
    raise typer.Exit(get_exit_code(report, strict))


def _show_file_context(file_path: str) -> None:
    """
    Show INSPECT section for a file (Phase 9.2 P14).

    Displays file status and contract patterns to help agents understand context.
    """
    from pathlib import Path
    from invar.core.inspect import analyze_file_context

    try:
        path = Path(file_path)
        if not path.exists():
            return

        source = path.read_text()
        ctx = analyze_file_context(source, file_path, max_lines=500)

        # Show compact INSPECT section
        console.print(f"  [dim]INSPECT: {ctx.lines} lines ({ctx.percentage}% of limit), "
                      f"{ctx.functions_with_contracts}/{ctx.functions_total} functions with contracts[/dim]")
        if ctx.contract_examples:
            patterns = ", ".join(ctx.contract_examples[:2])
            if len(patterns) > 60:
                patterns = patterns[:57] + "..."
            console.print(f"  [dim]Patterns: {patterns}[/dim]")
    except Exception:
        pass  # Silently ignore errors in context display


def _output_rich(
    report: GuardReport, strict_pure: bool = False, changed_mode: bool = False,
    pedantic_mode: bool = False, explain_mode: bool = False
) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    mode_info = []
    if strict_pure:
        mode_info.append("strict-pure")
    if changed_mode:
        mode_info.append("changed-only")
    if pedantic_mode:
        mode_info.append("pedantic")
    if explain_mode:
        mode_info.append("explain")
    if mode_info:
        console.print(f"[cyan]({', '.join(mode_info)} mode)[/cyan]")
    console.print()

    if not report.violations:
        console.print("[green]No violations found.[/green]")
    else:
        from invar.core.rule_meta import get_rule_meta

        by_file: dict[str, list] = {}
        for v in report.violations:
            by_file.setdefault(v.file, []).append(v)
        for fp, vs in sorted(by_file.items()):
            console.print(f"[bold]{fp}[/bold]")
            # Phase 9.2 P14: Show INSPECT section in --changed mode
            if changed_mode:
                _show_file_context(fp)
            for v in vs:
                if v.severity == Severity.ERROR:
                    icon = "[red]ERROR[/red]"
                elif v.severity == Severity.WARNING:
                    icon = "[yellow]WARN[/yellow]"
                else:
                    icon = "[blue]INFO[/blue]"
                ln = f":{v.line}" if v.line else ""
                console.print(f"  {icon} {ln} {v.message}")
                # Phase 9.2 P5: Always-on hints from RULE_META
                meta = get_rule_meta(v.rule)
                if meta:
                    console.print(f"    [dim cyan]→ {meta.hint}[/dim cyan]")
                    # --explain: show detailed information
                    if explain_mode:
                        console.print(f"    [dim]Detects: {meta.detects}[/dim]")
                        if meta.cannot_detect:
                            console.print(f"    [dim]Cannot detect: {', '.join(meta.cannot_detect)}[/dim]")
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

    # Phase 9 P11: Auto-detect agent mode
    use_json = json_output or _detect_agent_mode()
    result = run_map(path, top, use_json)
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

    # Phase 9 P11: Auto-detect agent mode
    use_json = json_output or _detect_agent_mode()
    result = run_sig(target, use_json)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


@app.command()
def rules(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    category: str = typer.Option(None, "--category", "-c",
                                  help="Filter by category (size, contracts, purity, shell, docs)"),
) -> None:
    """
    List all Guard rules with their metadata.

    Phase 9.2 P3: Shows what each rule detects and its limitations.
    """
    import json as json_lib
    from invar.core.rule_meta import RULE_META, RuleCategory, get_rules_by_category

    # Phase 9 P11: Auto-detect agent mode
    use_json = json_output or _detect_agent_mode()

    # Filter by category if specified
    if category:
        try:
            cat = RuleCategory(category.lower())
            rules_list = get_rules_by_category(cat)
        except ValueError:
            valid = ", ".join(c.value for c in RuleCategory)
            console.print(f"[red]Error:[/red] Invalid category '{category}'. Valid: {valid}")
            raise typer.Exit(1)
    else:
        rules_list = list(RULE_META.values())

    if use_json:
        # JSON output for agents
        data = {
            "rules": [
                {
                    "name": r.name,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "detects": r.detects,
                    "cannot_detect": list(r.cannot_detect),
                    "hint": r.hint,
                }
                for r in rules_list
            ]
        }
        console.print(json_lib.dumps(data, indent=2))
    else:
        # Rich table output for humans
        table = Table(title="Invar Guard Rules")
        table.add_column("Rule", style="cyan")
        table.add_column("Severity", style="yellow")
        table.add_column("Category")
        table.add_column("Detects")
        table.add_column("Hint", style="green")

        for r in rules_list:
            sev_style = {"error": "red", "warning": "yellow", "info": "blue"}.get(r.severity.value, "")
            table.add_row(
                r.name,
                f"[{sev_style}]{r.severity.value.upper()}[/{sev_style}]",
                r.category.value,
                r.detects[:50] + "..." if len(r.detects) > 50 else r.detects,
                r.hint[:40] + "..." if len(r.hint) > 40 else r.hint,
            )

        console.print(table)
        console.print(f"\n[dim]{len(rules_list)} rules total. Use --json for full details.[/dim]")


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
