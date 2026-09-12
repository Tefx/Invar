"""Exercise the installed CLI and SDK over a real MCP stdio connection."""

import asyncio
import shutil
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def _exercise_server(directory: Path) -> None:
    document = directory / "guide.md"
    document.write_text(
        "# Guide\n\n## Startup\n\nHandshake integration sentinel.\n\n"
        "## Other\n\nUnrelated content.\n",
        encoding="utf-8",
    )
    # Bind to the installed entry point in this interpreter's environment.
    executable = shutil.which("invar-tools", path=str(Path(sys.executable).parent))
    assert executable is not None, "invar-tools console entry point is missing"
    parameters = StdioServerParameters(command=executable, args=["mcp"], cwd=str(directory))
    async with asyncio.timeout(30):
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(
                reader, writer, read_timeout_seconds=timedelta(seconds=15)
            ) as session:
                initialized = await session.initialize()
                assert initialized.capabilities.tools is not None
                tools = await session.list_tools()
                assert "invar_doc_read" in {tool.name for tool in tools.tools}
                response = await session.call_tool(
                    "invar_doc_read", {"file": str(document), "section": "guide/startup"}
                )
                assert not response.isError, response
                text = "\n".join(
                    item.text for item in response.content if isinstance(item, TextContent)
                )
                assert "Handshake integration sentinel." in text
                assert "Unrelated content." not in text


def test_mcp_stdio_startup_and_document_read(tmp_path: Path) -> None:
    asyncio.run(_exercise_server(tmp_path))
