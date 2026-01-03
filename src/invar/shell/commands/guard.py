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
from invar.shell.config import find_project_root, load_config
from invar.shell.fs import scan_project
from invar.shell.guard_output import output_agent, output_rich

app = typer.Typer(
    name="invar",
    help="AI-native software engineering framework",
    add_completion=False,
)
console = Console()

# DX-76: Register doc subcommand
from invar.shell.commands.doc import doc_app

app.add_typer(doc_app, name="doc")

# DX-79: Register feedback subcommand
from invar.shell.commands.feedback import feedback_app

app.add_typer(feedback_app, name="feedback")


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
    from invar.core.entry_points import extract_escape_hatches
    from invar.core.models import EscapeHatchDetail
    from invar.core.review_trigger import check_duplicate_escape_reasons
    from invar.core.shell_architecture import check_complexity_debt

    report = GuardReport(files_checked=0)
    all_escapes: list[tuple[str, str, str]] = []  # DX-33: (file, rule, reason)

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
        # DX-33 + DX-66: Collect escape hatches for cross-file analysis and visibility
        if file_info.source:
            for rule, reason, line in extract_escape_hatches(file_info.source):
                all_escapes.append((file_info.path, rule, reason))
                # DX-66: Add to escape hatch summary
                report.escape_hatches.add(EscapeHatchDetail(
                    file=file_info.path,
                    line=line,
                    rule=rule,
                    reason=reason,
                ))

    # DX-22: Check project-level complexity debt (Fix-or-Explain enforcement)
    for debt_violation in check_complexity_debt(
        report.violations, config.shell_complexity_debt_limit
    ):
        report.add_violation(debt_violation)

    # DX-33: Check for duplicate escape reasons across files
    for escape_violation in check_duplicate_escape_reasons(all_escapes):
        report.add_violation(escape_violation)

    return Success(report)


