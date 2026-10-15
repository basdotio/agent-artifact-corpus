"""FastMCP 2.0 Client wrapper for ArXivLens."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Client, FastMCP

logger = logging.getLogger(__name__)


class ArXivLensClient:
    """Asynchronous client wrapper to connect to and interact with the ArXivLens FastMCP server."""

    def __init__(self, target: Optional[Union[str, FastMCP]] = None) -> None:
        """Initialize ArXivLensClient.

        Args:
            target: Server target. Can be:
                - None: Defaults to the in-package FastMCP server instance.
                - FastMCP instance: For in-memory, direct testing.
                - str (file path): e.g. "src/arxivlens/server.py"
                - str (URL): e.g. "http://localhost:8000/mcp"
        """
        if target is None:
            # Import in-memory server instance by default
            from arxivlens.server import mcp as server_instance
            self._target = server_instance
        else:
            self._target = target

        self._client = Client(self._target)

    async def __aenter__(self) -> ArXivLensClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self) -> List[Any]:
        """List all tools registered on the MCP server."""
        return await self._client.list_tools()

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a specific tool on the MCP server.

        Args:
            name: The tool name (e.g., 'search_arxiv', 'generate_research_brief').
            arguments: Dictionary of arguments to pass to the tool.

        Returns:
            The tool execution result.
        """
        args = arguments or {}
        return await self._client.call_tool(name, args)

    async def list_resources(self) -> List[Any]:
        """List all resources exposed by the MCP server."""
        return await self._client.list_resources()

    async def read_resource(self, uri: str) -> Any:
        """Read the content of a resource URI from the MCP server.

        Args:
            uri: Resource URI (e.g. 'arxiv://categories' or 'paper://1706.03762/brief').

        Returns:
            The resource content.
        """
        return await self._client.read_resource(uri)

    async def list_prompts(self) -> List[Any]:
        """List all prompt templates exposed by the MCP server."""
        return await self._client.list_prompts()

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Retrieve a populated prompt template by name.

        Args:
            name: Name of the prompt (e.g., 'literature_review', 'paper_critique').
            arguments: Arguments to populate the prompt template.

        Returns:
            The generated prompt text/messages.
        """
        args = arguments or {}
        return await self._client.get_prompt(name, args)

    # High-level convenience methods
    async def search(self, query: str, max_results: int = 5, sort_by: str = "relevance") -> Any:
        """Search papers on arXiv."""
        return await self.call_tool(
            "search_arxiv",
            {"query": query, "max_results": max_results, "sort_by": sort_by},
        )

    async def get_paper(self, arxiv_id: str) -> Any:
        """Fetch full details for an arXiv paper."""
        return await self.call_tool("get_paper_details", {"arxiv_id": arxiv_id})

    async def find_code(self, arxiv_id: str, title: str = "", max_results: int = 5) -> Any:
        """Find matching GitHub repositories for a paper."""
        return await self.call_tool(
            "find_code_repositories",
            {"arxiv_id": arxiv_id, "title": title, "max_results": max_results},
        )

    async def get_brief(self, arxiv_id: str) -> Any:
        """Generate a complete research brief for an arXiv paper."""
        return await self.call_tool("generate_research_brief", {"arxiv_id": arxiv_id})
