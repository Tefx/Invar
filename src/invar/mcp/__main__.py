"""
Entry point for running Invar MCP server.

Usage:
    python -m invar.mcp

This starts the MCP server using stdio transport.
"""

from invar.mcp.server import run_server

if __name__ == "__main__":
    run_server()
