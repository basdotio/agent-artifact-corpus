"""Retrieve chunk by ID tool."""

from typing import Any, Protocol

from mcp.types import TextContent

from mcp_rag.auth.jwt_handler import jwt_handler
from mcp_rag.auth.rbac import Permission, require_permission
from mcp_rag.observability.logging import get_logger, log_context
from mcp_rag.security.validation import RetrieveChunkInput
from mcp_rag.tools.base import BaseTool

logger = get_logger(__name__)


class VectorStoreProtocol(Protocol):
    """Interface cho VectorStore."""

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        ...


class RetrieveChunkTool(BaseTool):
    """Tool lấy full content của 1 chunk theo ID.

    Flow:
    1. Validate input
    2. Verify JWT → user_id, role
    3. Check RBAC (READ)
    4. Lookup chunk by ID
    5. Format response
    """

    def __init__(self, vector_store: VectorStoreProtocol) -> None:
        self.vector_store = vector_store

    @property
    def name(self) -> str:
        return "retrieve_chunk"

    @property
    def description(self) -> str:
        return (
            "Retrieve the full content of a specific chunk by its ID.\n\n"
            "Use this when you have a chunk_id from a previous search and "
            "need the complete content (not just preview).\n\n"
            "Example input: {\n"
            '  "chunk_id": "chunk-abc-123",\n'
            '  "token": "<JWT token>"\n'
            "}"
        )

    @property
    def input_model(self) -> type[RetrieveChunkInput]:
        return RetrieveChunkInput

    async def execute(
        self,
        arguments: dict[str, Any],
        context: Any,
    ) -> list[TextContent]:
        # ----- BƯỚC 1: VALIDATE INPUT -----
        try:
            params = self.input_model(**arguments)
        except Exception as e:
            logger.warning("validation_failed", error=str(e))
            return self.error_response(f"Invalid input: {e}")

        # ----- BƯỚC 2: VERIFY JWT -----
        try:
            payload = jwt_handler.verify_token(params.token)
        except PermissionError as e:
            logger.warning("auth_failed", error=str(e))
            return self.error_response(f"Authentication failed: {e}")

        user_id: str = payload["sub"]
        role: str = payload["role"]

        # ----- BƯỚC 3: CHECK RBAC -----
        try:
            require_permission(role, Permission.READ)
        except PermissionError as e:
            logger.warning("permission_denied", user_id=user_id, error=str(e))
            return self.error_response(f"Access denied: {e}")

        # ----- BƯỚC 4: LOOKUP CHUNK -----
        with log_context(user_id=user_id):
            logger.info("retrieve_started", chunk_id=params.chunk_id)

            try:
                chunk = await self.vector_store.get_chunk(params.chunk_id)
            except Exception as e:
                logger.exception("retrieve_failed", error=str(e))
                return self.error_response(f"Retrieve failed: {e}")

            if chunk is None:
                logger.info("chunk_not_found", chunk_id=params.chunk_id)
                return self.success_response(
                    f"Chunk not found: {params.chunk_id!r}"
                )

            logger.info("retrieve_completed", chunk_id=params.chunk_id)
            return self.success_response(self._format_chunk(chunk))

    def _format_chunk(self, chunk: dict[str, Any]) -> str:
        """Format chunk thành text cho LLM."""
        lines: list[str] = [
            f"# Chunk: {chunk.get('chunk_id', 'unknown')}",
            "",
            f"**Document ID:** {chunk.get('document_id', 'unknown')}",
            f"**Chunk index:** {chunk.get('chunk_index', 'N/A')}",
            "",
            "## Content",
            "",
            chunk.get("content", ""),
            "",
        ]

        metadata = chunk.get("metadata")
        if metadata:
            lines.append("## Metadata")
            lines.append("")
            for key, value in metadata.items():
                lines.append(f"- **{key}:** {value}")

        return "\n".join(lines)
