"""Cite sources tool — retrieve citations for a generated answer."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from mcp.types import TextContent
from pydantic import BaseModel, Field

from mcp_rag.auth.jwt_handler import jwt_handler
from mcp_rag.auth.rbac import Permission, require_permission
from mcp_rag.observability.logging import get_logger, log_context
from mcp_rag.tools.base import BaseTool

logger = get_logger(__name__)


# ============================================================
# INPUT MODEL
# ============================================================
class CiteSourcesInput(BaseModel):
    """Input cho tool cite_sources."""

    answer_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID của answer cần lấy citations",
    )
    token: str = Field(..., min_length=10, description="JWT token")


# ============================================================
# CITATION STORE (in-memory, production dùng Redis)
# ============================================================
@dataclass
class Citation:
    """1 citation record."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    created_at: float = field(default_factory=time.time)


class CitationStoreProtocol(Protocol):
    """Interface cho CitationStore."""

    async def store(
        self,
        answer_id: str,
        citations: list[Citation],
    ) -> None:
        ...

    async def get(self, answer_id: str) -> list[Citation] | None:
        ...


class InMemoryCitationStore:
    """In-memory citation store — chỉ dùng cho dev/test.

    Production nên dùng Redis hoặc PostgreSQL.
    """

    def __init__(self, max_entries: int = 10000) -> None:
        self._store: dict[str, list[Citation]] = {}
        self._max_entries = max_entries

    async def store(
        self,
        answer_id: str,
        citations: list[Citation],
    ) -> None:
        """Lưu citations cho answer_id."""
        # Cleanup nếu quá lớn (simple LRU)
        if len(self._store) >= self._max_entries:
            # Xóa 10% entries cũ nhất
            oldest = sorted(
                self._store.items(),
                key=lambda kv: max(c.created_at for c in kv[1]),
            )[: self._max_entries // 10]
            for key, _ in oldest:
                del self._store[key]

        self._store[answer_id] = citations

    async def get(self, answer_id: str) -> list[Citation] | None:
        """Lấy citations theo answer_id."""
        return self._store.get(answer_id)


# ============================================================
# CITE SOURCES TOOL
# ============================================================
class CiteSourcesTool(BaseTool):
    """Tool lấy citations cho một answer.

    Flow:
    1. Validate input
    2. Verify JWT + RBAC
    3. Lookup citations
    4. Format response
    """

    def __init__(self, store: CitationStoreProtocol) -> None:
        self.store = store

    @property
    def name(self) -> str:
        return "cite_sources"

    @property
    def description(self) -> str:
        return (
            "Retrieve citations (source chunks) for a previously generated "
            "answer.\n\n"
            "Use this when you need to show the user WHERE the answer came "
            "from, with links to original documents.\n\n"
            "Example input: {\n"
            '  "answer_id": "ans-abc-123",\n'
            '  "token": "<JWT token>"\n'
            "}"
        )

    @property
    def input_model(self) -> type[CiteSourcesInput]:
        return CiteSourcesInput

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

        # ----- BƯỚC 4: LOOKUP CITATIONS -----
        with log_context(user_id=user_id):
            logger.info("cite_started", answer_id=params.answer_id)

            try:
                citations = await self.store.get(params.answer_id)
            except Exception as e:
                logger.exception("cite_lookup_failed", error=str(e))
                return self.error_response(f"Citation lookup failed: {e}")

            if citations is None:
                logger.info("citations_not_found", answer_id=params.answer_id)
                return self.success_response(
                    f"No citations found for answer_id: {params.answer_id!r}"
                )

            if not citations:
                return self.success_response(
                    f"Answer {params.answer_id!r} has no citations"
                )

            logger.info(
                "cite_completed",
                answer_id=params.answer_id,
                citation_count=len(citations),
            )

            return self.success_response(
                self._format_citations(params.answer_id, citations)
            )

    def _format_citations(
        self,
        answer_id: str,
        citations: list[Citation],
    ) -> str:
        """Format citations thành text."""
        lines: list[str] = [
            f"# Citations for answer: {answer_id}",
            "",
            f"**Total:** {len(citations)} source(s)",
            "",
        ]

        for i, c in enumerate(citations, 1):
            preview = (
                c.content[:250] + "..."
                if len(c.content) > 250
                else c.content
            )
            lines.append(f"## [{i}] Document: {c.document_id}")
            lines.append(f"- **Chunk ID:** `{c.chunk_id}`")
            lines.append(f"- **Relevance score:** {c.score:.3f}")
            lines.append("")
            lines.append(f"{preview}")
            lines.append("")

        return "\n".join(lines)


# ============================================================
# HELPER: Tạo answer_id
# ============================================================
def new_answer_id() -> str:
    """Tạo answer ID mới."""
    return f"ans-{uuid.uuid4().hex[:12]}"


# Singleton store
citation_store = InMemoryCitationStore()
