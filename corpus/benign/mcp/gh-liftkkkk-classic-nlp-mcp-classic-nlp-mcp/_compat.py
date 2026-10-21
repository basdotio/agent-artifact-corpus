"""Compatibility shim for the `mcp` SDK major versions.

The `mcp` 2.0 release renamed ``FastMCP`` to ``MCPServer`` and *removed* the
old import path (``mcp.server.fastmcp``).  This shim lets classic-nlp-mcp run
on both 1.x and 2.x lines without forking the code base:

- mcp >= 2.0  -> ``from mcp.server.mcpserver import MCPServer``
- mcp >= 1.2  -> ``from mcp.server.fastmcp import FastMCP``

The ``@server.tool()`` decorator style and ``server.run(transport=...)`` are
unchanged between the two majors, so the rest of the code can treat the
imported object identically.
"""

from __future__ import annotations

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore[no-redef]

    MCP_SDK_MAJOR = 2
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]

    MCP_SDK_MAJOR = 1

__all__ = ["FastMCP", "MCP_SDK_MAJOR"]
