"""OKF MCP Server implementation.

This module contains the main OKF MCP Server class that provides
tools for MCP clients. It uses FastMCP to register and manage MCP capabilities.
"""

from fastmcp import FastMCP

from okf_mcp_server.src.settings import settings

# Import tools from the tools package
from okf_mcp_server.src.tools.browse_knowledge_tool import browse_knowledge
from okf_mcp_server.src.tools.get_knowledge_tool import get_knowledge
from okf_mcp_server.src.tools.search_knowledge_tool import search_knowledge
from okf_mcp_server.utils.pylogger import (
    force_reconfigure_all_loggers,
    get_python_logger,
)

logger = get_python_logger()


class OKFMCPServer:
    """OKF MCP Server: retrieval tools over published OKF knowledge snapshots.

    This server provides only tools, not resources or prompts, adhering to
    the tools-first architectural pattern for MCP servers.
    """

    def __init__(self):
        """Initialize the MCP server with knowledge tools following tools-first architecture."""
        try:
            # Initialize FastMCP server
            self.mcp = FastMCP("okf-knowledge")

            # Force reconfigure all loggers after FastMCP initialization to ensure structured logging
            force_reconfigure_all_loggers(settings.PYTHON_LOG_LEVEL)

            self._register_mcp_tools()

            logger.info("OKF MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OKF MCP Server: {e}")
            raise

    def _register_mcp_tools(self) -> None:
        """Register MCP tools for knowledge retrieval (tools-first architecture).

        Registers all available tools with the FastMCP server instance.
        In tools-first architecture, the server only provides tools.
        Currently includes:
        - browse_knowledge: Progressive disclosure over the bundle hierarchy
        - search_knowledge: Keyword search over passages with trust signals
        - get_knowledge: Read a concept or section with provenance
        """
        self.mcp.tool()(browse_knowledge)
        self.mcp.tool()(search_knowledge)
        self.mcp.tool()(get_knowledge)
