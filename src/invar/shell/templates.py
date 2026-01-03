"""
Template management for invar init.

Shell module: handles file I/O for template operations.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

from returns.result import Failure, Result, Success

# =============================================================================
# Language-Specific Configurations (LX-05)
# =============================================================================

# Python configuration
_PYTHON_PYPROJECT_CONFIG = """\n# Invar Configuration
[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 500
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "test", "scripts", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"]
"""

_PYTHON_INVAR_TOML = """# Invar Configuration (Python)
# For projects without pyproject.toml

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 500
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "test", "scripts", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"]

# Pattern-based classification (optional, takes priority over paths)
# core_patterns = ["**/domain/**", "**/models/**"]
# shell_patterns = ["**/api/**", "**/cli/**"]
"""

# TypeScript configuration (LX-05)
_TYPESCRIPT_INVAR_TOML = """# Invar Configuration (TypeScript)
# For TypeScript/JavaScript projects

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 500
max_function_lines = 50
require_contracts = true
require_doctests = false  # TypeScript uses JSDoc examples instead
# TypeScript/Node.js I/O modules to forbid in Core
forbidden_imports = ["fs", "path", "http", "https", "net", "child_process", "os", "process"]
exclude_paths = ["tests", "test", "scripts", "node_modules", "dist", "build", ".next", "coverage"]

# Pattern-based classification (optional, takes priority over paths)
# core_patterns = ["**/domain/**", "**/models/**"]
# shell_patterns = ["**/api/**", "**/cli/**"]
"""

# Backward compatibility alias
_DEFAULT_PYPROJECT_CONFIG = _PYTHON_PYPROJECT_CONFIG
_DEFAULT_INVAR_TOML = _PYTHON_INVAR_TOML


def _get_invar_config(language: str) -> str:
    """Get the appropriate config content for the language."""
    if language == "typescript":
        return _TYPESCRIPT_INVAR_TOML
    return _PYTHON_INVAR_TOML


def get_template_path(name: str) -> Result[Path, str]:
    """Get path to a template file."""
    try:
        path = Path(str(resources.files("invar.templates").joinpath(name)))
        if not path.exists():
            return Failure(f"Template '{name}' not found")
        return Success(path)
    except Exception as e:
        return Failure(f"Failed to get template path: {e}")


# @shell_complexity: Template copy with path resolution
def copy_template(
    template_name: str, dest: Path, dest_name: str | None = None
) -> Result[bool, str]:
    """Copy a template file to destination. Returns Success(True) if copied, Success(False) if skipped."""
    if dest_name is None:
        dest_name = template_name.replace(".template", "")
    dest_file = dest / dest_name
    if dest_file.exists():
        return Success(False)
    template_result = get_template_path(template_name)
    if isinstance(template_result, Failure):
        return template_result
    template_path = template_result.unwrap()
    try:
        dest_file.write_text(template_path.read_text())
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to copy template: {e}")


# @shell_complexity: Config addition with existing file detection
def add_config(path: Path, console, language: str = "python") -> Result[bool, str]:
    """Add configuration to project. Returns Success(True) if added, Success(False) if skipped.

    DX-70: Creates .invar/config.toml instead of invar.toml for cleaner organization.
    LX-05: Now generates language-specific config (Python vs TypeScript).
    Backward compatible: still reads from invar.toml if it exists.
    """
    pyproject = path / "pyproject.toml"
    invar_dir = path / ".invar"
    invar_config = invar_dir / "config.toml"
    legacy_invar_toml = path / "invar.toml"

    try:
        # Priority 1: Add to pyproject.toml if it exists (Python projects only)
        if pyproject.exists() and language == "python":
            content = pyproject.read_text()
            if "[tool.invar]" not in content:
                with pyproject.open("a") as f:
                    f.write(_DEFAULT_PYPROJECT_CONFIG)
                console.print("[green]Added[/green] [tool.invar.guard] to pyproject.toml")
                return Success(True)
            return Success(False)

        # Skip if legacy invar.toml exists (backward compatibility)
        if legacy_invar_toml.exists():
            return Success(False)

        # Create .invar/config.toml (DX-70: new default location)
        # LX-05: Use language-specific config
        if not invar_config.exists():
            invar_dir.mkdir(exist_ok=True)
            invar_config.write_text(_get_invar_config(language))
            console.print("[green]Created[/green] .invar/config.toml")
            return Success(True)

        return Success(False)
    except OSError as e:
        return Failure(f"Failed to add config: {e}")


def create_directories(path: Path, console) -> None:
    """Create src/core and src/shell directories."""
    core_path = path / "src" / "core"
    shell_path = path / "src" / "shell"

    if not core_path.exists():
        core_path.mkdir(parents=True)
        (core_path / "__init__.py").touch()
        console.print("[green]Created[/green] src/core/")

    if not shell_path.exists():
        shell_path.mkdir(parents=True)
        (shell_path / "__init__.py").touch()
        console.print("[green]Created[/green] src/shell/")


# @shell_complexity: Directory copy with file filtering
def copy_examples_directory(dest: Path, console) -> Result[bool, str]:
    """Copy examples directory to .invar/examples/. Returns Success(True) if copied."""
    import shutil

    examples_dest = dest / ".invar" / "examples"
    if examples_dest.exists():
        return Success(False)

    try:
        examples_src = Path(str(resources.files("invar.templates").joinpath("examples")))
        if not examples_src.exists():
            return Failure("Examples template directory not found")

        # Create .invar if needed
        invar_dir = dest / ".invar"
        if not invar_dir.exists():
            invar_dir.mkdir()

        shutil.copytree(examples_src, examples_dest)
        console.print("[green]Created[/green] .invar/examples/ (reference examples)")
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to copy examples: {e}")


# @shell_complexity: Directory copy for Claude commands (DX-32)
def copy_commands_directory(dest: Path, console) -> Result[bool, str]:
    """Copy commands directory to .claude/commands/. Returns Success(True) if copied."""
    import shutil

    commands_dest = dest / ".claude" / "commands"
    if commands_dest.exists():
        return Success(False)

    try:
        commands_src = Path(str(resources.files("invar.templates").joinpath("commands")))
        if not commands_src.exists():
            return Failure("Commands template directory not found")

        # Create .claude if needed
        claude_dir = dest / ".claude"
        if not claude_dir.exists():
            claude_dir.mkdir()

        shutil.copytree(commands_src, commands_dest)
        console.print("[green]Created[/green] .claude/commands/ (Claude Code skills)")
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to copy commands: {e}")


# @shell_complexity: Directory copy for Claude skills (DX-36)
def copy_skills_directory(dest: Path, console) -> Result[bool, str]:
    """Copy skills directory to .claude/skills/. Returns Success(True) if copied."""
    import shutil
    skills_dest = dest / ".claude" / "skills"
    if skills_dest.exists():
        return Success(False)
    try:
        skills_src = Path(str(resources.files("invar.templates").joinpath("skills")))
        if not skills_src.exists():
            return Failure("Skills template directory not found")
        (dest / ".claude").mkdir(exist_ok=True)
        shutil.copytree(skills_src, skills_dest)
        console.print("[green]Created[/green] .claude/skills/ (workflow skills)")
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to copy skills: {e}")


# Agent configuration - Claude Code only (DX-69: simplified, cursor/aider removed)
AGENT_CONFIGS = {
    "claude": {
        "file": "CLAUDE.md",
        "template": "CLAUDE.md.template",
        "check_pattern": "INVAR.md",
    },
}


# @shell_complexity: Multi-agent config detection with file existence checks
def detect_agent_configs(path: Path) -> Result[dict[str, str], str]:
    """
    Detect existing agent configuration files.

    Returns dict of agent -> status where status is one of:
    - "configured": File exists and contains Invar reference
    - "found": File exists but no Invar reference
    - "not_found": File does not exist

    >>> from pathlib import Path
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     result = detect_agent_configs(Path(tmp))
    ...     result.unwrap()["claude"]
    'not_found'
    """
    try:
        results = {}
        for agent, config in AGENT_CONFIGS.items():
            config_path = path / config["file"]
            if config_path.exists():
                content = config_path.read_text()
                if config["check_pattern"] in content:
                    results[agent] = "configured"
                else:
                    results[agent] = "found"
            else:
                results[agent] = "not_found"
        return Success(results)
    except OSError as e:
        return Failure(f"Failed to detect agent configs: {e}")


# @shell_complexity: MCP server config with JSON manipulation
def configure_mcp_server(path: Path, console) -> Result[list[str], str]:
    """
    Configure MCP server for AI agents (DX-16).

    Creates:
    - .invar/mcp-server.json (universal config)
    - .invar/mcp-setup.md (manual setup instructions)
    - Updates .claude/settings.json if .claude/ exists

    Returns list of configured agents.
    """
    import json

    configured: list[str] = []
    invar_dir = path / ".invar"

    # Ensure .invar exists
    if not invar_dir.exists():
        invar_dir.mkdir()

    # MCP config using current Python (the one that has invar installed)
    import sys

    mcp_config = {
        "name": "invar",
        "command": sys.executable,
        "args": ["-m", "invar.mcp"],
    }

    # 1. Create .mcp.json at project root (Claude Code standard)
    mcp_json_path = path / ".mcp.json"
    if not mcp_json_path.exists():
        mcp_json_content = {
            "mcpServers": {
                "invar": {
                    "command": mcp_config["command"],
                    "args": mcp_config["args"],
                }
            }
        }
        mcp_json_path.write_text(json.dumps(mcp_json_content, indent=2))
        console.print("[green]Created[/green] .mcp.json (MCP server config)")
        configured.append("Claude Code")
    else:
        # Check if invar is already configured
        try:
            existing = json.loads(mcp_json_path.read_text())
            if "mcpServers" in existing and "invar" in existing.get("mcpServers", {}):
                console.print("[dim]Skipped[/dim] .mcp.json (invar already configured)")
            else:
                # Add invar to existing config
                if "mcpServers" not in existing:
                    existing["mcpServers"] = {}
                existing["mcpServers"]["invar"] = {
                    "command": mcp_config["command"],
                    "args": mcp_config["args"],
                }
                mcp_json_path.write_text(json.dumps(existing, indent=2))
                console.print("[green]Updated[/green] .mcp.json (added invar)")
            configured.append("Claude Code")
        except (OSError, json.JSONDecodeError):
            console.print("[yellow]Warning[/yellow] .mcp.json exists but couldn't update")

    # 2. Create setup instructions (for reference)
    mcp_setup = invar_dir / "mcp-setup.md"
    if not mcp_setup.exists():
        mcp_setup.write_text(_MCP_SETUP_TEMPLATE)
        console.print("[green]Created[/green] .invar/mcp-setup.md (setup guide)")

    return Success(configured)


_MCP_SETUP_TEMPLATE = """\
# Invar MCP Server Setup

This project includes an MCP server that provides Invar tools to AI agents.

## Available Tools

| Tool | Replaces | Purpose |
|------|----------|---------|
| `invar_guard` | `pytest`, `crosshair` | Smart Guard verification |
| `invar_sig` | `Read` entire file | Show contracts and signatures |
| `invar_map` | `Grep` for functions | Symbol map with reference counts |

## Configuration

`invar init` automatically creates `.mcp.json` with smart detection of available methods.

### Recommended: uvx (isolated environment)

```json
{
  "mcpServers": {
    "invar": {
      "command": "uvx",
      "args": ["invar-tools", "mcp"]
    }
  }
}
```

### Alternative: invar command

```json
{
  "mcpServers": {
    "invar": {
      "command": "invar",
      "args": ["mcp"]
    }
  }
}
```

### Fallback: Python path

```json
{
  "mcpServers": {
    "invar": {
      "command": "/path/to/your/.venv/bin/python",
      "args": ["-m", "invar.mcp"]
    }
  }
}
```

Find your Python path: `python -c "import sys; print(sys.executable)"`

## Installation

```bash
# Recommended: use uvx (no installation needed)
uvx invar-tools guard

# Or install globally
pip install invar-tools

# Or install in project
pip install invar-tools
```

## Testing

Run the MCP server directly:

```bash
# Using uvx
uvx invar-tools mcp

# Or if installed
invar mcp
```

The server communicates via stdio and should be managed by your AI agent.
"""


# @shell_complexity: Git hooks installation with backup
def install_hooks(path: Path, console) -> Result[bool, str]:
    """Run 'pre-commit install' if config exists (file created by sync_templates)."""
    import subprocess

    pre_commit_config = path / ".pre-commit-config.yaml"

    if not pre_commit_config.exists():
        # File should be created by sync_templates; skip if missing
        return Success(False)

    # Auto-install hooks (Automatic > Opt-in)
    try:
        subprocess.run(
            ["pre-commit", "install"],
            cwd=path,
            check=True,
            capture_output=True,
        )
        console.print("[green]Installed[/green] pre-commit hooks")
        return Success(True)
    except FileNotFoundError:
        console.print("[dim]Run: pre-commit install (pre-commit not in PATH)[/dim]")
    except subprocess.CalledProcessError:
        console.print("[dim]Run: pre-commit install (not a git repo?)[/dim]")

    return Success(False)
