"""
Test and verify CLI commands.

Extracted from cli.py to manage file size.
DX-08: Updated to use contract-driven property testing.
"""

from __future__ import annotations

from pathlib import Path

import typer
from returns.result import Failure
from rich.console import Console

from invar.shell.git import get_changed_files, is_git_repo

console = Console()


def _detect_agent_mode() -> bool:
    """Detect agent context: INVAR_MODE=agent OR non-TTY (pipe/redirect)."""
    import os
    import sys

    return os.getenv("INVAR_MODE") == "agent" or not sys.stdout.isatty()


# @shell_complexity: Test command with file collection and output
def test(
    target: str = typer.Argument(None, help="File to test (optional with --changed)"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    changed: bool = typer.Option(False, "--changed", help="Test git-modified files only"),
    max_examples: int = typer.Option(100, "--max-examples", help="Maximum Hypothesis examples per function"),
) -> None:
    """Run property-based tests using Hypothesis on contracted functions."""
    from invar.shell.property_tests import (
        format_property_test_report,
        run_property_tests_on_files,
    )

    use_json = json_output or _detect_agent_mode()

    # Get files to test
    if changed:
        if not is_git_repo(Path()):
            console.print("[red]Error:[/red] --changed requires a git repository")
            raise typer.Exit(1)
        changed_result = get_changed_files(Path())
        if isinstance(changed_result, Failure):
            console.print(f"[red]Error:[/red] {changed_result.failure()}")
            raise typer.Exit(1)
        files = list(changed_result.unwrap())
        if not files:
            console.print("[green]No changed Python files.[/green]")
            raise typer.Exit(0)
    elif target:
        files = [Path(target)]
    else:
        console.print("[red]Error:[/red] Either provide a file or use --changed")
        raise typer.Exit(1)

    # DX-08: Run property tests on files
    result = run_property_tests_on_files(files, max_examples, verbose)

    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    report, _coverage_data = result.unwrap()
    output = format_property_test_report(report, use_json)
    console.print(output)

    if not report.all_passed():
        raise typer.Exit(1)


# @shell_complexity: Verify command with CrossHair integration
def verify(
    target: str = typer.Argument(None, help="File to verify (optional with --changed)"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout per function (seconds)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    changed: bool = typer.Option(False, "--changed", help="Verify git-modified files only"),
) -> None:
    """Run symbolic verification using CrossHair."""
    from invar.shell.testing import run_verify

    use_json = json_output or _detect_agent_mode()

    # Get files to verify
    if changed:
        if not is_git_repo(Path()):
            console.print("[red]Error:[/red] --changed requires a git repository")
            raise typer.Exit(1)
        changed_result = get_changed_files(Path())
        if isinstance(changed_result, Failure):
            console.print(f"[red]Error:[/red] {changed_result.failure()}")
            raise typer.Exit(1)
        files = list(changed_result.unwrap())
        if not files:
            console.print("[green]No changed Python files.[/green]")
            raise typer.Exit(0)
    elif target:
        files = [Path(target)]
    else:
        console.print("[red]Error:[/red] Either provide a file or use --changed")
        raise typer.Exit(1)

    # Run verification on all files
    all_passed = True
    for file_path in files:
        result = run_verify(str(file_path), use_json, timeout)
        if isinstance(result, Failure):
            console.print(f"[red]Error:[/red] {result.failure()}")
            all_passed = False

    if not all_passed:
        raise typer.Exit(1)
