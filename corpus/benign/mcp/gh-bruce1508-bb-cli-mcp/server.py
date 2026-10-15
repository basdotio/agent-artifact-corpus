"""MCP server for bb-cli — exposes all TOOL_REGISTRY functions as MCP tools.

Start with: bb mcp-server
Claude Desktop config:
    {"mcpServers": {"bb-cli": {"command": "bb", "args": ["mcp-server"]}}}
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from bb.tools import TOOL_REGISTRY

# log_level="WARNING" suppresses FastMCP's own INFO noise to stderr.
# stdout stays clean — MCP JSON-RPC protocol uses it exclusively.
mcp = FastMCP("bb-cli", log_level="WARNING")

for _name, _fn in TOOL_REGISTRY.items():
    mcp.add_tool(_fn, name=_name)


def run() -> None:
    """Start the MCP server on stdio transport. Called by `bb mcp-server`."""
    mcp.run(transport="stdio")
