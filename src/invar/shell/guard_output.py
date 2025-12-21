"""
Guard output formatters.

Shell module: handles output formatting for guard command.
Extracted from cli.py to reduce file size.
"""

from __future__ import annotations

from rich.console import Console

from invar.core.formatter import format_guard_agent
from invar.core.models import GuardReport, Severity

console = Console()


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


def output_rich(
    report: GuardReport,
    strict_pure: bool = False,
    changed_mode: bool = False,
    pedantic_mode: bool = False,
    explain_mode: bool = False,
) -> None:
    """Output report using Rich formatting."""
    console.print("\n[bold]Invar Guard Report[/bold]")
    console.print("=" * 40)
    mode_info = [
        m
        for m, c in [
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

    console.print(
        f"\n[{'green' if report.passed else 'red'}]Guard {'passed' if report.passed else 'failed'}.[/]"
    )
    console.print(
        "\n[dim]Note: Guard performs static analysis only. "
        "Dynamic imports and runtime behavior are not checked.[/dim]"
    )


def output_json(report: GuardReport) -> None:
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


def output_agent(
    report: GuardReport,
    doctest_passed: bool = True,
    doctest_output: str = "",
    crosshair_output: dict | None = None,
    verification_level: str = "standard",
) -> None:
    """Output report in Agent-optimized JSON format (Phase 8.2 + DX-06 + DX-09).

    Args:
        report: Guard analysis report
        doctest_passed: Whether doctests passed
        doctest_output: Doctest stdout (only if failed)
        crosshair_output: CrossHair results dict
        verification_level: Current level (static/standard/prove)
    """
    import json

    output = format_guard_agent(report)
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
    console.print(json.dumps(output, indent=2))
