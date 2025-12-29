"""
Guard output formatters.

Shell module: handles output formatting for guard command.
Extracted from cli.py to reduce file size.

DX-22: Added verification routing statistics for de-duplication.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console

from invar.core.formatter import format_guard_agent
from invar.core.models import GuardReport, Severity
from invar.core.utils import get_combined_status

console = Console()


@dataclass
class VerificationStats:
    """
    DX-22: De-duplicated verification statistics.

    Tracks separate counts for CrossHair (proof) vs Hypothesis (testing)
    to avoid misleading double-counting.
    """

    crosshair_proven: int = 0
    hypothesis_tested: int = 0
    doctests_passed: int = 0
    routed_to_hypothesis: int = 0  # Files routed due to C extensions

    @property
    def total_verified(self) -> int:
        """Total unique functions verified (no double-counting)."""
        return self.crosshair_proven + self.hypothesis_tested

    @property
    def proof_coverage_pct(self) -> float:
        """Percentage of verifiable code proven by CrossHair."""
        total = self.crosshair_proven + self.hypothesis_tested
        if total == 0:
            return 0.0
        return (self.crosshair_proven / total) * 100


# @shell_orchestration: Rich markup formatting tightly coupled to shell output
# @shell_complexity: Conditional formatting for each stat category
def format_verification_stats(stats: VerificationStats) -> str:
    """
    Format verification statistics for display.

    DX-22: Shows de-duplicated counts distinguishing proof from testing.
    """
    lines = []
    lines.append("Verification breakdown:")
    if stats.crosshair_proven > 0:
        lines.append(f"  ✓ Proven (CrossHair): {stats.crosshair_proven} functions")
    if stats.hypothesis_tested > 0:
        lines.append(f"  ✓ Tested (Hypothesis): {stats.hypothesis_tested} functions")
    if stats.routed_to_hypothesis > 0:
        lines.append(
            f"    [dim](C-extension routing: {stats.routed_to_hypothesis} files)[/dim]"
        )
    if stats.doctests_passed > 0:
        lines.append(f"  ✓ Doctests: {stats.doctests_passed} passed")
    if stats.total_verified > 0:
        lines.append(f"  Proof coverage: {stats.proof_coverage_pct:.0f}%")
    return "\n".join(lines)


# @shell_complexity: Context display with line range extraction
def show_file_context(file_path: str) -> None:
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


# @shell_complexity: Rich formatting with conditional sections
def output_rich(
    report: GuardReport,
    strict_pure: bool = False,
    changed_mode: bool = False,
    pedantic_mode: bool = False,
    explain_mode: bool = False,
    static_mode: bool = False,
) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    mode_info = [
        m
        for m, c in [
            ("static", static_mode),
            ("strict-pure", strict_pure),
            ("changed-only", changed_mode),
            ("pedantic", pedantic_mode),
            ("explain", explain_mode),
        ]
        if c
    ]
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
                show_file_context(fp)
            for v in vs:
                if v.severity == Severity.ERROR:
                    icon = "[red]ERROR[/red]"
                elif v.severity == Severity.WARNING:
                    icon = "[yellow]WARN[/yellow]"
                elif v.severity == Severity.SUGGEST:
                    icon = "[magenta]SUGGEST[/magenta]"  # DX-61
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
    summary = (
        f"Files checked: {report.files_checked}\n"
        f"Errors: {report.errors}\n"
        f"Warnings: {report.warnings}"
    )
    if report.infos > 0:
        summary += f"\nInfos: {report.infos}"
    # DX-61: Show suggestions count if any
    if report.suggests > 0:
        summary += f"\n[magenta]Suggestions: {report.suggests}[/magenta]"
    console.print(summary)

    # P24: Contract coverage statistics (only show if core files exist)
    if report.core_functions_total > 0:
        pct = report.contract_coverage_pct
        console.print(
            f"\n[bold]Contract coverage:[/bold] {pct}% "
            f"({report.core_functions_with_contracts}/{report.core_functions_total} functions)"
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

    # DX-66: Escape hatch summary (only show if any exist)
    if report.escape_hatches.count > 0:
        escape_count = report.escape_hatches.count
        by_rule = report.escape_hatches.by_rule
        rule_parts = [f"{count} {rule}" for rule, count in sorted(by_rule.items())]
        console.print(
            f"\n[bold]Escape hatches:[/bold] {escape_count} "
            f"({', '.join(rule_parts)})"
        )

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
            f"\n[bold]Code Health:[/bold] [{health_color}]{health}%[/{health_color}] "
            f"{bar} ({health_label})"
        )

        # Tip for fixing warnings
        if report.warnings > 0:
            console.print(
                "[dim]💡 Fix warnings in files you modified to improve code health.[/dim]"
            )

    # DX-26: Show static-only conclusion for --static mode
    # Full mode shows conclusion after all phases in output_verification_status()
    if static_mode:
        console.print(
            f"\n[{'green' if report.passed else 'red'}]Guard {'passed' if report.passed else 'failed'}.[/]"
        )
        console.print(
            "\n[dim]Note: --static mode skips runtime tests (doctests, CrossHair, Hypothesis).[/dim]"
        )


# @shell_complexity: JSON output assembly with multiple sections
def output_agent(
    report: GuardReport,
    strict: bool = False,
    doctest_passed: bool = True,
    doctest_output: str = "",
    crosshair_output: dict | None = None,
    verification_level: str = "standard",
    property_output: dict | None = None,  # DX-08
    routing_stats: dict | None = None,  # DX-22
    coverage_data: dict | None = None,  # DX-37
) -> None:
    """Output report in Agent-optimized JSON format (Phase 8.2 + DX-06 + DX-08 + DX-09 + DX-22 + DX-26 + DX-37).

    Args:
        report: Guard analysis report
        strict: Whether warnings are treated as errors
        doctest_passed: Whether doctests passed
        doctest_output: Doctest stdout (only if failed)
        crosshair_output: CrossHair results dict
        verification_level: Current level (static/standard)
        property_output: Property test results dict (DX-08)
        routing_stats: Smart routing statistics (DX-22)
        coverage_data: DX-37: Branch coverage data from doctest + hypothesis

    DX-22: Adds routing stats showing CrossHair vs Hypothesis distribution.
    DX-26: status now reflects ALL test phases, not just static analysis.
    DX-37: Adds optional coverage data from doctest + hypothesis phases.
    """
    import json

    # DX-26: Extract passed status from phase outputs
    crosshair_passed = True
    if crosshair_output:
        crosshair_status = crosshair_output.get("status", "verified")
        crosshair_passed = crosshair_status in ("verified", "skipped")

    property_passed = True
    if property_output:
        property_status = property_output.get("status", "passed")
        property_passed = property_status in ("passed", "skipped")

    # DX-26: Calculate combined status including all test phases
    combined_status = get_combined_status(
        report, strict, doctest_passed, crosshair_passed, property_passed
    )

    output = format_guard_agent(report, combined_status=combined_status)
    # DX-09: Add verification level for Agent transparency
    output["verification_level"] = verification_level
    # DX-06: Add doctest results to agent output
    output["doctest"] = {
        "passed": doctest_passed,
        "output": doctest_output if not doctest_passed else "",
    }
    # DX-06: Add CrossHair results if available
    if crosshair_output:
        output["crosshair"] = crosshair_output
    # DX-08: Add property test results if available
    if property_output:
        output["property_tests"] = property_output
    # DX-22: Add smart routing statistics if available
    if routing_stats:
        output["routing"] = routing_stats
    # DX-37: Add coverage data if collected
    if coverage_data:
        output["coverage"] = coverage_data
    console.print(json.dumps(output, indent=2))
