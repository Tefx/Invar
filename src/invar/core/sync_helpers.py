"""
DX-56: Pure sync helper functions.

Core module: Pure logic for template sync operations.
No I/O - only data transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from deal import post, pre

if TYPE_CHECKING:
    from invar.core.template_parser import ParsedFile


# =============================================================================
# Data Types
# =============================================================================


# LX-05: Valid language values for template rendering
VALID_LANGUAGES = frozenset({"python", "typescript"})


@dataclass
class SyncConfig:
    """Configuration for template sync operation.

    Examples:
        >>> config = SyncConfig()
        >>> config.syntax
        'cli'
        >>> config.language
        'python'
        >>> config.inject_project_additions
        False

        >>> config = SyncConfig(syntax="mcp", language="typescript", force=True)
        >>> config.syntax
        'mcp'
        >>> config.language
        'typescript'
        >>> config.force
        True

        >>> config = SyncConfig(skip_patterns=[".claude/skills/*"])
        >>> config.skip_patterns
        ['.claude/skills/*']
    """

    syntax: str = "cli"  # "cli" or "mcp"
    language: str = "python"  # "python" or "typescript" (LX-05)
    inject_project_additions: bool = False
    force: bool = False
    check: bool = False  # Preview only
    reset: bool = False  # Discard user content
    skip_patterns: list[str] = field(default_factory=list)  # Glob patterns to skip

    @post(lambda result: result is None)  # Void method, validates or raises
    def __post_init__(self) -> None:
        """Validate configuration values.

        Examples:
            >>> SyncConfig(language="python")  # Valid
            SyncConfig(syntax='cli', language='python', inject_project_additions=False, force=False, check=False, reset=False, skip_patterns=[])

            >>> SyncConfig(language="rust")  # doctest: +IGNORE_EXCEPTION_DETAIL
            Traceback (most recent call last):
            ValueError: Invalid language 'rust'. Must be one of: python, typescript
        """
        if self.language not in VALID_LANGUAGES:
            valid = ", ".join(sorted(VALID_LANGUAGES))
            msg = f"Invalid language '{self.language}'. Must be one of: {valid}"
            raise ValueError(msg)


@dataclass
class SyncReport:
    """Result of sync operation.

    Examples:
        >>> report = SyncReport()
        >>> report.created
        []
        >>> len(report.updated)
        0

        >>> report = SyncReport(created=["INVAR.md"], updated=["CLAUDE.md"])
        >>> report.created
        ['INVAR.md']
    """

    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Manifest Helpers
# =============================================================================


@pre(lambda path, patterns: len(path) > 0 and isinstance(patterns, list))
@post(lambda result: isinstance(result, bool))
def should_skip_file(path: str, patterns: list[str]) -> bool:
    """Check if path should be skipped based on skip patterns.

    Examples:
        >>> should_skip_file(".claude/skills/develop/SKILL.md", [".claude/skills/*"])
        True
        >>> should_skip_file("CLAUDE.md", [".claude/skills/*"])
        False
        >>> should_skip_file("INVAR.md", [])
        False
    """
    return any(matches_glob_pattern(path, pattern) for pattern in patterns)


@pre(lambda path, pattern: len(path) > 0 and len(pattern) > 0)
@post(lambda result: isinstance(result, bool))
def matches_glob_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a simple glob pattern with *.

    Examples:
        >>> matches_glob_pattern(".claude/skills/develop/SKILL.md", ".claude/skills/*/SKILL.md")
        True
        >>> matches_glob_pattern(".claude/skills/review/SKILL.md", ".claude/skills/*/SKILL.md")
        True
        >>> matches_glob_pattern("CLAUDE.md", ".claude/skills/*/SKILL.md")
        False
        >>> matches_glob_pattern("INVAR.md", "INVAR.md")
        True
    """
    if "*" not in pattern:
        return path == pattern

    parts = pattern.split("*")
    if len(parts) != 2:
        return False

    prefix, suffix = parts
    return path.startswith(prefix) and path.endswith(suffix)


