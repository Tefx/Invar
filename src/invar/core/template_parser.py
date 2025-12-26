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
    @post(lambda result: isinstance(result, bool))
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


@pre(lambda content: isinstance(content, str))
@post(lambda result: isinstance(result, ParsedFile))
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


@pre(lambda parsed, updates: isinstance(parsed, ParsedFile) and isinstance(updates, dict))
@pre(lambda parsed, updates: all(k == v.name for k, v in parsed.regions.items()))  # Keys must match names
@post(lambda result: isinstance(result, str))
@ensure(lambda parsed, updates, result: (
    not parsed.has_regions or all(f"<!--invar:{r}-->" in result for r in parsed.regions)
))
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


@pre(lambda command, manifest: isinstance(command, str) and isinstance(manifest, dict))
@post(lambda result: isinstance(result, str))
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
