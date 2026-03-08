from __future__ import annotations

from invar.core.entry_points import get_entry_point_kind, is_entry_point
from invar.core.models import Symbol, SymbolKind


def _symbol(name: str, line: int = 2) -> Symbol:
    return Symbol(name=name, kind=SymbolKind.FUNCTION, line=line, end_line=line + 1)


def test_classifies_mcp_tool_entry_point_kind() -> None:
    source = """
@mcp.tool()
def table_wait(table_id: str) -> dict[str, object]:
    return {"ok": True}
""".lstrip()
    symbol = _symbol("table_wait")

    assert get_entry_point_kind(symbol, source) == "mcp_tool"
    assert is_entry_point(symbol, source) is True


def test_classifies_flask_fastapi_typer_click_as_traditional() -> None:
    cases = [
        (
            "index",
            """
@app.route("/")
def index() -> str:
    return "ok"
""".lstrip(),
        ),
        (
            "health",
            """
@router.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
""".lstrip(),
        ),
        (
            "cli",
            """
@app.command()
def cli() -> int:
    return 0
""".lstrip(),
        ),
        (
            "main",
            """
@click.command()
def main() -> int:
    return 0
""".lstrip(),
        ),
    ]

    for name, source in cases:
        symbol = _symbol(name)
        assert get_entry_point_kind(symbol, source) == "traditional"
        assert is_entry_point(symbol, source) is True


def test_entry_marker_is_traditional_kind() -> None:
    source = """
# @shell:entry - legacy callback
def handler(payload: dict[str, object]) -> dict[str, object]:
    return payload
""".lstrip()
    symbol = _symbol("handler", line=2)

    assert get_entry_point_kind(symbol, source) == "traditional"
    assert is_entry_point(symbol, source) is True


def test_non_entry_point_kind_is_none_and_boolean_is_false() -> None:
    source = """
def compute(value: int) -> int:
    return value * 2
""".lstrip()
    symbol = Symbol(name="compute", kind=SymbolKind.FUNCTION, line=1, end_line=2)

    assert get_entry_point_kind(symbol, source) is None
    assert is_entry_point(symbol, source) is False