@pre(lambda manifest: "templates" in manifest or "sync" in manifest)
@post(lambda result: isinstance(result, tuple) and len(result) == 3)
def get_sync_file_lists(
    manifest: dict,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    """Extract file lists from manifest for sync operations.

    Returns:
        Tuple of (fully_managed, region_managed, create_only) file lists.
        - fully_managed: List of (dest, src) tuples for full overwrite
        - region_managed: List of (dest, src) tuples for region-based updates
        - create_only: List of destination paths created once

    Examples:
        >>> manifest = {
        ...     "sync": {
        ...         "fully_managed": ["INVAR.md"],
        ...         "region_managed": ["CLAUDE.md"],
        ...         "create_only": [".invar/context.md"],
        ...     },
        ...     "templates": {
        ...         "INVAR.md": {"src": "protocol/INVAR.md", "type": "copy"},
        ...         "CLAUDE.md": {"src": "config/CLAUDE.md.jinja", "type": "jinja"},
        ...     }
        ... }
        >>> fm, rm, co = get_sync_file_lists(manifest)
        >>> len(fm)
        1
        >>> fm[0][0]
        'INVAR.md'
    """
    sync_config = manifest.get("sync", {})
    templates = manifest.get("templates", {})

    fully_managed = []
    for dest in sync_config.get("fully_managed", []):
        if dest in templates:
            fully_managed.append((dest, templates[dest].get("src", "")))

    region_managed = []
    for dest in sync_config.get("region_managed", []):
        if dest in templates:
            region_managed.append((dest, templates[dest].get("src", "")))
        elif "*" in dest:
            # Handle glob patterns like ".claude/skills/*/SKILL.md"
            for template_dest, template_config in templates.items():
                if matches_glob_pattern(template_dest, dest):
                    region_managed.append((template_dest, template_config.get("src", "")))

    create_only = sync_config.get("create_only", [])

    return fully_managed, region_managed, create_only


@pre(lambda manifest, file_path: "regions" in manifest and len(file_path) > 0)
def get_region_config(manifest: dict, file_path: str) -> dict[str, dict] | None:
    """Get region configuration for a file from manifest.

    Examples:
        >>> manifest = {
        ...     "regions": {
        ...         "CLAUDE.md": {
        ...             "managed": {"action": "overwrite"},
        ...             "user": {"action": "preserve"},
        ...         }
        ...     }
        ... }
        >>> config = get_region_config(manifest, "CLAUDE.md")
        >>> config["managed"]["action"]
        'overwrite'
        >>> get_region_config(manifest, "unknown.md") is None
        True
    """
    regions = manifest.get("regions", {})

    # Direct match
    if file_path in regions:
        return regions[file_path]

    # Glob pattern match
    for pattern, config in regions.items():
        if matches_glob_pattern(file_path, pattern):
            return config

    return None


@pre(lambda parsed: hasattr(parsed, "regions"))
def detect_region_scheme(parsed: ParsedFile) -> tuple[str, str] | None:
    """Detect the region scheme from parsed file.

    Returns (primary_region, user_region) or None if no known scheme.

    Examples:
        >>> from invar.core.template_parser import ParsedFile, Region
        >>> p = ParsedFile(regions={"managed": Region("managed", 0, 10, "")})
        >>> detect_region_scheme(p)
        ('managed', 'user')
        >>> p2 = ParsedFile(regions={"skill": Region("skill", 0, 10, "")})
        >>> detect_region_scheme(p2)
        ('skill', 'extensions')
        >>> p3 = ParsedFile(regions={})
        >>> detect_region_scheme(p3) is None
        True
    """
    # Known schemes
    schemes = {
        "managed": ("managed", "user"),
        "skill": ("skill", "extensions"),
    }

    for primary, scheme in schemes.items():
        if primary in parsed.regions:
            return scheme

    return None
