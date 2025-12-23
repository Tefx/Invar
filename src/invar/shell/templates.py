"""
Template management for invar init.

Shell module: handles file I/O for template operations.
"""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

from returns.result import Failure, Result, Success

_DEFAULT_PYPROJECT_CONFIG = """\n# Invar Configuration
[tool.invar.guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "scripts", ".venv"]
"""

_DEFAULT_INVAR_TOML = """# Invar Configuration
# For projects without pyproject.toml

[guard]
core_paths = ["src/core"]
shell_paths = ["src/shell"]
max_file_lines = 300
max_function_lines = 50
require_contracts = true
require_doctests = true
forbidden_imports = ["os", "sys", "socket", "requests", "urllib", "subprocess", "shutil", "io", "pathlib"]
exclude_paths = ["tests", "scripts", ".venv"]

# Pattern-based classification (optional, takes priority over paths)
# core_patterns = ["**/domain/**", "**/models/**"]
# shell_patterns = ["**/api/**", "**/cli/**"]
"""


def get_template_path(name: str) -> Result[Path, str]:
    """Get path to a template file."""
    try:
        path = Path(str(resources.files("invar.templates").joinpath(name)))
        if not path.exists():
            return Failure(f"Template '{name}' not found")
        return Success(path)
    except Exception as e:
        return Failure(f"Failed to get template path: {e}")


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


def add_config(path: Path, console) -> Result[bool, str]:
    """Add configuration to project. Returns Success(True) if added, Success(False) if skipped."""
    pyproject = path / "pyproject.toml"
    invar_toml = path / "invar.toml"

    try:
        if pyproject.exists():
            content = pyproject.read_text()
            if "[tool.invar]" not in content:
                with pyproject.open("a") as f:
                    f.write(_DEFAULT_PYPROJECT_CONFIG)
                console.print("[green]Added[/green] [tool.invar.guard] to pyproject.toml")
                return Success(True)
            return Success(False)

        if not invar_toml.exists():
            invar_toml.write_text(_DEFAULT_INVAR_TOML)
            console.print("[green]Created[/green] invar.toml")
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


# Agent configuration for multi-agent support (DX-11, DX-17)
AGENT_CONFIGS = {
    "claude": {
        "file": "CLAUDE.md",
        "template": "CLAUDE.md.template",
        "reference": '> **Protocol:** Follow [INVAR.md](./INVAR.md) for the Invar development methodology.\n',
        "check_pattern": "INVAR.md",
    },
    "cursor": {
        "file": ".cursorrules",
        "template": "cursorrules.template",
        "reference": "Follow the Invar Protocol in INVAR.md.\n\n",
        "check_pattern": "INVAR.md",
    },
    "aider": {
        "file": ".aider.conf.yml",
        "template": "aider.conf.yml.template",
        "reference": "# Follow the Invar Protocol in INVAR.md\nread:\n  - INVAR.md\n",
        "check_pattern": "INVAR.md",
    },
}


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


def add_invar_reference(path: Path, agent: str, console) -> Result[bool, str]:
    """Add Invar reference to an existing agent config file."""
    if agent not in AGENT_CONFIGS:
        return Failure(f"Unknown agent: {agent}")

    config = AGENT_CONFIGS[agent]
    config_path = path / config["file"]

    if not config_path.exists():
        return Failure(f"Config file not found: {config['file']}")

    try:
        content = config_path.read_text()
        if config["check_pattern"] in content:
            return Success(False)  # Already configured

        # Prepend reference
        new_content = config["reference"] + content
        config_path.write_text(new_content)
        console.print(f"[green]Updated[/green] {config['file']} (added Invar reference)")
        return Success(True)
    except OSError as e:
        return Failure(f"Failed to update {config['file']}: {e}")


def create_agent_config(path: Path, agent: str, console) -> Result[bool, str]:
    """
    Create agent config from template (DX-17).

    Creates full template file for agents that don't have an existing config.
    """
    if agent not in AGENT_CONFIGS:
        return Failure(f"Unknown agent: {agent}")

    config = AGENT_CONFIGS[agent]
    config_path = path / config["file"]

    if config_path.exists():
        return Success(False)  # Already exists

    # Use template if available
    template_name = config.get("template")
    if template_name:
        result = copy_template(template_name, path, config["file"])
        if isinstance(result, Success) and result.unwrap():
            console.print(f"[green]Created[/green] {config['file']} (Invar workflow enforcement)")
            return Success(True)
        elif isinstance(result, Failure):
            return result

    return Success(False)


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


def install_hooks(path: Path, console) -> Result[bool, str]:
    """Install pre-commit hooks configuration and activate them."""
    import subprocess

    pre_commit_config = path / ".pre-commit-config.yaml"

    if pre_commit_config.exists():
        console.print("[yellow]Skipped[/yellow] .pre-commit-config.yaml (already exists)")
        return Success(False)

    result = copy_template("pre-commit-config.yaml.template", path, ".pre-commit-config.yaml")
    if isinstance(result, Failure):
        return result

    if result.unwrap():
        console.print("[green]Created[/green] .pre-commit-config.yaml")

        # Auto-install hooks (Automatic > Opt-in)
        try:
            subprocess.run(
                ["pre-commit", "install"],
                cwd=path,
                check=True,
                capture_output=True,
            )
            console.print("[green]Installed[/green] pre-commit hooks")
        except FileNotFoundError:
            console.print("[dim]Run: pre-commit install (pre-commit not in PATH)[/dim]")
        except subprocess.CalledProcessError:
            console.print("[dim]Run: pre-commit install (not a git repo?)[/dim]")

        return Success(True)

    return Success(False)
