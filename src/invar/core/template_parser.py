"""DX-49: Pure template parsing logic for region markers.

This module provides pure functions for parsing and reconstructing
files with Invar region markers (<!--invar:name-->...<!--/invar:name-->).

All functions are pure (no I/O) with @pre/@post contracts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from deal import ensure, post, pre

# =============================================================================
# Data Models
# =============================================================================


@dataclass
class Region:
    """A parsed region from a file with Invar markers.

    Examples:
        >>> r = Region(name="managed", start=0, end=50, content="# Header")
        >>> r.name
        'managed'
        >>> r.content
        '# Header'
    """

    name: str
    start: int
    end: int
    content: str
    version: str = ""


@dataclass
class ParsedFile:
    """Result of parsing a file with Invar region markers.

    Examples:
        >>> pf = ParsedFile(regions={}, before="", after="", raw="")
        >>> pf.has_regions
        False
    """

    regions: dict[str, Region] = field(default_factory=dict)
    before: str = ""  # Content before first marker
    after: str = ""  # Content after last marker
    raw: str = ""  # Original content

    @property
    # @invar:allow missing_contract: Boolean derived from dict length
    def has_regions(self) -> bool:
        """Check if any Invar regions were found.

        Examples:
            >>> ParsedFile(regions={"a": Region("a", 0, 10, "")}).has_regions
            True
            >>> ParsedFile(regions={}).has_regions
            False
        """
        return len(self.regions) > 0


# =============================================================================
# Region Patterns
# =============================================================================

# Patterns for region markers
# <!--invar:managed version="5.0"-->
# <!--/invar:managed-->
REGION_START_PATTERN = re.compile(
    r'<!--invar:(\w+)(?:\s+version=["\']([^"\']+)["\'])?-->'
)
REGION_END_PATTERN = re.compile(r"<!--/invar:(\w+)-->")


# =============================================================================
# Pure Parsing Functions
# =============================================================================


@post(lambda result: result.raw is not None)  # Always captures original content
@ensure(lambda content, result: result.raw == content)  # Preserves input verbatim
def parse_invar_regions(content: str) -> ParsedFile:
    """Parse <!--invar:...--> regions from content.

    Extracts named regions while preserving content before/after markers.

    Examples:
        >>> content = '''before
        ... <!--invar:managed-->
        ... managed content
        ... <!--/invar:managed-->
        ... after'''
        >>> parsed = parse_invar_regions(content)
        >>> parsed.has_regions
        True
        >>> "managed" in parsed.regions
        True
        >>> parsed.regions["managed"].content.strip()
        'managed content'
        >>> "before" in parsed.before
        True
        >>> "after" in parsed.after
        True

        >>> # No regions
        >>> parsed2 = parse_invar_regions("just plain text")
        >>> parsed2.has_regions
        False
        >>> parsed2.before
        'just plain text'
    """
    if "<!--invar:" not in content:
        return ParsedFile(raw=content, before=content)

    regions: dict[str, Region] = {}
    before = ""
    after = ""
    last_end = 0
    first_start: int | None = None

    # Find all region starts
    for start_match in REGION_START_PATTERN.finditer(content):
        region_name = start_match.group(1)
        version = start_match.group(2) or ""
        region_start = start_match.start()

        if first_start is None:
            first_start = region_start
            before = content[:region_start]

        # Find corresponding end marker
        end_pattern = re.compile(rf"<!--/invar:{region_name}-->")
        end_match = end_pattern.search(content, start_match.end())

        if end_match:
            region_content = content[start_match.end() : end_match.start()]
            regions[region_name] = Region(
                name=region_name,
                start=region_start,
                end=end_match.end(),
                content=region_content,
                version=version,
            )
            last_end = end_match.end()

    # Content after last region
    if last_end > 0:
        after = content[last_end:]

    return ParsedFile(regions=regions, before=before, after=after, raw=content)


@pre(lambda parsed, updates: all(k == v.name for k, v in parsed.regions.items()))  # Keys must match names
@ensure(lambda parsed, updates, result: (
    not parsed.has_regions or all(f"<!--invar:{r}" in result for r in parsed.regions)
))  # Checks start tag prefix (version attribute may follow)
def reconstruct_file(parsed: ParsedFile, updates: dict[str, str]) -> str:
    """Reconstruct file content with updated regions.

    Preserves:
    - Content before first marker
    - Content after last marker
    - Regions not in updates dict

    Note:
        Regions must be contiguous (no content between region end and next start).
        Content between regions is NOT preserved. This matches Invar's template
        design where regions are adjacent.

    Examples:
        >>> content = '''before
        ... <!--invar:managed-->
        ... old content
        ... <!--/invar:managed-->
        ... <!--invar:user-->
        ... user content
        ... <!--/invar:user-->
        ... after'''
        >>> parsed = parse_invar_regions(content)
        >>> result = reconstruct_file(parsed, {"managed": "NEW CONTENT"})
        >>> "NEW CONTENT" in result
        True
        >>> "user content" in result
        True
        >>> "before" in result
        True
        >>> "after" in result
        True
    """
    if not parsed.has_regions:
        # No regions - return original content
        return parsed.raw

    parts = [parsed.before]

    # Sort regions by their original position
    sorted_regions = sorted(parsed.regions.values(), key=lambda r: r.start)

    for region in sorted_regions:
        # Start marker
        if region.version:
            parts.append(f'<!--invar:{region.name} version="{region.version}"-->')
        else:
            parts.append(f"<!--invar:{region.name}-->")

        # Content - updated or original
        if region.name in updates:
            content = updates[region.name]
            # Ensure content has newlines at boundaries
            if content and not content.startswith("\n"):
                content = "\n" + content
            if content and not content.endswith("\n"):
                content = content + "\n"
            parts.append(content)
        else:
            parts.append(region.content)

        # End marker
        parts.append(f"<!--/invar:{region.name}-->")

    parts.append(parsed.after)

    return "".join(parts)


@post(lambda result: len(result) > 0)  # Always returns a syntax variant (defaults to "cli")
def get_syntax_for_command(command: str, manifest: dict) -> str:
    """Get the syntax variant for a command.

    Examples:
        >>> manifest = {"commands": {"init": {"syntax": "cli"}}}
        >>> get_syntax_for_command("init", manifest)
        'cli'
        >>> get_syntax_for_command("unknown", manifest)
        'cli'
    """
    commands = manifest.get("commands", {})
    cmd_config = commands.get(command, {})
    return cmd_config.get("syntax", "cli")


# =============================================================================
# DX-55: State Detection for Idempotent Init
# =============================================================================


@dataclass
class ClaudeMdState:
    """State of CLAUDE.md Invar regions.

    Examples:
        >>> state = ClaudeMdState(state="intact", has_managed=True, has_user=True)
        >>> state.state
        'intact'
        >>> state.needs_recovery
        False
        >>> partial = ClaudeMdState(state="partial", has_managed=True, has_user=False)
        >>> partial.needs_recovery
        True
    """

    state: str  # "intact", "partial", "missing", "absent"
    has_managed: bool = False
    has_user: bool = False
    has_project: bool = False
    version: str = ""
    user_content: str = ""  # Preserved user content

    @property
    # @invar:allow missing_contract: Boolean derived from state enum check
    def needs_recovery(self) -> bool:
        """Check if recovery/merge is needed.

        Examples:
            >>> ClaudeMdState(state="intact").needs_recovery
            False
            >>> ClaudeMdState(state="missing").needs_recovery
            True
        """
        return self.state in ("partial", "missing")


@post(lambda result: result.state in ("intact", "partial", "missing", "absent"))
def detect_claude_md_state(content: str) -> ClaudeMdState:
    """Detect the state of CLAUDE.md Invar regions.

    DX-55: Core state detection for idempotent init.

    States:
    - "intact": All required regions present and properly closed
    - "partial": Some regions present but malformed (corruption)
    - "missing": File exists but no Invar regions (overwritten by claude /init)
    - "absent": Empty content (file doesn't exist - caller handles this)

    Examples:
        >>> # Intact state
        >>> intact = '''<!--invar:managed version="5.0"-->
        ... managed content
        ... <!--/invar:managed--><!--invar:project-->
        ... <!--/invar:project--><!--invar:user-->
        ... user content
        ... <!--/invar:user-->'''
        >>> state = detect_claude_md_state(intact)
        >>> state.state
        'intact'
        >>> state.has_managed
        True
        >>> state.has_user
        True
        >>> "user content" in state.user_content
        True

        >>> # Missing state (no Invar markers)
        >>> missing = "# Project Guide\\nGenerated by Claude"
        >>> state2 = detect_claude_md_state(missing)
        >>> state2.state
        'missing'
        >>> state2.has_managed
        False

        >>> # Partial state (incomplete markers)
        >>> partial = "<!--invar:managed-->content but no close tag"
        >>> state3 = detect_claude_md_state(partial)
        >>> state3.state
        'partial'

        >>> # Absent state (empty)
        >>> state4 = detect_claude_md_state("")
        >>> state4.state
        'absent'
    """
    if not content.strip():
        return ClaudeMdState(state="absent")

    # Check for markers
    has_managed_open = "<!--invar:managed" in content
    has_managed_close = "<!--/invar:managed-->" in content
    has_user_open = "<!--invar:user-->" in content
    has_user_close = "<!--/invar:user-->" in content
    has_project_open = "<!--invar:project-->" in content
    has_project_close = "<!--/invar:project-->" in content

    # Extract version if present
    version = ""
    version_match = re.search(r'<!--invar:managed\s+version=["\']([^"\']+)["\']-->', content)
    if version_match:
        version = version_match.group(1)

    # Determine state
    managed_complete = has_managed_open and has_managed_close
    user_complete = has_user_open and has_user_close
    project_complete = has_project_open and has_project_close

    # All markers present
    any_marker = any([
        has_managed_open, has_managed_close,
        has_user_open, has_user_close,
        has_project_open, has_project_close,
    ])

    if not any_marker:
        return ClaudeMdState(state="missing")

    # Extract user content if user region is complete
    user_content = ""
    if user_complete:
        parsed = parse_invar_regions(content)
        if "user" in parsed.regions:
            user_content = parsed.regions["user"].content

    # Check if all required regions are complete
    if managed_complete and user_complete:
        return ClaudeMdState(
            state="intact",
            has_managed=True,
            has_user=True,
            has_project=project_complete,
            version=version,
            user_content=user_content,
        )

    # Some markers but not all complete - partial corruption
    return ClaudeMdState(
        state="partial",
        has_managed=managed_complete,
        has_user=user_complete,
        has_project=project_complete,
        version=version,
        user_content=user_content,
    )


@post(lambda result: "<!--invar" not in result)  # All markers removed
def strip_invar_markers(content: str) -> str:
    """Remove all Invar region markers, keeping content.

    DX-55: Used for recovering content from corrupted files.

    Examples:
        >>> content = '''<!--invar:managed-->
        ... managed content
        ... <!--/invar:managed-->
        ... <!--invar:user-->
        ... user content
        ... <!--/invar:user-->'''
        >>> cleaned = strip_invar_markers(content)
        >>> "<!--invar" in cleaned
        False
        >>> "managed content" in cleaned
        True
        >>> "user content" in cleaned
        True

        >>> # No markers
        >>> strip_invar_markers("plain text")
        'plain text'
    """
    # Remove all <!--invar:xxx--> and <!--/invar:xxx--> markers
    # Also handle version attribute
    cleaned = re.sub(r'<!--/?invar:\w+[^>]*-->', '', content)
    # Clean up excessive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


@pre(lambda content, merge_date: len(content) > 0)
@post(lambda result: "MERGED CONTENT" in result)
def format_preserved_content(content: str, merge_date: str = "") -> str:
    """Format preserved content with review markers.

    DX-55: Wraps content that was overwritten/corrupted for user review.

    Args:
        content: The content to preserve
        merge_date: ISO format date string (shell provides this)

    Examples:
        >>> content = "# Project Guide\\nSome analysis"
        >>> formatted = format_preserved_content(content, "2025-12-27")
        >>> "MERGED CONTENT" in formatted
        True
        >>> "Project Guide" in formatted
        True
        >>> "2025-12-27" in formatted
        True
    """
    date_line = f"<!-- Merge date: {merge_date} -->\n" if merge_date else ""

    return f"""<!-- ======================================== -->
<!-- MERGED CONTENT - Please review and organize -->
<!-- Original source: claude /init or manual edit -->
{date_line}<!-- ======================================== -->

## Claude Analysis (Preserved)

{content}

<!-- ======================================== -->
<!-- END MERGED CONTENT -->
<!-- ======================================== -->"""
