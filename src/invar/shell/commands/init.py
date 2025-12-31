"""
Init command for Invar.

Shell module: handles project initialization.
DX-70: Simplified init with interactive menus and safe merge behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from returns.result import Failure, Success
from rich.console import Console
from rich.panel import Panel

from invar.core.sync_helpers import VALID_LANGUAGES, SyncConfig
from invar.shell.claude_hooks import install_claude_hooks
from invar.shell.commands.template_sync import sync_templates
from invar.shell.mcp_config import (
    generate_mcp_json,
    get_recommended_method,
)
from invar.shell.pi_hooks import install_pi_hooks
from invar.shell.templates import (
    add_config,
    create_directories,
    install_hooks,
)

console = Console()


# =============================================================================
# File Categories (DX-70)
# =============================================================================

FILE_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "required": [
        ("INVAR.md", "Protocol and contract rules"),
        (".invar/", "Config, context, examples"),
    ],
    "optional": [
        (".pre-commit-config.yaml", "Verification before commit"),
        ("src/core/", "Pure logic directory"),
        ("src/shell/", "I/O operations directory"),
    ],
    "claude": [
        ("CLAUDE.md", "Agent instructions"),
        (".claude/skills/", "Workflow automation"),
        (".claude/commands/", "User commands (/audit, /guard)"),
        (".claude/hooks/", "Tool guidance (+ settings.local.json)"),
        (".mcp.json", "MCP server config"),
    ],
    "generic": [
        ("AGENT.md", "Universal agent instructions"),
    ],
    "pi": [
        ("CLAUDE.md", "Agent instructions (Pi compatible)"),
        (".claude/skills/", "Workflow automation (Pi compatible)"),
        (".pi/hooks/", "Pi-specific hooks"),
    ],
}

AGENT_CONFIGS: dict[str, dict[str, str]] = {
    "claude": {"name": "Claude Code", "category": "claude"},
    "pi": {"name": "Pi Coding Agent", "category": "pi"},
    "generic": {"name": "Other (AGENT.md)", "category": "generic"},
}


# =============================================================================
# Language Detection (LX-05)
# =============================================================================

# Supported languages for template rendering
SUPPORTED_LANGUAGES = frozenset({"python", "typescript"})
FUTURE_LANGUAGES = frozenset({"rust", "go"})


# @shell_complexity: Multi-marker file detection for language auto-detect
def detect_language(path: Path) -> str:
    """Auto-detect project language from marker files.

    Checks for common project configuration files to determine the primary
    language. Returns a supported language or defaults to "python".

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d)
        ...     (p / "pyproject.toml").touch()
        ...     detect_language(p)
        'python'

        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d)
        ...     (p / "tsconfig.json").touch()
        ...     detect_language(p)
        'typescript'

        >>> with tempfile.TemporaryDirectory() as d:
        ...     p = Path(d)
        ...     detect_language(p)  # Empty dir defaults to python
        'python'
    """
    # Detection order matters - first match wins
    if (path / "pyproject.toml").exists() or (path / "setup.py").exists():
        return "python"
    if (path / "tsconfig.json").exists() or (path / "package.json").exists():
        return "typescript"
    if (path / "Cargo.toml").exists():
        return "rust"  # Future
    if (path / "go.mod").exists():
        return "go"  # Future
    return "python"  # Default


# =============================================================================
# Interactive Prompts (DX-70)
# =============================================================================


def _is_interactive() -> bool:
    """Check if running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


# @shell_orchestration: Style configuration for questionary UI library
def _get_prompt_style():
    """Get custom style for questionary prompts.

    Simple design:
    - Pointer (») indicates current row
    - Checkbox (●/○) indicates selected state
    - All text in default color, no reverse
    """
    from questionary import Style

    return Style([
        ("pointer", "fg:cyan bold"),        # Pointer: cyan bold
        ("highlighted", "noreverse"),       # Current row: no reverse
        ("selected", "noreverse"),          # Selected items: no reverse
        ("text", "noreverse"),              # Normal text: no reverse
    ])


