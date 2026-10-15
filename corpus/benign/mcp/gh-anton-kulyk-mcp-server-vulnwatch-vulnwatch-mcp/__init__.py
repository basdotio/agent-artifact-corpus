"""VulnWatch MCP server — read-mostly bridge to the VulnWatch Public Developer API."""

from .server import mcp, main

__all__ = ["mcp", "main"]
__version__ = "0.1.0"