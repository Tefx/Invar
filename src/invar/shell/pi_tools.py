"""
Pi Coding Agent custom tools for Invar.

Provides Invar CLI commands as Pi custom tools for better LLM integration.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from rich.console import Console

# Pi tools directory
PI_TOOLS_DIR = ".pi/tools/invar"


def get_pi_tools_template_path() -> Path:
    """Get the path to Pi tools template."""
    return Path(__file__).parent.parent / "templates" / "pi-tools" / "invar"


def install_pi_tools(
    project_path: Path,
    console: Console,
) -> Result[list[str], str]:
    """
    Install Pi custom tools for Invar.

    Creates .pi/tools/invar/index.ts with:
    - invar_guard: Wrapper for invar guard command
    - invar_sig: Wrapper for invar sig command
    - invar_map: Wrapper for invar map command
    - invar_doc_toc: Extract document structure
    - invar_doc_read: Read specific section
    - invar_doc_find: Find sections by pattern
    - invar_doc_replace: Replace section content
    - invar_doc_insert: Insert content relative to section
    - invar_doc_delete: Delete section
    """
    tools_dir = project_path / PI_TOOLS_DIR
    tools_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold]Installing Pi custom tools...[/bold]")
    console.print("  Tools provide:")
    console.print("    ✓ invar_guard - Smart verification (static + doctests + symbolic)")
    console.print("    ✓ invar_sig - Show function signatures and contracts")
    console.print("    ✓ invar_map - Symbol map with reference counts")
    console.print("    ✓ 6 doc tools - Structured markdown editing (toc, read, find, replace, insert, delete)")
    console.print("")

    template_path = get_pi_tools_template_path()
    tool_file = template_path / "index.ts"

    if not tool_file.exists():
        return Failure(f"Template not found: {tool_file}")

    try:
        # Copy the template file
        dest_file = tools_dir / "index.ts"
        shutil.copy2(tool_file, dest_file)

        console.print(f"  [green]Created[/green] {PI_TOOLS_DIR}/index.ts")
        console.print("\n  [bold green]✓ Pi custom tools installed[/bold green]")
        console.print("  [dim]Pi will auto-discover tools in .pi/tools/[/dim]")
        console.print("  [yellow]⚠ Restart Pi session for tools to take effect[/yellow]")

        return Success(["index.ts"])
    except Exception as e:
        return Failure(f"Failed to install Pi tools: {e}")


def remove_pi_tools(
    project_path: Path,
    console: Console,
) -> Result[None, str]:
    """Remove Pi custom tools."""
    tools_dir = project_path / PI_TOOLS_DIR
    tool_file = tools_dir / "index.ts"

    if tool_file.exists():
        tool_file.unlink()
        console.print(f"  [red]Removed[/red] {PI_TOOLS_DIR}/index.ts")

        # Remove directory if empty
        try:
            tools_dir.rmdir()
            console.print(f"  [red]Removed[/red] {PI_TOOLS_DIR}/")
        except OSError:
            pass  # Directory not empty, keep it

        console.print("[bold green]✓ Pi custom tools removed[/bold green]")
    else:
        console.print("[dim]No Pi custom tools installed[/dim]")

    return Success(None)


def pi_tools_status(
    project_path: Path,
    console: Console,
) -> Result[dict[str, str], str]:
    """Check status of Pi custom tools."""
    tools_dir = project_path / PI_TOOLS_DIR
    tool_file = tools_dir / "index.ts"

    status: dict[str, str] = {}

    if not tool_file.exists():
        console.print("[dim]No Pi custom tools installed[/dim]")
        return Success({"status": "not_installed"})

    status["status"] = "installed"

    # Try to check file size (basic validation)
    try:
        size = tool_file.stat().st_size
        status["size"] = f"{size} bytes"
        console.print(f"[green]✓ Pi custom tools installed[/green] ({size} bytes)")
    except OSError:
        console.print("[green]✓ Pi custom tools installed[/green]")

    return Success(status)
