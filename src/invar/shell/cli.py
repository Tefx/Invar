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
from invar.core.models import GuardReport, RuleConfig
from invar.core.rules import check_all_rules
from invar.core.utils import get_exit_code
from invar.shell.config import load_config
from invar.shell.fs import scan_project
from invar.shell.guard_output import output_agent, output_json, output_rich

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
        False, "--explain", help="Show detailed explanations and limitations"
    ),
    changed: bool = typer.Option(
        False, "--changed", help="Only check git-modified files"
    ),
    agent: bool = typer.Option(
        False, "--agent", help="Output JSON with fix instructions for agents"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON (simple format, no fix instructions)"
    ),
    static: bool = typer.Option(
        False, "--static", help="Static analysis only, skip doctests"
    ),
    prove: bool = typer.Option(
        False, "--prove", help="Add symbolic verification with CrossHair"
    ),
) -> None:
    """Check project against Invar architecture rules.

    Smart Guard: Automatically runs doctests after static analysis.
    Use --static for static-only, --prove for symbolic verification.
    """
    from invar.shell.guard_helpers import (
        collect_files_to_check,
        handle_changed_mode,
        output_verification_status,
        run_crosshair_phase,
        run_doctests_phase,
    )
    from invar.shell.testing import VerificationLevel

    # Load and configure
    config_result = load_config(path)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)

    config = config_result.unwrap()
    if no_strict_pure:
        config.strict_pure = False
    if pedantic:
        config.severity_overrides = {}

    # Handle --changed mode
    only_files: set[Path] | None = None
    checked_files: list[Path] = []
    if changed:
        changed_result = handle_changed_mode(path)
        if isinstance(changed_result, Failure):
            if changed_result.failure() == "NO_CHANGES":
                console.print("[green]No changed Python files.[/green]")
                raise typer.Exit(0)
            console.print(f"[red]Error:[/red] {changed_result.failure()}")
            raise typer.Exit(1)
        only_files, checked_files = changed_result.unwrap()

    # Run static analysis
    scan_result = _scan_and_check(path, config, only_files)
    if isinstance(scan_result, Failure):
        console.print(f"[red]Error:[/red] {scan_result.failure()}")
        raise typer.Exit(1)
    report = scan_result.unwrap()

    # Determine output mode
    use_agent_output, use_json_output = _determine_output_mode(
        json_output, agent
    )

    # Determine verification level (DX-15: auto-select based on context)
    verification_level = _determine_verification_level(
        prove, static, changed_mode=changed, changed_files_count=len(checked_files)
    )
    level_name = _get_level_name(verification_level)

    # Show verification level (human mode)
    if not use_agent_output and not use_json_output:
        _show_verification_level(verification_level)

    # Run verification phases
    static_exit_code = get_exit_code(report, strict)
    doctest_passed, doctest_output = True, ""
    crosshair_passed, crosshair_output = True, {}

    if verification_level >= VerificationLevel.STANDARD and static_exit_code == 0:
        checked_files = collect_files_to_check(path, checked_files)
        doctest_passed, doctest_output = run_doctests_phase(checked_files, explain)

    if verification_level >= VerificationLevel.PROVE:
        crosshair_passed, crosshair_output = run_crosshair_phase(
            path, checked_files, doctest_passed, static_exit_code,
            changed_mode=changed,  # DX-13: Only git-incremental when --changed
        )

    # Output results
    if use_agent_output:
        output_agent(report, doctest_passed, doctest_output, crosshair_output, level_name)
    elif use_json_output:
        output_json(report)
    else:
        output_rich(report, config.strict_pure, changed, pedantic, explain)
        output_verification_status(
            verification_level, static_exit_code, doctest_passed,
            doctest_output, crosshair_output, explain
        )

    # Exit with combined status
    all_passed = doctest_passed and crosshair_passed
    final_exit = static_exit_code if all_passed else 1
    raise typer.Exit(final_exit)


def _determine_output_mode(json_output: bool, agent: bool) -> tuple[bool, bool]:
    """Determine output mode based on flags and context."""
    if json_output:
        return False, True
    if agent or _detect_agent_mode():
        return True, False
    return False, False


def _determine_verification_level(
    prove: bool, static: bool, changed_mode: bool = False, changed_files_count: int = 0
):
    """
    Determine verification level from flags and context.

    DX-15: Auto-select PROVE when appropriate:
    - CI environment always uses PROVE
    - Small changes (<=3 files) in --changed mode use PROVE
    - Otherwise defaults to STANDARD
    """
    import os

    from invar.shell.testing import VerificationLevel

    # Explicit flags take precedence
    if prove:
        return VerificationLevel.PROVE
    if static:
        return VerificationLevel.STATIC

    # DX-15: Auto-detect appropriate level
    # CI environment always uses PROVE
    if os.getenv("CI"):
        return VerificationLevel.PROVE

    # In --changed mode with few files, use PROVE (it's fast enough)
    if changed_mode and 0 < changed_files_count <= 3:
        return VerificationLevel.PROVE

    # Otherwise use STANDARD level
    return VerificationLevel.STANDARD


def _get_level_name(verification_level) -> str:
    """Get string name for verification level."""
    from invar.shell.testing import VerificationLevel

    return {
        VerificationLevel.STATIC: "static",
        VerificationLevel.STANDARD: "standard",
        VerificationLevel.PROVE: "prove",
    }[verification_level]


def _show_verification_level(verification_level) -> None:
    """Show verification level in human-readable format."""
    from invar.shell.testing import VerificationLevel

    labels = {
        VerificationLevel.STATIC: "[yellow]--static[/yellow] (static only, doctests skipped)",
        VerificationLevel.STANDARD: "default (static + doctests)",
        VerificationLevel.PROVE: "--prove (static + doctests + CrossHair)",
    }
    console.print(f"[dim]Verification: {labels[verification_level]}[/dim]")


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

    Shows what each rule detects and its limitations.
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


# Import commands from separate modules to reduce file size
from invar.shell.init_cmd import init
from invar.shell.test_cmd import test, verify
from invar.shell.update_cmd import update

app.command()(init)
app.command()(update)
app.command()(test)
app.command()(verify)


if __name__ == "__main__":
    app()
