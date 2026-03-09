"""Regression tests for MCP guard changed/all flag mapping."""

from __future__ import annotations

import pytest
from mcp.types import TextContent

from invar.mcp import handlers

pytestmark = pytest.mark.anyio


async def test_run_guard_default_uses_changed_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default MCP guard call should use --changed."""
    captured: dict[str, list[str]] = {}

    async def fake_execute_command(
        cmd: list[str],
        timeout: int = 600,
    ) -> list[TextContent]:
        captured["cmd"] = cmd
        return [TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute_command)

    result = await handlers._run_guard({"path": "."})

    assert len(result) == 1
    assert "--changed" in captured["cmd"]
    assert "--all" not in captured["cmd"]


async def test_run_guard_changed_true_uses_changed_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit changed=True should use --changed."""
    captured: dict[str, list[str]] = {}

    async def fake_execute_command(
        cmd: list[str],
        timeout: int = 600,
    ) -> list[TextContent]:
        captured["cmd"] = cmd
        return [TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute_command)

    result = await handlers._run_guard({"path": ".", "changed": True})

    assert len(result) == 1
    assert "--changed" in captured["cmd"]
    assert "--all" not in captured["cmd"]


async def test_run_guard_changed_false_uses_all_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """changed=False should map to --all for full-project scans."""
    captured: dict[str, list[str]] = {}

    async def fake_execute_command(
        cmd: list[str],
        timeout: int = 600,
    ) -> list[TextContent]:
        captured["cmd"] = cmd
        return [TextContent(type="text", text="ok")]

    monkeypatch.setattr(handlers, "_execute_command", fake_execute_command)
    monkeypatch.setattr(handlers, "_should_defer_full_scan", lambda *args: False)

    result = await handlers._run_guard({"path": ".", "changed": False})

    assert len(result) == 1
    assert "--all" in captured["cmd"]
    assert "--changed" not in captured["cmd"]
