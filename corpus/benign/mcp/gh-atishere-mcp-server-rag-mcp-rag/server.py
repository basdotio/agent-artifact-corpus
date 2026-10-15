"""MCP Server — main entry point."""

from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_rag.config import settings
from mcp_rag.observability.logging import get_logger, setup_logging
from mcp_rag.tools.base import BaseTool
from mcp_rag.tools.cite import CiteSourcesTool, InMemoryCitationStore
from mcp_rag.tools.generate import GenerateAnswerTool
from mcp_rag.tools.retrieve import RetrieveChunkTool
from mcp_rag.tools.search import SearchDocumentsTool

logger = get_logger(__name__)


# ============================================================
# MOCK SERVICES (thay bằng real services sau)
# ============================================================
class MockVectorStore:
    """Mock vector store — trả về fake data.

    Sẽ thay bằng RealVectorStore (pgvector) sau.
    """

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Mock hybrid search."""
        return [
            {
                "chunk_id": f"chunk-{i}",
                "document_id": f"doc-{i}",
                "content": f"Mock content {i} for query: {query}",
                "score": 1.0 - i * 0.1,
            }
            for i in range(1, min(top_k, 4))
        ]

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Mock get chunk by ID."""
        return {
            "chunk_id": chunk_id,
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": f"Mock full content for chunk: {chunk_id}",
            "metadata": {"source": "mock.md"},
        }


class MockReranker:
    """Mock reranker — giữ nguyên thứ tự."""

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Mock rerank — chỉ cắt top_k."""
        return documents[:top_k]


class MockGenerator:
    """Mock LLM generator — trả về fake answer."""

    async def generate(self, query: str, context: list[str]) -> str:
        """Mock generate answer."""
        return (
            f"Based on {len(context)} context chunks, here is the answer to "
            f"{query!r}: This is a mock response. In production, this would "
            f"call Claude API."
        )


# ============================================================
# CREATE TOOLS
# ============================================================
def create_tools() -> list[BaseTool]:
    """Khởi tạo tất cả tools với mock dependencies."""
    vector_store = MockVectorStore()
    reranker = MockReranker()
    generator = MockGenerator()
    citation_store = InMemoryCitationStore()

    return [
        SearchDocumentsTool(vector_store=vector_store, reranker=reranker),
        RetrieveChunkTool(vector_store=vector_store),
        GenerateAnswerTool(generator=generator),
        CiteSourcesTool(store=citation_store),
    ]


# ============================================================
# CREATE MCP SERVER
# ============================================================
def create_server() -> Server:
    """Tạo MCP Server và đăng ký tools."""
    logger.info("creating_mcp_server", name=settings.app_name)

    app: Server = Server(settings.app_name)
    tools = create_tools()
    tools_by_name = {t.name: t for t in tools}

    logger.info("registered_tools", tool_names=list(tools_by_name.keys()))

    # ========================================================
    # HANDLER: list_tools
    # ========================================================
    @app.list_tools()
    async def list_tools() -> list[Tool]:
        """Trả về danh sách tools cho client."""
        return [t.to_mcp_tool() for t in tools]

    # ========================================================
    # HANDLER: call_tool
    # ========================================================
    @app.call_tool()
    async def call_tool(
        name: str,
        arguments: dict[str, Any],
    ) -> list[TextContent]:
        """Dispatch tool call đến tool tương ứng."""
        logger.info("tool_call_received", tool=name)

        tool = tools_by_name.get(name)
        if tool is None:
            logger.warning("unknown_tool", tool=name)
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name!r}. "
                    f"Available: {list(tools_by_name.keys())}",
                )
            ]

        try:
            # Truyền request_context (có thể None khi test)
            context = getattr(app.request_context, "_request", None)
            result = await tool.execute(arguments, context)
            return result

        except PermissionError as e:
            logger.warning("permission_denied", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Access denied: {e}")]

        except ValueError as e:
            logger.warning("invalid_input", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Invalid input: {e}")]

        except Exception as e:
            logger.exception("tool_error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Tool error: {e}")]

    return app


# ============================================================
# MAIN
# ============================================================
async def run_server() -> None:
    """Chạy MCP server với stdio transport."""
    setup_logging()

    logger.info(
        "server_starting",
        version=settings.app_version,
        environment=settings.environment,
    )

    app = create_server()

    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("server_ready", transport="stdio")
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    except Exception as e:
        logger.exception("server_failed", error=str(e))
        raise
    finally:
        logger.info("server_shutdown")


def main() -> None:
    """Entry point cho CLI `mcp-rag`."""
    import asyncio

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
