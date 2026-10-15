"""Interchangeable direct and real MCP transports for the same document tools."""

from __future__ import annotations

import asyncio
import copy
import json
import sys
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import Protocol, Self

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .documents import TOOL_DEFINITIONS, DocumentStore, ToolError


class Gateway(Protocol):
    async def call(self, name: str, arguments: dict) -> dict: ...
    async def list_tools(self) -> list[dict]: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...


class LocalGateway:
    """In-process baseline, with exactly the same tool semantics as MCP."""

    def __init__(self, data_dir: Path):
        self.store = DocumentStore(data_dir)
        self.metadata = {"transport": "local", "server": "docagent-document-tools"}

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def call(self, name: str, arguments: dict) -> dict:
        return await asyncio.to_thread(self.store.call, name, arguments)

    async def list_tools(self) -> list[dict]:
        return copy.deepcopy(TOOL_DEFINITIONS)


class MCPGateway:
    """Launch and negotiate with an isolated official-SDK stdio tool process.

    Only transport metadata is recorded. API credentials, request text, and
    private machine paths are never placed in that metadata.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).resolve()
        self.session: ClientSession | None = None
        self._stack: AsyncExitStack | None = None
        self.metadata: dict = {"transport": "mcp-stdio"}

    async def __aenter__(self) -> Self:
        if self._stack is not None:
            raise ToolError("MCP gateway is already connected.")
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "docagent.mcp_server", "--data-dir", str(self.data_dir)],
                # SDK retains its minimal platform environment; no model secrets.
                env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PYTHONIOENCODING": "utf-8"},
            )
            read_stream, write_stream = await stack.enter_async_context(stdio_client(parameters))
            self.session = await stack.enter_async_context(ClientSession(read_stream, write_stream, read_timeout_seconds=timedelta(seconds=30)))
            initialized = await self.session.initialize()
            self.metadata.update({"protocol_version": initialized.protocolVersion,
                                  "server": initialized.serverInfo.name,
                                  "server_version": initialized.serverInfo.version,
                                  "capabilities": initialized.capabilities.model_dump(exclude_none=True)})
            self._stack = stack
            return self
        except BaseException:
            self.session = None
            await stack.aclose()
            raise

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        stack, self._stack = self._stack, None
        self.session = None
        if stack is not None:
            await stack.__aexit__(exc_type, exc, traceback)

    def _connected(self) -> ClientSession:
        if self.session is None:
            raise ToolError("MCP gateway must be used inside an async context manager.")
        return self.session

    async def list_tools(self) -> list[dict]:
        try:
            response = await self._connected().list_tools()
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError("MCP tool discovery failed.") from exc
        definitions = [tool.model_dump(exclude_none=True) for tool in response.tools]
        self.metadata["tool_names"] = [tool["name"] for tool in definitions]
        return definitions

    async def call(self, name: str, arguments: dict) -> dict:
        try:
            response = await self._connected().call_tool(name, arguments=arguments)
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError("MCP tool request failed.") from exc
        if response.isError:
            details = " ".join(block.text for block in response.content if block.type == "text")
            raise ToolError(details or "MCP tool execution failed.")
        result: dict = {}
        images = []
        for block in response.content:
            if block.type == "text":
                try:
                    parsed = json.loads(block.text)
                except json.JSONDecodeError as exc:
                    raise ToolError("MCP tool returned malformed JSON metadata.") from exc
                if not isinstance(parsed, dict):
                    raise ToolError("MCP tool returned non-object metadata.")
                result.update(parsed)
            elif block.type == "image":
                images.append({"data": block.data, "mimeType": block.mimeType})
        if images or name in ("get_image", "get_table_image", "get_page_images"):
            result["images"] = images
        return result


__all__ = ["Gateway", "LocalGateway", "MCPGateway", "ToolError"]
