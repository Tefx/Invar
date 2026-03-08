from __future__ import annotations

from invar.core.models import FileInfo, RuleConfig, Symbol, SymbolKind
from invar.core.rules import check_entry_point_thin, check_shell_result
from invar.core.utils import parse_guard_config


def _entry_symbol(name: str, line: int, end_line: int, signature: str = "") -> Symbol:
    return Symbol(
        name=name,
        kind=SymbolKind.FUNCTION,
        line=line,
        end_line=end_line,
        signature=signature,
    )


def test_mcp_entry_point_uses_default_35_line_threshold() -> None:
    source = """
@mcp.tool()
def tool_handler() -> dict[str, object]:
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("tool_handler", line=2, end_line=36)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    assert check_entry_point_thin(info, RuleConfig()) == []


def test_traditional_entry_point_keeps_default_15_line_threshold() -> None:
    source = """
@app.route("/")
def index() -> str:
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/web.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())

    assert len(violations) == 1
    assert violations[0].rule == "entry_point_too_thick"
    assert "max: 15" in violations[0].message


def test_global_entry_max_lines_is_fallback_when_kind_threshold_missing() -> None:
    source = """
@mcp.tool()
def tool_handler() -> dict[str, object]:
    return {"ok": True}
""".lstrip()
    symbol = _entry_symbol("tool_handler", line=2, end_line=22)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )
    config = RuleConfig(entry_max_lines=20, entry_point_thresholds={})

    violations = check_entry_point_thin(info, config)

    assert len(violations) == 1
    assert "max: 20" in violations[0].message


def test_parse_guard_config_reads_entry_threshold_fields() -> None:
    config = parse_guard_config(
        {
            "entry_max_lines": 19,
            "entry_point_thresholds": {"mcp_tool": 44},
        }
    )

    assert config.entry_max_lines == 19
    assert config.entry_point_thresholds["mcp_tool"] == 44


def test_shell_result_rule_behavior_is_unchanged_for_entry_points() -> None:
    source = """
@app.route("/")
def index() -> str:
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=4, signature="() -> str")
    info = FileInfo(
        path="src/shell/web.py", lines=20, symbols=[symbol], is_shell=True, source=source
    )

    assert check_shell_result(info, RuleConfig()) == []


# DX-93: MCP-specific diagnostic message tests
def test_mcp_tool_violation_contains_mcp_specific_guidance() -> None:
    """MCP tool violations should explain MCP-specific policy."""
    source = """
@mcp.tool()
def tool_handler() -> dict[str, object]:
    # A very long tool handler with business logic that should be extracted
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
    # Line 35 - this makes it 36 lines, exceeding 35
    return {"result": "ok"}
""".lstrip()
    symbol = _entry_symbol("tool_handler", line=2, end_line=37)
    info = FileInfo(
        path="src/shell/tools.py", lines=80, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())

    assert len(violations) == 1
    assert violations[0].rule == "entry_point_too_thick"
    assert "MCP tool" in violations[0].message
    assert "max: 35" in violations[0].message
    # MCP-specific guidance should discourage single-use helper extraction
    assert (
        "business logic" in violations[0].suggestion.lower()
        or "Shell function" in violations[0].suggestion
    )
    assert (
        "single-use" in violations[0].suggestion.lower()
        or "protocol adaptation" in violations[0].suggestion.lower()
    )


def test_traditional_entry_point_violation_uses_original_message() -> None:
    """Traditional entry points should keep original message format."""
    source = """
@app.route("/")
def index() -> str:
    # A very long route handler
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
    # Line 15 - this makes it 16 lines, exceeding 15
    return "ok"
""".lstrip()
    symbol = _entry_symbol("index", line=2, end_line=17)
    info = FileInfo(
        path="src/shell/web.py", lines=60, symbols=[symbol], is_shell=True, source=source
    )

    violations = check_entry_point_thin(info, RuleConfig())

    assert len(violations) == 1
    assert violations[0].rule == "entry_point_too_thick"
    assert "Entry point" in violations[0].message
    assert "max: 15" in violations[0].message
    # Traditional should keep original suggestion format
    assert "# @invar:allow entry_point_too_thick:" in violations[0].suggestion
