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
from invar.shell.config import get_path_classification, load_config
from invar.shell.fs import scan_project
from invar.shell.git import get_changed_files, is_git_repo
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
    # Smart Guard flags - --static is primary, --quick is hidden alias
    static: bool = typer.Option(
        False, "--static", help="Static analysis only, skip doctests"
    ),
    quick: bool = typer.Option(
        False, "--quick", hidden=True, help="Alias for --static"
    ),
    prove: bool = typer.Option(
        False, "--prove", help="Add symbolic verification with CrossHair"
    ),
) -> None:
    """Check project against Invar architecture rules.

    Smart Guard: Automatically runs doctests after static analysis.
    Use --static for static-only, --prove for symbolic verification.
    """
    from invar.shell.prove_cache import ProveCache
    from invar.shell.testing import (
        VerificationLevel,
        detect_verification_context,
        get_files_to_prove,
        run_crosshair_parallel,
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

    # Output mode: explicit flags take precedence over auto-detection
    # Priority: --json (simple) > --agent (full) > auto-detect
    if json_output:
        use_agent_output = False
        use_json_output = True
    elif agent:
        use_agent_output = True
        use_json_output = False
    elif _detect_agent_mode():
        use_agent_output = True
        use_json_output = False
    else:
        use_agent_output = False
        use_json_output = False

    # Smart Guard - determine verification level
    # Note: --prove takes precedence (explicit > implicit, higher tier > lower)
    use_static = static or quick  # --quick is hidden alias for --static
    if prove:
        verification_level = VerificationLevel.PROVE
    elif use_static:
        verification_level = VerificationLevel.STATIC
    else:
        verification_level = detect_verification_context()

    # DX-09: Verification level labels (used for both human and agent output)
    level_labels = {
        VerificationLevel.STATIC: "static",
        VerificationLevel.STANDARD: "standard",
        VerificationLevel.PROVE: "prove",
    }
    level_name = level_labels[verification_level]

    # Show verification level (human mode)
    if not use_agent_output and not use_json_output:
        human_labels = {
            VerificationLevel.STATIC: "[yellow]--static[/yellow] (static only, doctests skipped)",
            VerificationLevel.STANDARD: "default (static + doctests)",
            VerificationLevel.PROVE: "--prove (static + doctests + CrossHair)",
        }
        console.print(f"[dim]Verification: {human_labels[verification_level]}[/dim]")

    # DX-06: Run doctests if not --quick and static analysis passed
    doctest_passed = True
    doctest_output = ""
    crosshair_passed = True
    crosshair_output: dict = {}
    static_exit_code = get_exit_code(report, strict)

    if verification_level >= VerificationLevel.STANDARD and static_exit_code == 0:
        # Collect files to test
        if not checked_files:
            # DX-07: Get core/shell paths from config (not RuleConfig)
            path_result = get_path_classification(path)
            if isinstance(path_result, Success):
                core_paths, shell_paths = path_result.unwrap()
            else:
                core_paths, shell_paths = ["src/core"], ["src/shell"]
            # Scan for Python files in core/shell paths
            for core_path in core_paths:
                full_path = path / core_path
                if full_path.exists():
                    checked_files.extend(full_path.rglob("*.py"))
            for shell_path in shell_paths:
                full_path = path / shell_path
                if full_path.exists():
                    checked_files.extend(full_path.rglob("*.py"))
            # DX-07: Fallback - if no configured paths found, scan path directly
            if not checked_files and path.exists():
                checked_files.extend(path.rglob("*.py"))

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
    # DX-13: Uses incremental mode, parallel execution, and caching
    if verification_level >= VerificationLevel.PROVE:
        if doctest_passed and static_exit_code == 0:
            if checked_files:
                # Only verify Core files (pure logic)
                core_files = [f for f in checked_files if "core" in str(f)]
                if core_files:
                    # DX-13: Automatic incremental mode - only verify changed files
                    files_to_prove = get_files_to_prove(
                        path, core_files, changed_only=True
                    )

                    if not files_to_prove:
                        crosshair_output = {
                            "status": "verified",
                            "reason": "no changes to verify",
                            "files_verified": 0,
                            "files_cached": len(core_files),
                        }
                    else:
                        # DX-13: Create cache for verification results
                        cache = ProveCache(path / ".invar" / "cache" / "prove")

                        # DX-13: Run parallel verification with caching
                        crosshair_result = run_crosshair_parallel(
                            files_to_prove,
                            max_iterations=5,  # Fast mode
                            max_workers=None,  # Auto-detect
                            cache=cache,
                        )
                        if isinstance(crosshair_result, Success):
                            crosshair_output = crosshair_result.unwrap()
                            crosshair_passed = crosshair_output.get("status") in (
                                "verified",
                                "skipped",
                            )
                        else:
                            crosshair_passed = False
                            crosshair_output = {
                                "status": "error",
                                "error": crosshair_result.failure(),
                            }
                else:
                    crosshair_output = {"status": "skipped", "reason": "no core files found"}
            else:
                crosshair_output = {"status": "skipped", "reason": "no files to verify"}
        else:
            crosshair_output = {"status": "skipped", "reason": "prior failures"}

    # Output results
    if use_agent_output:
        output_agent(report, doctest_passed, doctest_output, crosshair_output, level_name)
    elif use_json_output:
        output_json(report)
    else:
        output_rich(report, config.strict_pure, changed, pedantic, explain)
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
        # DX-13: Enhanced output with stats (verified, cached, time, workers)
        if verification_level >= VerificationLevel.PROVE:
            if static_exit_code == 0 and doctest_passed:
                status = crosshair_output.get("status", "unknown")
                if status == "verified":
                    # DX-13: Show detailed stats
                    verified_count = crosshair_output.get("files_verified", 0)
                    cached_count = crosshair_output.get("files_cached", 0)
                    time_ms = crosshair_output.get("total_time_ms", 0)
                    workers = crosshair_output.get("workers", 1)

                    if verified_count == 0 and cached_count > 0:
                        # All from cache/no changes
                        reason = crosshair_output.get("reason", "cached")
                        console.print(f"[green]✓ CrossHair verified ({reason})[/green]")
                    elif time_ms > 0:
                        time_sec = time_ms / 1000
                        stats = f"{verified_count} verified"
                        if cached_count > 0:
                            stats += f", {cached_count} cached"
                        if workers > 1:
                            stats += f", {workers} workers"
                        console.print(
                            f"[green]✓ CrossHair verified[/green] "
                            f"[dim]({stats}, {time_sec:.1f}s)[/dim]"
                        )
                    else:
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
from invar.shell.update_cmd import update
from invar.shell.test_cmd import test, verify

app.command()(init)
app.command()(update)
app.command()(test)
app.command()(verify)


if __name__ == "__main__":
    app()
