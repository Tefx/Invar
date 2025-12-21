"""
CLI commands using Typer.

Shell module: handles user interaction and file I/O.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from returns.result import Failure, Result, Success
from rich.console import Console
from rich.table import Table


def _detect_agent_mode() -> bool:
    """Detect agent context: INVAR_MODE=agent OR non-TTY (pipe/redirect)."""
    import sys
    return os.getenv("INVAR_MODE") == "agent" or not sys.stdout.isatty()


from invar import __version__
from invar.core.formatter import format_guard_agent
from invar.core.models import GuardReport, RuleConfig, Severity
from invar.core.rules import check_all_rules
from invar.core.utils import get_exit_code
from invar.shell.config import load_config
from invar.shell.fs import scan_project
from invar.shell.git import get_changed_files, is_git_repo

app = typer.Typer(
    name="invar",
    help="AI-native software engineering framework",
    add_completion=False,
)
console = Console()


def _count_core_functions(file_info) -> tuple[int, int]:
    """Count functions and functions with contracts in a Core file (P24)."""
    from invar.core.models import SymbolKind

    if not file_info.is_core:
        return (0, 0)

    total = 0
    with_contracts = 0
    for sym in file_info.symbols:
        if sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            total += 1
            if sym.contracts:
                with_contracts += 1
    return (total, with_contracts)


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
        # P24: Track contract coverage for Core files
        total, with_contracts = _count_core_functions(file_info)
        report.update_coverage(total, with_contracts)
        for violation in check_all_rules(file_info, config):
            report.add_violation(violation)
    return Success(report)


@app.command()
def guard(
    path: Path = typer.Argument(
        Path(), help="Project root directory", exists=True, file_okay=False, dir_okay=True
    ),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    no_strict_pure: bool = typer.Option(
        False, "--no-strict-pure", help="Disable purity checks (internal imports, impure calls)"
    ),
    pedantic: bool = typer.Option(
        False, "--pedantic", help="Show all violations including off-by-default rules"
    ),
    explain: bool = typer.Option(
        False, "--explain", help="Show detailed explanations and limitations (Phase 9.2 P5)"
    ),
    changed: bool = typer.Option(
        False, "--changed", help="Only check git-modified files (Phase 8.1)"
    ),
    agent: bool = typer.Option(
        False, "--agent", help="Output JSON with fix instructions for agents (Phase 8.2)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    # DX-06: Smart Guard flags
    quick: bool = typer.Option(
        False, "--quick", help="Static analysis only, skip doctests (DX-06)"
    ),
    prove: bool = typer.Option(
        False, "--prove", help="Force symbolic verification with CrossHair (DX-06)"
    ),
) -> None:
    """Check project against Invar architecture rules.

    Smart Guard (DX-06): Automatically runs doctests after static analysis.
    Use --quick for static-only, --prove for symbolic verification.
    """
    from invar.shell.testing import (
        VerificationLevel,
        detect_verification_context,
        run_crosshair_on_files,
        run_doctests_on_files,
    )

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
    checked_files: list[Path] = []
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
        checked_files = list(only_files)

    scan_result = _scan_and_check(path, config, only_files)
    if isinstance(scan_result, Failure):
        console.print(f"[red]Error:[/red] {scan_result.failure()}")
        raise typer.Exit(1)
    report = scan_result.unwrap()

    # Phase 9 P11: Auto-detect agent mode from environment
    use_agent_output = agent or _detect_agent_mode()

    # DX-06: Smart Guard - determine verification level
    if quick:
        verification_level = VerificationLevel.STATIC
    elif prove:
        verification_level = VerificationLevel.PROVE
    else:
        verification_level = detect_verification_context()

    # DX-06: Run doctests if not --quick and static analysis passed
    doctest_passed = True
    doctest_output = ""
    crosshair_passed = True
    crosshair_output: dict = {}
    static_exit_code = get_exit_code(report, strict)

    if verification_level >= VerificationLevel.STANDARD and static_exit_code == 0:
        # Collect files to test
        if not checked_files:
            # Scan for Python files in core/shell paths
            for core_path in config.core_paths:
                full_path = path / core_path
                if full_path.exists():
                    checked_files.extend(full_path.rglob("*.py"))
            for shell_path in config.shell_paths:
                full_path = path / shell_path
                if full_path.exists():
                    checked_files.extend(full_path.rglob("*.py"))

        if checked_files:
            doctest_result = run_doctests_on_files(checked_files, verbose=explain)
            if isinstance(doctest_result, Success):
                result_data = doctest_result.unwrap()
                doctest_passed = result_data.get("status") in ("passed", "skipped")
                doctest_output = result_data.get("stdout", "")
            else:
                doctest_passed = False
                doctest_output = doctest_result.failure()

    # DX-06: Run CrossHair if --prove and doctests passed
    if verification_level >= VerificationLevel.PROVE and doctest_passed and static_exit_code == 0:
        if checked_files:
            # Only verify Core files (pure logic)
            core_files = [f for f in checked_files if "core" in str(f)]
            if core_files:
                crosshair_result = run_crosshair_on_files(core_files)
                if isinstance(crosshair_result, Success):
                    crosshair_output = crosshair_result.unwrap()
                    crosshair_passed = crosshair_output.get("status") in ("verified", "skipped")
                else:
                    crosshair_passed = False
                    crosshair_output = {"error": crosshair_result.failure()}

    # Output results
    if use_agent_output:
        _output_agent(report, doctest_passed, doctest_output, crosshair_output)
    elif json_output:
        _output_json(report)
    else:
        _output_rich(report, config.strict_pure, changed, pedantic, explain)
        # DX-06: Show doctest results
        if verification_level >= VerificationLevel.STANDARD:
            if static_exit_code == 0:
                if doctest_passed:
                    console.print("[green]✓ Doctests passed[/green]")
                else:
                    console.print("[red]✗ Doctests failed[/red]")
                    if doctest_output and explain:
                        console.print(doctest_output)
            else:
                console.print("[dim]⊘ Doctests skipped (static errors)[/dim]")
        # DX-06: Show CrossHair results
        if verification_level >= VerificationLevel.PROVE:
            if static_exit_code == 0 and doctest_passed:
                status = crosshair_output.get("status", "unknown")
                if status == "verified":
                    console.print("[green]✓ CrossHair verified[/green]")
                elif status == "skipped":
                    reason = crosshair_output.get("reason", "no files")
                    console.print(f"[dim]⊘ CrossHair skipped ({reason})[/dim]")
                else:
                    console.print("[yellow]! CrossHair found counterexamples[/yellow]")
                    for ce in crosshair_output.get("counterexamples", [])[:5]:
                        console.print(f"  {ce}")
            else:
                console.print("[dim]⊘ CrossHair skipped (prior failures)[/dim]")

    # Exit with combined status
    all_passed = doctest_passed and crosshair_passed
    final_exit = static_exit_code if all_passed else 1
    raise typer.Exit(final_exit)


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
        console.print(
            f"  [dim]INSPECT: {ctx.lines} lines ({ctx.percentage}% of limit), "
            f"{ctx.functions_with_contracts}/{ctx.functions_total} functions with contracts[/dim]"
        )
        if ctx.contract_examples:
            patterns = ", ".join(ctx.contract_examples[:2])
            if len(patterns) > 60:
                patterns = patterns[:57] + "..."
            console.print(f"  [dim]Patterns: {patterns}[/dim]")
    except Exception:
        pass  # Silently ignore errors in context display


def _output_rich(
    report: GuardReport,
    strict_pure: bool = False,
    changed_mode: bool = False,
    pedantic_mode: bool = False,
    explain_mode: bool = False,
) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    mode_info = [m for m, c in [("strict-pure", strict_pure), ("changed-only", changed_mode),
                                ("pedantic", pedantic_mode), ("explain", explain_mode)] if c]
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
                # Show violation's suggestion if present (includes P25 extraction hints)
                if v.suggestion:
                    # Handle multi-line suggestions (P25)
                    for line in v.suggestion.split("\n"):
                        console.print(f"    [dim cyan]→ {line}[/dim cyan]")
                else:
                    # Phase 9.2 P5: Fallback to hints from RULE_META
                    meta = get_rule_meta(v.rule)
                    if meta:
                        console.print(f"    [dim cyan]→ {meta.hint}[/dim cyan]")
                        # --explain: show detailed information
                        if explain_mode:
                            console.print(f"    [dim]Detects: {meta.detects}[/dim]")
                            if meta.cannot_detect:
                                console.print(
                                    f"    [dim]Cannot detect: {', '.join(meta.cannot_detect)}[/dim]"
                                )
            console.print()

    console.print("-" * 40)
    summary = f"Files checked: {report.files_checked}\nErrors: {report.errors}\nWarnings: {report.warnings}"
    if report.infos > 0:
        summary += f"\nInfos: {report.infos}"
    console.print(summary)

    # P24: Contract coverage statistics (only show if core files exist)
    if report.core_functions_total > 0:
        pct = report.contract_coverage_pct
        console.print(
            f"\n[bold]Contract coverage:[/bold] {pct}% ({report.core_functions_with_contracts}/{report.core_functions_total} functions)"
        )
        issues = report.contract_issue_counts
        issue_parts = []
        if issues["tautology"] > 0:
            issue_parts.append(f"{issues['tautology']} tautology")
        if issues["empty"] > 0:
            issue_parts.append(f"{issues['empty']} empty")
        if issues["partial"] > 0:
            issue_parts.append(f"{issues['partial']} partial")
        if issues["type_only"] > 0:
            issue_parts.append(f"{issues['type_only']} type-check only")
        if issue_parts:
            console.print(f"[dim]Issues: {', '.join(issue_parts)}[/dim]")

    # Code Health display (only when guard passes)
    if report.passed and report.files_checked > 0:
        # Calculate health: 100% for 0 warnings, decreases by 5% per warning, min 50%
        health = max(50, 100 - report.warnings * 5)
        bar_filled = health // 5  # 20 chars total
        bar_empty = 20 - bar_filled
        bar = "█" * bar_filled + "░" * bar_empty

        if report.warnings == 0:
            health_color = "green"
            health_label = "Excellent"
        elif report.warnings <= 2:
            health_color = "green"
            health_label = "Good"
        elif report.warnings <= 5:
            health_color = "yellow"
            health_label = "Fair"
        else:
            health_color = "yellow"
            health_label = "Needs attention"

        console.print(
            f"\n[bold]Code Health:[/bold] [{health_color}]{health}%[/{health_color}] {bar} ({health_label})"
        )

        # Tip for fixing warnings
        if report.warnings > 0:
            console.print(
                "[dim]💡 Fix warnings in files you modified to improve code health.[/dim]"
            )

    console.print(
        f"\n[{'green' if report.passed else 'red'}]Guard {'passed' if report.passed else 'failed'}.[/]"
    )
    console.print(
        "\n[dim]Note: Guard performs static analysis only. Dynamic imports and runtime behavior are not checked.[/dim]"
    )


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


def _output_agent(
    report: GuardReport,
    doctest_passed: bool = True,
    doctest_output: str = "",
    crosshair_output: dict | None = None,
) -> None:
    """Output report in Agent-optimized JSON format (Phase 8.2 + DX-06)."""
    import json

    output = format_guard_agent(report)
    # DX-06: Add doctest results to agent output
    output["doctest"] = {
        "passed": doctest_passed,
        "output": doctest_output if not doctest_passed else "",
    }
    # DX-06: Add CrossHair results if available
    if crosshair_output:
        output["crosshair"] = crosshair_output
    console.print(json.dumps(output, indent=2))


@app.command()
def version() -> None:
    """Show Invar version."""
    console.print(f"invar {__version__}")


@app.command("map")
def map_command(
    path: Path = typer.Argument(Path(), help="Project root directory"),
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
    category: str = typer.Option(
        None, "--category", "-c", help="Filter by category (size, contracts, purity, shell, docs)"
    ),
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
            sev_style = {"error": "red", "warning": "yellow", "info": "blue"}.get(
                r.severity.value, ""
            )
            table.add_row(
                r.name,
                f"[{sev_style}]{r.severity.value.upper()}[/{sev_style}]",
                r.category.value,
                r.detects[:50] + "..." if len(r.detects) > 50 else r.detects,
                r.hint[:40] + "..." if len(r.hint) > 40 else r.hint,
            )

        console.print(table)
        console.print(f"\n[dim]{len(rules_list)} rules total. Use --json for full details.[/dim]")


# Import init from separate module to reduce file size
from invar.shell.init_cmd import init

app.command()(init)


@app.command()
def test(
    target: str = typer.Argument(..., help="File to test"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run property-based tests using Hypothesis via deal.cases."""
    from invar.shell.testing import run_test

    use_json = json_output or _detect_agent_mode()
    result = run_test(target, use_json, verbose)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


@app.command()
def verify(
    target: str = typer.Argument(..., help="File to verify"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout per function (seconds)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run symbolic verification using CrossHair."""
    from invar.shell.testing import run_verify

    use_json = json_output or _detect_agent_mode()
    result = run_verify(target, use_json, timeout)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
