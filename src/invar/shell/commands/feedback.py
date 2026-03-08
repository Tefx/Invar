"""
CLI commands for feedback management.

DX-79 Phase D: Analysis Tools for /invar-reflect feedback.
Shell module: handles feedback file operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from returns.result import Failure, Result, Success
from rich.console import Console
from rich.table import Table

from invar.core.feedback import anonymize_feedback_content

console = Console()

# Create feedback subcommand app
feedback_app = typer.Typer(
    name="feedback",
    help="Manage Invar usage feedback files.",
    no_args_is_help=True,
)


# @shell_complexity: File discovery with filtering
def _get_feedback_files(
    project_path: Path,
    older_than_days: int | None = None,
) -> Result[list[tuple[Path, datetime]], str]:
    """
    Get feedback files with optional age filtering.

    Args:
        project_path: Path to project root
        older_than_days: Only return files older than N days (None = all)

    Returns:
        Success with list of (file_path, modified_time) tuples, or Failure
    """
    feedback_dir = project_path / ".invar" / "feedback"

    if not feedback_dir.exists():
        return Success([])

    try:
        files: list[tuple[Path, datetime]] = []
        cutoff = datetime.now() - timedelta(days=older_than_days) if older_than_days else None

        for file in feedback_dir.glob("feedback-*.md"):
            if not file.is_file():
                continue

            mtime = datetime.fromtimestamp(file.stat().st_mtime)

            if cutoff is None or mtime < cutoff:
                files.append((file, mtime))

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[1], reverse=True)
        return Success(files)

    except OSError as e:
        return Failure(f"Failed to read feedback directory: {e}")


# @invar:allow entry_point_too_thick: CLI display with table formatting and help text
@feedback_app.command(name="list")
def list_feedback(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory (default: current directory)"),
    ] = Path(),
) -> None:
    """
    List all feedback files in the project.

    Shows:
    - File name
    - Last modified time
    - File size

    Example:
        invar feedback list
    """
    path = path.resolve()
    result = _get_feedback_files(path)

    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    files = result.unwrap()

    if not files:
        console.print("[dim]No feedback files found in .invar/feedback/[/dim]")
        console.print("\n[dim]Tip: Use /invar-reflect to generate feedback[/dim]")
        return

    # Display table
    table = Table(title="Invar Feedback Files")
    table.add_column("File", style="cyan")
    table.add_column("Last Modified", style="yellow")
    table.add_column("Size", justify="right", style="dim")

    for file, mtime in files:
        size_kb = file.stat().st_size / 1024
        table.add_row(
            file.name,
            mtime.strftime("%Y-%m-%d %H:%M"),
            f"{size_kb:.1f} KB",
        )

    console.print(table)
    console.print(f"\n[bold]{len(files)}[/bold] feedback file(s) found")


# @invar:allow entry_point_too_thick: CLI workflow with confirmation, deletion, and error handling
@feedback_app.command(name="cleanup")
def cleanup_feedback(
    older_than: Annotated[
        int,
        typer.Option("--older-than", help="Delete files older than N days"),
    ] = 90,
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory (default: current directory)"),
    ] = Path(),
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be deleted without deleting"),
    ] = False,
) -> None:
    """
    Clean up old feedback files.

    Default: Delete files older than 90 days.

    Examples:
        invar feedback cleanup                  # Delete files older than 90 days
        invar feedback cleanup --older-than 30  # Delete files older than 30 days
        invar feedback cleanup --dry-run        # Preview what would be deleted
    """
    path = path.resolve()
    result = _get_feedback_files(path, older_than_days=older_than)

    if isinstance(result, Failure):
        console.print(f"[red]Error:[/red] {result.failure()}")
        raise typer.Exit(1)

    files = result.unwrap()

    if not files:
        console.print(f"[green]✓[/green] No files older than {older_than} days")
        return

    # Display what will be deleted
    console.print(f"[bold]Files older than {older_than} days:[/bold]\n")
    for file, mtime in files:
        age_days = (datetime.now() - mtime).days
        console.print(f"  [red]✗[/red] {file.name} ({age_days} days old)")

    if dry_run:
        console.print(f"\n[dim]Dry run: Would delete {len(files)} file(s)[/dim]")
        console.print("[dim]Run without --dry-run to apply[/dim]")
        return

    # Confirm deletion
    from rich.prompt import Confirm

    if not Confirm.ask(f"\nDelete {len(files)} file(s)?", default=False):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Delete files
    deleted = 0
    failed = 0
    for file, _ in files:
        try:
            file.unlink()
            deleted += 1
        except OSError as e:
            console.print(f"  [red]Failed to delete {file.name}:[/red] {e}")
            failed += 1

    # Summary
    console.print(f"\n[green]✓[/green] Deleted {deleted} file(s)")
    if failed > 0:
        console.print(f"[red]✗[/red] Failed to delete {failed} file(s)")


# @invar:allow entry_point_too_thick: CLI with file handling, error display, and multiple output modes
@feedback_app.command(name="anonymize")
def anonymize_feedback(
    file: Annotated[
        str,
        typer.Argument(help="Feedback file name (e.g., feedback-2026-01-03.md)"),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", help="Project root directory"),
    ] = Path(),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file (default: stdout)"),
    ] = None,
) -> None:
    """
    Anonymize feedback for sharing.

    Removes:
    - Project names
    - File paths
    - Function/symbol names
    - Error messages

    Examples:
        invar feedback anonymize feedback-2026-01-03.md
        invar feedback anonymize feedback-2026-01-03.md -o safe.md
        invar feedback anonymize feedback-2026-01-03.md > share.md
    """
    path = path.resolve()
    feedback_dir = path / ".invar" / "feedback"
    input_file = feedback_dir / file

    if not input_file.exists():
        console.print(f"[red]Error:[/red] File not found: {input_file}")
        console.print("\n[dim]Available files:[/dim]")

        # Show available files
        result = _get_feedback_files(path)
        if isinstance(result, Success):
            for f, _ in result.unwrap():
                console.print(f"  {f.name}")

        raise typer.Exit(1)

    # Read and anonymize
    try:
        content = input_file.read_text(encoding="utf-8")
        anonymized = anonymize_feedback_content(content)

        # Output
        if output:
            output.write_text(anonymized, encoding="utf-8")
            console.print(f"[green]✓[/green] Anonymized feedback saved to: {output}")
        else:
            # Print to stdout
            console.print(anonymized)

    except OSError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
