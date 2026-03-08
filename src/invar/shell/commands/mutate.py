"""
Mutation testing command for Invar CLI.

DX-28: `invar mutate` wraps mutmut to detect undertested code.
"""

from __future__ import annotations

import json as json_lib
from pathlib import Path

import typer
from returns.result import Failure
from rich.console import Console

from invar.shell.mutation import (
    MutationResult,
    check_mutmut_installed,
    get_surviving_mutants,
    run_mutation_test,
    show_mutant,
)

console = Console()


# @shell:entry - CLI command entry point
# @invar:allow entry_point_too_thick: CLI orchestration with multiple output modes
def mutate(
    target: Path = typer.Argument(
        Path(),
        help="File or directory to mutate",
        exists=True,
    ),
    tests: Path = typer.Option(
        None,
        "--tests",
        "-t",
        help="Test directory (auto-detected if not specified)",
    ),
    timeout: int = typer.Option(
        300,
        "--timeout",
        help="Maximum time in seconds",
    ),
    show_survivors: bool = typer.Option(
        False,
        "--survivors",
        "-s",
        help="Show surviving mutants",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
) -> None:
    """
    Run mutation testing to find undertested code.

    DX-28: Uses mutmut to automatically mutate code (e.g., `in` → `not in`)
    and check if tests catch the mutations. Surviving mutants indicate
    weak test coverage.

    Examples:

        invar mutate src/myapp/core/parser.py

        invar mutate src/myapp --tests tests/ --timeout 600

        invar mutate --survivors  # Show surviving mutants from last run
    """
    # Check if mutmut is installed
    install_check = check_mutmut_installed()
    if isinstance(install_check, Failure):
        if json_output:
            console.print(json_lib.dumps({"error": install_check.failure()}))
        else:
            console.print(f"[red]Error:[/red] {install_check.failure()}")
            console.print("\n[dim]Install with: pip install mutmut[/dim]")
        raise typer.Exit(1)

    # If just showing survivors from last run
    if show_survivors:
        result = get_surviving_mutants(target)
        if isinstance(result, Failure):
            if json_output:
                console.print(json_lib.dumps({"error": result.failure()}))
            else:
                console.print(f"[red]Error:[/red] {result.failure()}")
            raise typer.Exit(1)

        survivors = result.unwrap()
        if json_output:
            console.print(json_lib.dumps({"survivors": survivors}))
        else:
            if survivors:
                console.print(f"[yellow]Surviving mutants ({len(survivors)}):[/yellow]")
                for s in survivors:
                    console.print(f"  {s}")
            else:
                console.print("[green]No surviving mutants![/green]")
        return

    # Run mutation testing
    if not json_output:
        console.print(f"[bold]Running mutation testing on {target}...[/bold]")
        console.print("[dim]This may take a while.[/dim]\n")

    result = run_mutation_test(target, tests, timeout)

    if isinstance(result, Failure):
        if json_output:
            console.print(json_lib.dumps({"error": result.failure()}))
        else:
            console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    mutation_result = result.unwrap()
    _display_mutation_result(mutation_result, json_output)

    # Exit with error if mutation score is too low
    if not mutation_result.passed:
        raise typer.Exit(1)


# @shell_complexity: Result display with dual output modes (JSON/human)
def _display_mutation_result(result: MutationResult, json_output: bool) -> None:
    """Display mutation testing results."""
    if json_output:
        data = {
            "total": result.total,
            "killed": result.killed,
            "survived": result.survived,
            "timeout": result.timeout,
            "score": round(result.score, 1),
            "passed": result.passed,
            "errors": result.errors,
            "survivors": result.survivors,
        }
        console.print(json_lib.dumps(data, indent=2))
    else:
        # Human-readable output
        score_color = "green" if result.passed else "red"

        console.print("\n[bold]Mutation Testing Results[/bold]")
        console.print(f"  Total mutants: {result.total}")
        console.print(f"  [green]Killed:[/green] {result.killed}")
        console.print(f"  [red]Survived:[/red] {result.survived}")
        if result.timeout > 0:
            console.print(f"  [yellow]Timeout:[/yellow] {result.timeout}")

        console.print(
            f"\n  [{score_color}]Mutation Score: {result.score:.1f}%[/{score_color}]"
        )

        if result.passed:
            console.print("\n[green]✓ Mutation testing passed (≥80% killed)[/green]")
        else:
            console.print("\n[red]✗ Mutation testing failed (<80% killed)[/red]")
            console.print("[dim]Run with --survivors to see surviving mutants[/dim]")

        if result.errors:
            console.print("\n[yellow]Errors:[/yellow]")
            for err in result.errors:
                console.print(f"  {err}")


# @shell:entry - CLI command for showing mutant details
def mutant_show(
    mutant_id: int = typer.Argument(..., help="Mutant ID to show"),
) -> None:
    """
    Show the diff for a specific mutant.

    Use after `invar mutate --survivors` to investigate surviving mutants.
    """
    result = show_mutant(mutant_id)

    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    console.print(result.unwrap())
