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
from invar.shell.guard_output import output_agent, output_rich

app = typer.Typer(
    name="invar",
    help="AI-native software engineering framework",
    add_completion=False,
)
console = Console()


# @shell_orchestration: Statistics helper for CLI guard output
# @shell_complexity: Iterates symbols checking kind and contracts (4 branches minimal)
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


# @shell_complexity: Core orchestration - iterates files, handles failures, aggregates results
def _scan_and_check(
    path: Path, config: RuleConfig, only_files: set[Path] | None = None
) -> Result[GuardReport, str]:
    """Scan project files and check against rules."""
    from invar.core.shell_architecture import check_complexity_debt

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

    # DX-22: Check project-level complexity debt (Fix-or-Explain enforcement)
    for debt_violation in check_complexity_debt(
        report.violations, config.shell_complexity_debt_limit
    ):
        report.add_violation(debt_violation)

    return Success(report)


# @invar:allow entry_point_too_thick: Main CLI entry point, orchestrates all verification phases
@app.command()
def guard(
    path: Path = typer.Argument(
        Path(), help="Project root directory", exists=True, file_okay=False, dir_okay=True
    ),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    changed: bool = typer.Option(
        False, "--changed", help="Only check git-modified files"
    ),
    static: bool = typer.Option(
        False, "--static", help="Static analysis only, skip all runtime tests"
    ),
    human: bool = typer.Option(
        False, "--human", help="Force human-readable output (for testing/debugging)"
    ),
    # DX-26: Deprecated flags kept for backward compatibility
    no_strict_pure: bool = typer.Option(
        False, "--no-strict-pure", hidden=True, help="[Deprecated] Disable purity checks"
    ),
    pedantic: bool = typer.Option(
        False, "--pedantic", hidden=True, help="[Deprecated] Show off-by-default rules"
    ),
    explain: bool = typer.Option(
        False, "--explain", hidden=True, help="[Deprecated] Show detailed explanations"
    ),
    agent: bool = typer.Option(
        False, "--agent", help="Force JSON output (for inspecting agent format)"
    ),
    json_output: bool = typer.Option(
        False, "--json", hidden=True, help="[Deprecated] Use TTY auto-detection instead"
    ),
) -> None:
    """Check project against Invar architecture rules.

    Smart Guard: Runs static analysis + doctests + CrossHair + Hypothesis by default.
    Use --static for quick static-only checks (~0.5s vs ~5s full).
    """
    from invar.shell.guard_helpers import (
        collect_files_to_check,
        handle_changed_mode,
        output_verification_status,
        run_crosshair_phase,
        run_doctests_phase,
        run_property_tests_phase,
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

    # DX-26: Simplified output mode (TTY auto-detect + --human override)
    use_agent_output = _determine_output_mode(human, agent, json_output)

    # DX-19: Simplified to 2 levels (STATIC or STANDARD)
    verification_level = VerificationLevel.STATIC if static else VerificationLevel.STANDARD
    level_name = "STATIC" if static else "STANDARD"

    # Show verification level (human mode)
    if not use_agent_output:
        _show_verification_level(verification_level)

    # Run verification phases
    static_exit_code = get_exit_code(report, strict)
    doctest_passed, doctest_output = True, ""
    crosshair_passed, crosshair_output = True, {}
    property_passed, property_output = True, {}

    # DX-19: STANDARD runs all verification phases
    if verification_level == VerificationLevel.STANDARD and static_exit_code == 0:
        checked_files = collect_files_to_check(path, checked_files)

        # Phase 1: Doctests
        doctest_passed, doctest_output = run_doctests_phase(checked_files, explain)

        # Phase 2: CrossHair symbolic verification
        crosshair_passed, crosshair_output = run_crosshair_phase(
            path, checked_files, doctest_passed, static_exit_code,
            changed_mode=changed,
        )

        # Phase 3: Hypothesis property tests
        property_passed, property_output = run_property_tests_phase(
            checked_files, doctest_passed, static_exit_code
        )

    # DX-26: Unified output (agent JSON or human Rich)
    if use_agent_output:
        output_agent(
            report, strict, doctest_passed, doctest_output, crosshair_output, level_name,
            property_output=property_output,
        )
    else:
        output_rich(report, config.strict_pure, changed, pedantic, explain, static)
        output_verification_status(
            verification_level, static_exit_code, doctest_passed,
            doctest_output, crosshair_output, explain,
            property_output=property_output,
            strict=strict,
        )

    # Exit with combined status
    all_passed = doctest_passed and crosshair_passed and property_passed
    final_exit = static_exit_code if all_passed else 1
    raise typer.Exit(final_exit)


# @shell_orchestration: Output mode decision helper for CLI
def _determine_output_mode(human: bool, agent: bool = False, json_output: bool = False) -> bool:
    """Determine if agent JSON output should be used (DX-26).

    DX-26: TTY auto-detection with --human override.
    - --human flag → human output (for testing/debugging)
    - TTY (terminal) → human output
    - Non-TTY (pipe/redirect) → agent JSON output
    - Deprecated --agent/--json flags → still work for backward compat
    """
    # --human flag always forces human output
    if human:
        return False  # use_agent = False

    # Deprecated flags (backward compat)
    if json_output or agent:
        return True  # use_agent = True

    # TTY auto-detection
    return _detect_agent_mode()  # Returns True if non-TTY


def _show_verification_level(verification_level) -> None:
    """Show verification level in human-readable format.

    DX-19: Simplified to 2 levels.
    """
    from invar.shell.testing import VerificationLevel

    labels = {
        VerificationLevel.STATIC: "[yellow]--static[/yellow] (static only)",
        VerificationLevel.STANDARD: "default (static + doctests + CrossHair + Hypothesis)",
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


# @invar:allow entry_point_too_thick: Rules display with filtering and dual output modes
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
from invar.shell.mutate_cmd import mutate  # DX-28
from invar.shell.test_cmd import test, verify
from invar.shell.update_cmd import update

app.command()(init)
app.command()(update)
app.command()(test)
app.command()(verify)
app.command()(mutate)  # DX-28: Mutation testing


if __name__ == "__main__":
    app()
