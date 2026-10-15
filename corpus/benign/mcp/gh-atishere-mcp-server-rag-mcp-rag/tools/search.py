"""Search documents tool — hybrid search với security layers."""

from typing import Any, Protocol

from mcp.types import LoggingLevel, TextContent

from mcp_rag.auth.jwt_handler import jwt_handler
from mcp_rag.auth.rbac import Permission, require_permission
from mcp_rag.observability.logging import get_logger, log_context
from mcp_rag.security.injection import detect_injection
from mcp_rag.security.validation import SearchInput
from mcp_rag.tools.base import BaseTool

logger = get_logger(__name__)


# ============================================================
# PROTOCOLS (interfaces — không cần implement thật)
# ============================================================
class VectorStoreProtocol(Protocol):
    """Interface cho VectorStore — chỉ cần có method hybrid_search."""

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ...


class RerankerProtocol(Protocol):
    """Interface cho Reranker — chỉ cần có method rerank."""

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        ...


# ============================================================
# SEARCH DOCUMENTS TOOL
# ============================================================
class SearchDocumentsTool(BaseTool):
    """Tool tìm kiếm tài liệu với hybrid search (BM25 + vector).

    Flow:
    1. Validate input (SearchInput)
    2. Verify JWT → lấy user_id, role
    3. Check RBAC (role phải có READ)
    4. Check injection trên query
    5. Hybrid search (vector + BM25)
    6. Rerank kết quả
    7. Format response
    """

    def __init__(
        self,
        vector_store: VectorStoreProtocol,
        reranker: RerankerProtocol,
    ) -> None:
        """Khởi tạo tool với dependencies.

        Args:
            vector_store: Vector store để search
            reranker: Reranker để cải thiện relevance
        """
        self.vector_store = vector_store
        self.reranker = reranker

    # ============================================================
    # PROPERTIES
    # ============================================================
    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Search documents in the knowledge base using hybrid search "
            "(BM25 + vector similarity). Returns top-k relevant chunks "
            "with metadata.\n\n"
            "Use this when you need to find information in the knowledge base.\n\n"
            "Results are reranked with a cross-encoder for improved relevance.\n\n"
            "This is read-only and safe to call multiple times.\n\n"
            "Example input: {\n"
            '  "query": "What is Kubernetes?",\n'
            '  "top_k": 5,\n'
            '  "token": "<JWT token>"\n'
            "}"
        )

    @property
    def input_model(self) -> type[SearchInput]:
        return SearchInput

    # ============================================================
    # EXECUTE
    # ============================================================
    async def execute(
        self,
        arguments: dict[str, Any],
        context: Any,
    ) -> list[TextContent]:
        """Thực thi tool search_documents.

        Args:
            arguments: Dict với query, top_k, filters, token
            context: MCP request context

        Returns:
            List[TextContent] chứa kết quả search
        """
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
            logger.warning(
                "permission_denied",
                user_id=user_id,
                role=role,
                error=str(e),
            )
            return self.error_response(f"Access denied: {e}")

        # ----- BƯỚC 4: CHECK INJECTION -----
        if detect_injection(params.query):
            logger.warning(
                "injection_detected",
                user_id=user_id,
                query=params.query[:100],
            )
            return self.error_response(
                "Query rejected: potential prompt injection detected"
            )

        # ----- BƯỚC 5-7: SEARCH + RERANK + FORMAT -----
        # Dùng log_context để tự động thêm user_id vào mọi log
        with log_context(user_id=user_id):
            # Gửi log cho client
            if context is not None:
                await context.session.send_log_message(
                    level=LoggingLevel.INFO,
                    data=f"Searching for: {params.query[:50]}...",
                )

            logger.info(
                "search_started",
                query=params.query[:100],
                top_k=params.top_k,
            )

            # ----- SEARCH -----
            try:
                # Lấy gấp đôi để rerank
                raw_results = await self.vector_store.hybrid_search(
                    query=params.query,
                    top_k=params.top_k * 2,
                    filters=params.filters,
                )
            except Exception as e:
                logger.exception("search_failed", error=str(e))
                return self.error_response(f"Search failed: {e}")

            if not raw_results:
                logger.info("search_no_results", query=params.query[:100])
                return self.success_response(
                    f"No documents found for query: {params.query!r}"
                )

            # ----- RERANK -----
            try:
                reranked = await self.reranker.rerank(
                    query=params.query,
                    documents=raw_results,
                    top_k=params.top_k,
                )
            except Exception as e:
                logger.exception("rerank_failed", error=str(e))
                # Fallback: dùng kết quả gốc
                reranked = raw_results[: params.top_k]

            # ----- FORMAT -----
            logger.info(
                "search_completed",
                query=params.query[:100],
                results_count=len(reranked),
            )

            return self.success_response(
                self._format_results(params.query, reranked)
            )

    # ============================================================
    # HELPERS
    # ============================================================
    def _format_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:
        """Format kết quả thành text cho LLM."""
        lines: list[str] = [
            f"Found {len(results)} relevant chunks for query: {query!r}",
            "",
        ]

        for i, r in enumerate(results, 1):
            chunk_id = r.get("chunk_id", "unknown")
            doc_id = r.get("document_id", "unknown")
            content = r.get("content", "")
            score = r.get("score", 0.0)

            # Cắt content nếu quá dài
            preview = content[:300] + "..." if len(content) > 300 else content

            lines.append(f"**{i}. [{doc_id}]** (score: {score:.3f})")
            lines.append(f"   chunk_id: {chunk_id}")
            lines.append(f"   {preview}")
            lines.append("")

        return "\n".join(lines)