# @shell_complexity: Interactive prompt with cursor selection
def _prompt_agent_selection() -> list[str]:
    """Prompt user to select code agent using cursor navigation."""
    import questionary

    console.print("\n[bold]Select code agent:[/bold]")
    console.print("[dim]Use arrow keys to move, enter to select[/dim]\n")

    choices = [
        questionary.Choice("Claude Code (recommended)", value="claude"),
        questionary.Choice("Pi Coding Agent", value="pi"),
        questionary.Choice("Other (AGENT.md)", value="generic"),
    ]

    selected = questionary.select(
        "",
        choices=choices,
        instruction="",
        style=_get_prompt_style(),
    ).ask()

    # Handle Ctrl+C
    if not selected:
        return ["claude"]  # Default to Claude Code
    return [selected]


# @shell_complexity: Interactive file selection with cursor navigation
def _prompt_file_selection(agents: list[str]) -> dict[str, bool]:
    """Prompt user to select optional files using cursor navigation."""
    import questionary

    # Build available files
    available: dict[str, list[tuple[str, str]]] = {
        "optional": FILE_CATEGORIES["optional"],
    }
    for agent in agents:
        config = AGENT_CONFIGS.get(agent)
        if config:
            category = config["category"]
            available[category] = FILE_CATEGORIES.get(category, [])

    # Show header
    console.print("\n[bold]File Selection:[/bold]")
    console.print("[dim]Existing files will be MERGED (your content preserved).[/dim]\n")

    # Required files (always installed)
    console.print("[bold]Required (always installed):[/bold]")
    for file, desc in FILE_CATEGORIES["required"]:
        console.print(f"  [green]✓[/green] {file:30} {desc}")

    console.print()
    console.print("[dim]Use arrow keys to move, space to toggle, enter to confirm[/dim]\n")

    # Build choices with categories as separators
    choices: list[questionary.Choice | questionary.Separator] = []
    file_list: list[str] = []

    for category, files in available.items():
        if category == "required":
            continue
        category_name = category.capitalize()
        if category == "claude":
            category_name = "Claude Code"
        elif category == "pi":
            category_name = "Pi Coding Agent"
        choices.append(questionary.Separator(f"── {category_name} ──"))
        for file, desc in files:
            choices.append(
                questionary.Choice(f"{file:28} {desc}", value=file, checked=True)
            )
            file_list.append(file)

    selected = questionary.checkbox(
        "Select files to install:",
        choices=choices,
        instruction="",
        style=_get_prompt_style(),
    ).ask()

    # Handle Ctrl+C or empty result
    if selected is None:
        return dict.fromkeys(file_list, True)  # Default: all selected

    # Build result dict
    return {f: f in selected for f in file_list}


def _show_execution_output(
    created: list[str],
    merged: list[str],
    skipped: list[str],
) -> None:
    """Display execution results."""
    console.print()
    for file in created:
        console.print(f"  [green]✓[/green] {file:30} [dim]created[/dim]")
    for file in merged:
        console.print(f"  [cyan]↻[/cyan] {file:30} [dim]merged[/dim]")
    for file in skipped:
        console.print(f"  [dim]○[/dim] {file:30} [dim]skipped[/dim]")


# =============================================================================
# MCP Configuration
# =============================================================================


# @shell_complexity: MCP config merge with existing file handling
def _configure_mcp(path: Path) -> bool:
    """Configure MCP server with recommended method."""
    import json

    config = get_recommended_method()
    mcp_json_path = path / ".mcp.json"
    mcp_content = generate_mcp_json(config)

    if mcp_json_path.exists():
        try:
            existing = json.loads(mcp_json_path.read_text())
            if "mcpServers" in existing and "invar" in existing.get("mcpServers", {}):
                return False  # Already configured
            # Add invar to existing config
            if "mcpServers" not in existing:
                existing["mcpServers"] = {}
            existing["mcpServers"]["invar"] = mcp_content["mcpServers"]["invar"]
            mcp_json_path.write_text(json.dumps(existing, indent=2))
            return True
        except (json.JSONDecodeError, OSError):
            return False
    else:
        mcp_json_path.write_text(json.dumps(mcp_content, indent=2))
        return True


