"""ASKG MCP Server Package

This package provides a Model Context Protocol (MCP) server implementation
for the ASKG (Agent-Server Knowledge Graph) project.

The MCP server allows semantic search of MCP servers stored in the Neo4j
knowledge graph database using natural language prompts.
"""

from .mcp_server import (
    ASKGMCPServer,
    ServerSearchRequest,
    ServerSearchResult,
    create_mcp_server,
)

__version__ = "1.0.0"
__author__ = "ASKG Team"

__all__ = [
    "ASKGMCPServer",
    "ServerSearchRequest",
    "ServerSearchResult",
    "create_mcp_server",
]
