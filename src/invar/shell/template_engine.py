"""DX-49: Template engine with I/O operations and Jinja2 support.

This module provides:
- File update with region preservation
- Jinja2 template rendering
- Manifest loading

Pure parsing logic is in core/template_parser.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from deal import pre
from returns.result import Failure, Result, Success

# Import pure logic from Core
from invar.core.template_parser import (
    ParsedFile,
    Region,
    get_syntax_for_command,
    parse_invar_regions,
    reconstruct_file,
)

# Re-export for convenience
__all__ = [
    "ParsedFile",
    "Region",
    "generate_from_manifest",
    "get_syntax_for_command",
    "get_templates_dir",
    "is_invar_project",
    "load_manifest",
    "parse_invar_regions",
    "reconstruct_file",
    "render_template",
    "render_template_file",
    "update_file_with_regions",
]


# =============================================================================
# File Update Logic
# =============================================================================


# @shell_complexity: File handling requires branching for exists/has_regions/new_project cases
@pre(lambda path, new_managed: isinstance(path, Path) and isinstance(new_managed, str))
def update_file_with_regions(
    path: Path,
    new_managed: str,
    new_project: str | None = None,
) -> Result[str, str]:
    """Update file preserving user regions and unmarked content.

    Args:
        path: File path to update
        new_managed: New content for managed region
        new_project: New content for project region (sync-self only)

    Returns:
        Success with updated content, or Failure with error message

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     _ = f.write('''<!--invar:managed-->
        ... old
        ... <!--/invar:managed-->
        ... <!--invar:user-->
        ... keep this
        ... <!--/invar:user-->''')
        ...     path = Path(f.name)
        >>> result = update_file_with_regions(path, "NEW")
        >>> isinstance(result, Success)
        True
        >>> "NEW" in result.unwrap()
        True
        >>> "keep this" in result.unwrap()
        True
        >>> path.unlink()  # cleanup
    """
    if not path.exists():
        # New file - just wrap in managed region
        content = f"<!--invar:managed-->\n{new_managed}\n<!--/invar:managed-->\n"
        if new_project:
            content += f"\n<!--invar:project-->\n{new_project}\n<!--/invar:project-->\n"
        content += "\n<!--invar:user-->\n\n<!--/invar:user-->\n"
        return Success(content)

    try:
        current = path.read_text()
    except OSError as e:
        return Failure(f"Failed to read {path}: {e}")

    parsed = parse_invar_regions(current)

    if not parsed.has_regions:
        # No markers - insert at top, preserve rest
        content = f"<!--invar:managed-->\n{new_managed}\n<!--/invar:managed-->\n\n"
        content += current
        return Success(content)

    # Build updates dict
    updates: dict[str, str] = {"managed": new_managed}
    if new_project is not None and "project" in parsed.regions:
        updates["project"] = new_project

    result = reconstruct_file(parsed, updates)
    return Success(result)


# =============================================================================
# Jinja2 Template Rendering
# =============================================================================


def render_template(
    template_content: str,
    variables: dict[str, str],
) -> Result[str, str]:
    """Render a Jinja2 template with given variables.

    Args:
        template_content: Jinja2 template string
        variables: Variables to inject (syntax, version, project_name, etc.)

    Returns:
        Success with rendered content, or Failure with error

    Examples:
        >>> result = render_template("Hello {{ name }}", {"name": "World"})
        >>> result.unwrap()
        'Hello World'

        >>> result = render_template("{% if x %}yes{% endif %}", {"x": True})
        >>> result.unwrap()
        'yes'
    """
    try:
        from jinja2 import BaseLoader, Environment, StrictUndefined

        env = Environment(
            loader=BaseLoader(),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        template = env.from_string(template_content)
        rendered = template.render(**variables)
        return Success(rendered)
    except ImportError:
        return Failure("Jinja2 not installed. Run: pip install jinja2")
    except Exception as e:
        return Failure(f"Template rendering failed: {e}")


def render_template_file(
    template_path: Path,
    variables: dict[str, str],
) -> Result[str, str]:
    """Render a Jinja2 template file with {% include %} support.

    Uses FileSystemLoader to resolve includes relative to templates directory.

    Examples:
        >>> from pathlib import Path
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile(mode='w', suffix='.jinja', delete=False) as f:
        ...     _ = f.write("Version: {{ version }}")
        ...     path = Path(f.name)
        >>> result = render_template_file(path, {"version": "5.0"})
        >>> result.unwrap()
        'Version: 5.0'
        >>> path.unlink()
    """
    try:
        from jinja2 import Environment, FileSystemLoader, StrictUndefined

        # Use FileSystemLoader for {% include %} support (LX-05)
        templates_dir = get_templates_dir()
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

        # Get template path relative to templates directory
        try:
            rel_path = template_path.relative_to(templates_dir)
            template = env.get_template(str(rel_path))
        except ValueError:
            # Template is not in templates_dir, fall back to direct rendering
            content = template_path.read_text()
            template = env.from_string(content)

        rendered = template.render(**variables)
        return Success(rendered)
    except OSError as e:
        return Failure(f"Failed to read template {template_path}: {e}")
    except ImportError:
        return Failure("Jinja2 not installed. Run: pip install jinja2")
    except Exception as e:
        return Failure(f"Template rendering failed: {e}")


# =============================================================================
# Manifest Loading
# =============================================================================


# @shell_complexity: TOML loading with Python version fallback (tomllib vs tomli)
def load_manifest(templates_dir: Path) -> Result[dict, str]:
    """Load manifest.toml from templates directory.

    Examples:
        >>> from pathlib import Path
        >>> # Will fail if manifest doesn't exist
        >>> result = load_manifest(Path("/nonexistent"))
        >>> isinstance(result, Failure)
        True
    """
    manifest_path = templates_dir / "manifest.toml"

    if not manifest_path.exists():
        return Failure(f"Manifest not found: {manifest_path}")

    try:
        import tomllib

        content = manifest_path.read_text()
        data = tomllib.loads(content)
        return Success(data)
    except ImportError:
        # Python < 3.11
        try:
            import tomli as tomllib  # type: ignore

            content = manifest_path.read_text()
            data = tomllib.loads(content)
            return Success(data)
        except ImportError:
            return Failure("tomllib/tomli not available")
    except Exception as e:
        return Failure(f"Failed to parse manifest: {e}")


# =============================================================================
# Template Generation
# =============================================================================


def get_templates_dir() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent.parent / "templates"


# @shell_complexity: Template generation has multiple paths for copy/jinja/copy_dir types
def generate_from_manifest(
    dest_root: Path,
    syntax: str = "cli",
    files_to_generate: list[str] | None = None,
) -> Result[list[str], str]:
    """Generate files from manifest.toml templates.

    Args:
        dest_root: Destination project root
        syntax: "cli" or "mcp" for command syntax
        files_to_generate: Optional list of files to generate (None = all from manifest)

    Returns:
        Success with list of generated files, or Failure with error
    """
    templates_dir = get_templates_dir()
    manifest_result = load_manifest(templates_dir)
    if isinstance(manifest_result, Failure):
        return manifest_result

    manifest = manifest_result.unwrap()
    templates = manifest.get("templates", {})
    # Copy to avoid mutating cached manifest
    variables = {**manifest.get("variables", {}), "syntax": syntax}

    generated: list[str] = []

    for dest_path, config in templates.items():
        # Skip if not in files_to_generate list
        if files_to_generate is not None and dest_path not in files_to_generate:
            continue

        src = config.get("src", "")
        template_type = config.get("type", "copy")
        src_path = templates_dir / src

        # Resolve destination
        full_dest = dest_root / dest_path

        # Ensure parent directories exist
        full_dest.parent.mkdir(parents=True, exist_ok=True)

        if template_type == "copy":
            # Direct file copy
            if not src_path.exists():
                continue
            if full_dest.exists():
                continue  # Don't overwrite existing
            try:
                full_dest.write_text(src_path.read_text())
                generated.append(dest_path)
            except OSError as e:
                print(f"Warning: Failed to copy {dest_path}: {e}", file=sys.stderr)
                continue

        elif template_type == "jinja":
            # Jinja2 template rendering
            if not src_path.exists():
                continue
            if full_dest.exists():
                continue  # Don't overwrite existing
            result = render_template_file(src_path, variables)
            if isinstance(result, Success):
                try:
                    full_dest.write_text(result.unwrap())
                    generated.append(dest_path)
                except OSError as e:
                    print(f"Warning: Failed to write {dest_path}: {e}", file=sys.stderr)
                    continue

        elif template_type == "copy_dir":
            # Directory copy
            if not src_path.exists() or not src_path.is_dir():
                continue
            if full_dest.exists():
                continue  # Don't overwrite existing directory
            try:
                import shutil
                shutil.copytree(src_path, full_dest)
                generated.append(dest_path)
            except OSError as e:
                print(f"Warning: Failed to copy directory {dest_path}: {e}", file=sys.stderr)
                continue

    return Success(generated)


# =============================================================================
# Utility Functions
# =============================================================================


def is_invar_project(project_root: Path) -> bool:
    """Check if this is the Invar project itself.

    The Invar project has special handling via sync-self.

    Examples:
        >>> from pathlib import Path
        >>> is_invar_project(Path("/some/random/project"))
        False
    """
    # Check for Invar-specific markers
    invar_markers = [
        project_root / "src" / "invar" / "__init__.py",
        project_root / "runtime" / "src" / "invar_runtime" / "__init__.py",
    ]
    return all(marker.exists() for marker in invar_markers)