# =============================================================================
# Main Init Command (DX-70)
# =============================================================================


# @shell_complexity: Main CLI entry point with interactive flow and file generation
def init(
    path: Path = typer.Argument(
        Path(),
        help="Project root directory (default: current directory)",
    ),
    claude: bool = typer.Option(
        False,
        "--claude",
        help="Auto-select Claude Code, skip all prompts",
    ),
    pi: bool = typer.Option(
        False,
        "--pi",
        help="Auto-select Pi Coding Agent, skip all prompts",
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help="Target language (auto-detected if not specified): python, typescript",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        help="Show what would be done (dry run)",
    ),
) -> None:
    """
    Initialize or update Invar configuration.

    DX-70: Simplified init with interactive selection and safe merge.

    \b
    Quick setup options:
    - --claude  Auto-select Claude Code (MCP + hooks + skills)
    - --pi      Auto-select Pi (shares CLAUDE.md + skills, adds Pi hooks)

    \b
    This command is safe - it always MERGES with existing files:
    - File doesn't exist → Create
    - File exists → Merge (update invar regions, preserve your content)
    - Never overwrites user content
    - Never deletes files

    \b
    For full reset, use: invar uninstall && invar init
    """
    from invar import __version__

    # Mutual exclusivity check
    if claude and pi:
        console.print("[red]Error:[/red] Cannot use --claude and --pi together.")
        raise typer.Exit(1)

    # Resolve path
    if path == Path():
        path = Path.cwd()
    path = path.resolve()

    # LX-05: Language detection and validation
    if language is None:
        detected = detect_language(path)
        # Fall back to python for unsupported detected languages
        if detected in FUTURE_LANGUAGES:
            console.print(
                f"[yellow]Note:[/yellow] {detected} project detected. "
                f"Using python templates (most similar). "
                f"Native {detected} support coming soon."
            )
            language = "python"
        else:
            language = detected
    else:
        # Validate explicitly provided language
        if language not in VALID_LANGUAGES:
            valid = ", ".join(sorted(VALID_LANGUAGES))
            console.print(f"[red]Error:[/red] Invalid language '{language}'. Must be one of: {valid}")
            raise typer.Exit(1)

    # Header
    if claude:
        console.print(f"\n[bold]Invar v{__version__} - Quick Setup (Claude Code)[/bold]")
    elif pi:
        console.print(f"\n[bold]Invar v{__version__} - Quick Setup (Pi)[/bold]")
    else:
        console.print(f"\n[bold]Invar v{__version__} - Project Setup[/bold]")
    console.print("=" * 45)
    console.print(f"[dim]Language: {language} | Existing files will be MERGED.[/dim]")

    # Determine agents and files
    if claude:
        # Quick mode: Claude Code defaults
        agents = ["claude"]
        selected_files: dict[str, bool] = {}
        for category in ["optional", "claude"]:
            for file, _ in FILE_CATEGORIES.get(category, []):
                selected_files[file] = True
    elif pi:
        # Quick mode: Pi defaults
        agents = ["pi"]
        selected_files = {}
        for category in ["optional", "pi"]:
            for file, _ in FILE_CATEGORIES.get(category, []):
                selected_files[file] = True
    else:
        # Interactive mode
        if not _is_interactive():
            console.print("[yellow]Non-interactive terminal detected. Use --claude or --pi for quick setup.[/yellow]")
            raise typer.Exit(1)

        agents = _prompt_agent_selection()
        selected_files = _prompt_file_selection(agents)

    # Preview mode
    if preview:
        console.print("\n[bold]Preview - Would create/update:[/bold]")
        console.print("\n[bold]Required:[/bold]")
        for file, desc in FILE_CATEGORIES["required"]:
            console.print(f"  [green]✓[/green] {file:30} {desc}")

        console.print("\n[bold]Selected:[/bold]")
        for file, selected in selected_files.items():
            if selected:
                console.print(f"  [green]✓[/green] {file}")
            else:
                console.print(f"  [dim]○[/dim] {file} [dim](skipped)[/dim]")

        console.print("\n[dim]Run without --preview to apply.[/dim]")
        return

    # Execute
    console.print("\n[bold]Creating files...[/bold]")

    created: list[str] = []
    merged: list[str] = []
    skipped: list[str] = []

    # Add config file (.invar/config.toml or pyproject.toml)
    config_result = add_config(path, console)
    if isinstance(config_result, Failure):
        console.print(f"[red]Error:[/red] {config_result.failure()}")
        raise typer.Exit(1)

    # Ensure .invar directory exists
    invar_dir = path / ".invar"
    if not invar_dir.exists():
        invar_dir.mkdir()

    # Build skip patterns based on selection
    skip_patterns: list[str] = []
    if not selected_files.get(".claude/skills/", True):
        skip_patterns.append(".claude/skills/*")
    if not selected_files.get(".claude/commands/", True):
        skip_patterns.append(".claude/commands/*")
    if not selected_files.get(".pre-commit-config.yaml", True):
        skip_patterns.append(".pre-commit-config.yaml")

    # Run template sync (LX-05: pass language for template rendering)
    sync_config = SyncConfig(
        syntax="cli",
        language=language,
        inject_project_additions=(path / ".invar" / "project-additions.md").exists(),
        force=False,
        check=False,
        reset=False,
        skip_patterns=skip_patterns,
    )

    result = sync_templates(path, sync_config)
    if isinstance(result, Success):
        report = result.unwrap()
        created.extend(report.created)
        merged.extend(report.updated)

    # Create proposals directory
    proposals_dir = invar_dir / "proposals"
    if not proposals_dir.exists():
        proposals_dir.mkdir()
        from invar.shell.templates import copy_template

        copy_template("proposal.md.template", proposals_dir, "TEMPLATE.md")

    # Configure MCP if Claude selected
    if "claude" in agents and selected_files.get(".mcp.json", True):
        if _configure_mcp(path):
            created.append(".mcp.json")

    # Create directories if selected
    if selected_files.get("src/core/", True):
        create_directories(path, console)

    # Install pre-commit hooks if selected
    if selected_files.get(".pre-commit-config.yaml", True):
        install_hooks(path, console)

    # Install Claude hooks if selected
    if "claude" in agents and selected_files.get(".claude/hooks/", True):
        install_claude_hooks(path, console)

    # Install Pi hooks if selected
    if "pi" in agents and selected_files.get(".pi/hooks/", True):
        install_pi_hooks(path, console)

    # Create MCP setup guide
    mcp_setup = invar_dir / "mcp-setup.md"
    if not mcp_setup.exists():
        from invar.shell.templates import _MCP_SETUP_TEMPLATE

        mcp_setup.write_text(_MCP_SETUP_TEMPLATE)

    # Track skipped files
    for file, selected in selected_files.items():
        if not selected:
            skipped.append(file)

    # Show results
    _show_execution_output(created, merged, skipped)

    # Completion message
    console.print(f"\n[bold green]✓ Initialized Invar v{__version__}[/bold green]")

    # Show agent-specific tips
    if "claude" in agents:
        console.print()
        console.print(
            Panel(
                "[dim]If you run [bold]claude /init[/bold] afterward, "
                "run [bold]invar init[/bold] again to restore protocol.[/dim]",
                title="📌 Tip",
                border_style="dim",
            )
        )
    elif "pi" in agents:
        console.print()
        console.print(
            Panel(
                "[dim]Pi reads CLAUDE.md and .claude/skills/ directly.\n"
                "Run [bold]pi[/bold] to start — USBV workflow is auto-enabled.[/dim]",
                title="📌 Tip",
                border_style="dim",
            )
        )
