"""
Focused regression tests for DX-93 MCP Entry Point Thickness Policy.

These tests verify:
1. MCP tool examples below and above the new 35-line threshold
2. Traditional Flask/FastAPI/Typer/Click entry points still enforced at 15 lines
3. Control cases proving genuinely thick MCP handlers still trigger violations
4. Diagnostic text differs between MCP and traditional entry points
"""

from __future__ import annotations

from invar.core.models import FileInfo, RuleConfig, Symbol, SymbolKind
from invar.core.rules import check_entry_point_thin


def _entry_symbol(name: str, line: int, end_line: int, signature: str = "") -> Symbol:
    return Symbol(
        name=name,
        kind=SymbolKind.FUNCTION,
        line=line,
        end_line=end_line,
        signature=signature,
    )


# =============================================================================
# MCP Tool Tests - Below and At Threshold
# =============================================================================


def test_mcp_tool_at_exactly_35_lines_passes() -> None:
    """MCP tool with exactly 35 lines should pass (boundary case)."""
    # 35 lines total: 1 (decorator) + 1 (def) + 33 (body) = 35
    source = """
@mcp.tool()
def tool_handler() -> dict[str, object]:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("tool_handler", line=2, end_line=36)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert violations == [], f"Expected no violations at exactly 35 lines, got {violations}"


def test_mcp_tool_at_36_lines_fails() -> None:
    """MCP tool with 36 lines should fail (just over threshold)."""
    source = """
@mcp.tool()
def tool_handler() -> dict[str, object]:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    # Line 34
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("tool_handler", line=2, end_line=37)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert violations[0].rule == "entry_point_too_thick"
    assert "max: 35" in violations[0].message


def test_mcp_tool_genuinely_thick_at_50_lines_still_triggers() -> None:
    """Control case: genuinely thick MCP tool (50 lines) should still trigger violation."""
    # Build a 50-line function body
    lines = ["    # Line " + str(i) for i in range(1, 49)]
    body = "\n".join(lines) + "\n    return {'result': 'ok'}"
    source = f"""
@mcp.tool()
def thick_tool() -> dict[str, object]:
{body}
""".lstrip()
    symbol = _entry_symbol("thick_tool", line=2, end_line=51)
    info = FileInfo(
        path="src/shell/tools.py", lines=100, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert violations[0].rule == "entry_point_too_thick"
    assert "max: 35" in violations[0].message


# =============================================================================
# Traditional Entry Point Tests - Flask/FastAPI/Typer/Click at 15
# =============================================================================


def test_flask_route_at_exactly_15_lines_passes() -> None:
    """Flask route with exactly 15 lines should pass."""
    source = """
@app.route("/")
def index() -> str:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=16)
    info = FileInfo(
        path="src/shell/web.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert violations == [], f"Expected no violations at exactly 15 lines, got {violations}"


def test_flask_route_at_16_lines_fails() -> None:
    """Flask route with 16 lines should fail."""
    source = """
@app.route("/")
def index() -> str:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/web.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "max: 15" in violations[0].message


def test_fastapi_route_enforced_at_15() -> None:
    """FastAPI route should use 15-line threshold."""
    source = """
@router.get("/health")
def health() -> dict[str, bool]:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("health", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/api.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "max: 15" in violations[0].message


def test_typer_command_enforced_at_15() -> None:
    """Typer command should use 15-line threshold."""
    source = """
@app.command()
def cli_cmd() -> int:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    return 0
""".lstrip()
    symbol = _entry_symbol("cli_cmd", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/cli.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "max: 15" in violations[0].message


def test_click_command_enforced_at_15() -> None:
    """Click command should use 15-line threshold."""
    source = """
@click.command()
def main() -> int:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    return 0
""".lstrip()
    symbol = _entry_symbol("main", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/cli.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "max: 15" in violations[0].message


# =============================================================================
# Diagnostic Text Tests - Policy Branch Differences
# =============================================================================


def test_mcp_tool_violation_message_uses_mcp_specific_term() -> None:
    """MCP tool violations should use 'MCP tool' in message."""
    source = """
@mcp.tool()
def tool() -> dict[str, object]:
    # Extra line to exceed threshold
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    # Line 34
    return {}
""".lstrip()
    symbol = _entry_symbol("tool", line=2, end_line=38)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "MCP tool" in violations[0].message


def test_traditional_entry_point_message_uses_generic_term() -> None:
    """Traditional entry point violations should use 'Entry point' in message."""
    source = """
@app.route("/")
def index() -> str:
    # Extra line
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/web.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    assert "Entry point" in violations[0].message
    assert "MCP tool" not in violations[0].message


def test_mcp_tool_suggestion_mentions_protocol_adaptation() -> None:
    """MCP tool suggestion should mention protocol adaptation context."""
    source = """
@mcp.tool()
def tool() -> dict[str, object]:
    # Extra content
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    return {}
""".lstrip()
    symbol = _entry_symbol("tool", line=2, end_line=37)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert len(violations) == 1
    # Should contain context about not extracting for line count alone
    suggestion_lower = violations[0].suggestion.lower()
    assert "protocol" in suggestion_lower or "shell" in suggestion_lower


# =============================================================================
# Edge Cases
# =============================================================================


def test_mcp_tool_with_escape_hatch_bypasses_check() -> None:
    """MCP tool with @invar:allow marker should bypass the check."""
    source = """
# @invar:allow entry_point_too_thick: Required by MCP protocol specification
@mcp.tool()
def tool() -> dict[str, object]:
    # Very long implementation that cannot be extracted
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    # Line 34
    return {}
""".lstrip()
    symbol = _entry_symbol("tool", line=3, end_line=39)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())
    assert violations == [], "Expected escape hatch to bypass check"


def test_config_custom_mcp_threshold_overrides_default() -> None:
    """Custom MCP threshold in config should override the default 35."""
    source = """
@mcp.tool()
def tool() -> dict[str, object]:
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("tool", line=2, end_line=22)
    info = FileInfo(
        path="src/shell/tools.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )
    # Default threshold is 35, this is 21 lines - should pass
    # Now test with custom threshold of 20
    config = RuleConfig(entry_point_thresholds={"mcp_tool": 20})

    violations = check_entry_point_thin(info, config)
    assert len(violations) == 1
    assert "max: 20" in violations[0].message