# @invar:allow entry_point_too_thick: Main CLI entry point, orchestrates all verification phases
@app.command()
def guard(
    path: Path = typer.Argument(
        Path(),
        help="Project directory or single Python file",
        exists=True,
        file_okay=True,
        dir_okay=True,
    ),
    strict: bool = typer.Option(False, "--strict", help="Treat warnings as errors"),
    changed: bool = typer.Option(
        True, "--changed/--all", help="Check git-modified files only (use --all for full check)"
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
    coverage: bool = typer.Option(
        False, "--coverage", help="DX-37: Collect branch coverage from doctest + hypothesis"
    ),
    suggest: bool = typer.Option(
        False, "--suggest", help="DX-61: Show functional pattern suggestions"
    ),
    contracts_only: bool = typer.Option(
        False, "--contracts-only", "-c", help="DX-63: Contract coverage check only"
    ),
) -> None:
    """Check project against Invar architecture rules.

    Smart Guard: Runs static analysis + doctests + CrossHair + Hypothesis by default.

    By default, checks only git-modified files for fast feedback during development.
    Use --all to check the entire project (useful for CI/release).
    Use --static for quick static-only checks (~0.5s vs ~5s full).
    Use --suggest to get functional pattern suggestions (NewType, Validation, etc.).
    Use --contracts-only (-c) to check contract coverage without running tests (DX-63).
    """
    # LX-06: Language detection and dispatch
    from invar.shell.commands.init import detect_language
    from invar.shell.guard_helpers import (
        collect_files_to_check,
        handle_changed_mode,
        output_verification_status,
        run_crosshair_phase,
        run_doctests_phase,
        run_property_tests_phase,
    )
    from invar.shell.testing import VerificationLevel

    project_language = detect_language(path if path.is_dir() else find_project_root(path))

    # Dispatch to language-specific guard if not Python
    if project_language == "typescript":
        from invar.shell.prove.guard_ts import run_typescript_guard

        ts_result = run_typescript_guard(path if path.is_dir() else find_project_root(path))
        match ts_result:
            case Success(result):
                if json_output or agent:
                    import json as json_mod

                    from invar.shell.prove.guard_ts import format_typescript_guard_v2

                    output = format_typescript_guard_v2(result)
                    console.print(json_mod.dumps(output, indent=2))
                else:
                    console.print(f"[bold]TypeScript Guard[/bold] ({project_language})")
                    if result.status == "passed":
                        console.print("[green]✓ PASSED[/green]")
                    elif result.status == "skipped":
                        console.print("[yellow]⚠ SKIPPED[/yellow] (no TypeScript tools available)")
                    else:
                        console.print(f"[red]✗ FAILED[/red] ({result.error_count} errors)")
                        for v in result.violations[:10]:  # Show first 10
                            console.print(f"  {v.file}:{v.line}: [{v.severity}] {v.message}")
                raise typer.Exit(0 if result.status == "passed" else 1)
            case Failure(err):
                console.print(f"[red]Error:[/red] {err}")
                raise typer.Exit(1)

    # DX-65: Handle single file mode (Python only from here)
    single_file_mode = path.is_file()
    single_file: Path | None = None
    if single_file_mode:
        if path.suffix != ".py":
            console.print(f"[red]Error:[/red] {path} is not a Python file")
            raise typer.Exit(1)
        single_file = path.resolve()
        path = find_project_root(path)

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

    # DX-63: Contract coverage check only mode
    if contracts_only:
        import json

        from invar.shell.contract_coverage import (
            calculate_contract_coverage,
            format_contract_coverage_agent,
            format_contract_coverage_report,
        )

        # DX-65: Use single file path if in single file mode
        coverage_path = single_file if single_file else path
        coverage_result = calculate_contract_coverage(coverage_path, changed_only=changed)
        if isinstance(coverage_result, Failure):
            console.print(f"[red]Error:[/red] {coverage_result.failure()}")
            raise typer.Exit(1)

        report_data = coverage_result.unwrap()
        use_agent_output = _determine_output_mode(human, agent, json_output)

        if use_agent_output:
            console.print(json.dumps(format_contract_coverage_agent(report_data)))
        else:
            console.print(format_contract_coverage_report(report_data))

        raise typer.Exit(0 if report_data.ready_for_build else 1)

    # Handle --changed mode or single file mode (DX-65)
    only_files: set[Path] | None = None
    checked_files: list[Path] = []
    if single_file:
        # DX-65: Single file mode - only check the specified file
        only_files = {single_file}
        checked_files = [single_file]
    elif changed:
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

    # DX-61: Run pattern detection if --suggest flag is set
    pattern_suggestions: list = []
    if suggest:
        from invar.shell.pattern_integration import (
            filter_suggestions,
            run_pattern_detection,
            suggestions_to_violations,
        )
        # Run pattern detection on checked files
        files_to_check = list(only_files) if only_files else None
        pattern_result = run_pattern_detection(path, files_to_check)
        if isinstance(pattern_result, Success):
            raw_suggestions = pattern_result.unwrap()
            # DX-61: Apply config-based filtering
            pattern_suggestions = filter_suggestions(raw_suggestions, config)
            # Add suggestions to report as SUGGEST-level violations
            for violation in suggestions_to_violations(pattern_suggestions):
                report.add_violation(violation)

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
    crosshair_passed: bool = True
    crosshair_output: dict = {}
    property_passed: bool = True
    property_output: dict = {}
    # DX-37: Coverage data from doctest + hypothesis phases
    doctest_coverage: dict | None = None
    property_coverage: dict | None = None

    # DX-37: Check coverage availability if requested
    if coverage:
        from invar.shell.coverage import check_coverage_available
        cov_check = check_coverage_available()
        if isinstance(cov_check, Failure):
            console.print(f"[yellow]Warning:[/yellow] {cov_check.failure()}")
            coverage = False  # Disable coverage if not available

    # DX-19: STANDARD runs all verification phases
    if verification_level == VerificationLevel.STANDARD and static_exit_code == 0:
        checked_files = collect_files_to_check(path, checked_files)

        # Phase 1: Doctests (DX-37: with optional coverage)
        doctest_passed, doctest_output, doctest_coverage = run_doctests_phase(
            checked_files, explain, timeout=config.timeout_doctest,
            collect_coverage=coverage,
        )

        # Phase 2: CrossHair symbolic verification
        # Note: CrossHair uses subprocess + symbolic execution, coverage not applicable
        crosshair_passed, crosshair_output = run_crosshair_phase(
            path, checked_files, doctest_passed, static_exit_code,
            changed_mode=changed,
            timeout=config.timeout_crosshair,
            per_condition_timeout=config.timeout_crosshair_per_condition,
        )

        # Phase 3: Hypothesis property tests (DX-37: with optional coverage)
        property_passed, property_output, property_coverage = run_property_tests_phase(
            checked_files, doctest_passed, static_exit_code,
            collect_coverage=coverage,
        )
    elif verification_level == VerificationLevel.STATIC:
        # Static-only mode: explicitly mark verification as skipped
        crosshair_output = {"status": "skipped", "reason": "static mode"}
        property_output = {"status": "skipped", "reason": "static mode"}
    elif static_exit_code != 0:
        # Static failures: explicitly mark verification as skipped
        crosshair_output = {"status": "skipped", "reason": "prior failures"}
        property_output = {"status": "skipped", "reason": "prior failures"}

    # DX-37: Merge coverage data from doctest + hypothesis
    coverage_output: dict | None = None
    if coverage and (doctest_coverage or property_coverage):
        coverage_output = {
            "enabled": True,
            "phases_tracked": [],
            "phases_excluded": ["crosshair"],  # CrossHair uses symbolic execution
        }
        if doctest_coverage and doctest_coverage.get("collected"):
            coverage_output["phases_tracked"].append("doctest")
        if property_coverage and property_coverage.get("collected"):
            coverage_output["phases_tracked"].append("hypothesis")
            if "overall_branch_coverage" in property_coverage:
                coverage_output["overall_branch_coverage"] = property_coverage["overall_branch_coverage"]

    # DX-26: Unified output (agent JSON or human Rich)
    if use_agent_output:
        output_agent(
            report, strict, doctest_passed, doctest_output, crosshair_output, level_name,
            property_output=property_output,
            coverage_data=coverage_output,  # DX-37
        )
    else:
        output_rich(report, config.strict_pure, changed, pedantic, explain, static)
        output_verification_status(
            verification_level, static_exit_code, doctest_passed,
            doctest_output, crosshair_output, explain,
            property_output=property_output,
            strict=strict,
        )
        # DX-37: Show coverage info in human output
        if coverage_output and coverage_output.get("phases_tracked"):
            phases = coverage_output.get("phases_tracked", [])
            overall = coverage_output.get("overall_branch_coverage", 0.0)
            console.print(f"\n[bold]Coverage Analysis[/bold] ({' + '.join(phases)})")
            console.print(f"  Overall branch coverage: {overall}%")
            console.print("  [dim]Note: CrossHair uses symbolic execution; coverage not applicable.[/dim]")

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
    console.print(f"invar-tools {__version__}")


@app.command("map")
def map_command(
    path: Path = typer.Argument(Path(), help="Project root directory"),
    top: int = typer.Option(0, "--top", help="Show top N most-referenced symbols"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate symbol map with reference counts."""
    from invar.shell.commands.perception import run_map

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
    from invar.shell.commands.perception import run_sig

    # Phase 9 P11: Auto-detect agent mode
    use_json = json_output or _detect_agent_mode()
    result = run_sig(target, use_json)
    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)


# @invar:allow entry_point_too_thick: Multi-language ref finding with examples
@app.command("refs")
def refs_command(
    target: str = typer.Argument(..., help="file.py::symbol or file.ts::symbol"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Find all references to a symbol.

    DX-78: Supports Python (via jedi) and TypeScript (via TS Compiler API).

    Examples:
        invar refs src/auth.py::AuthService
        invar refs src/auth.ts::validateToken
    """
    from invar.shell.commands.perception import run_refs

    # Auto-detect agent mode
    use_json = json_output or _detect_agent_mode()
    result = run_refs(target, use_json)
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


# DX-48b: Import commands from shell/commands/
from invar.shell.commands.hooks import app as hooks_app  # DX-57
from invar.shell.commands.init import init
from invar.shell.commands.mutate import mutate  # DX-28
from invar.shell.commands.skill import app as skill_app  # LX-07
from invar.shell.commands.sync_self import sync_self  # DX-49
from invar.shell.commands.test import test, verify
from invar.shell.commands.uninstall import uninstall  # DX-69
from invar.shell.commands.update import update

app.command()(init)
app.command()(uninstall)  # DX-69: Remove Invar from project
app.command()(update)
app.command()(test)
app.command()(verify)
app.command()(mutate)  # DX-28: Mutation testing
app.add_typer(hooks_app, name="hooks")  # DX-57: Claude Code hooks management
app.add_typer(skill_app, name="skill")  # LX-07: Extension skills management

# DX-56: Create dev subcommand group for developer commands
dev_app = typer.Typer(
    name="dev",
    help="Developer commands for Invar project development",
    add_completion=False,
)
dev_app.command("sync")(sync_self)  # DX-56: renamed from sync-self
app.add_typer(dev_app)

# DX-56: Keep sync-self as alias for backward compatibility (deprecated)
app.command("sync-self", hidden=True)(sync_self)


# MCP server command for Claude Code integration
@app.command()
def mcp() -> None:
    """Start Invar MCP server for AI agent integration.

    This runs the MCP server using stdio transport.
    Used by Claude Code and other MCP-compatible AI agents.
    """
    from invar.mcp.server import run_server

    run_server()


if __name__ == "__main__":
    app()
