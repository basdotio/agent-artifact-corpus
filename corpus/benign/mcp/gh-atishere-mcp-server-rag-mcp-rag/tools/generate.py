"""Generate answer with LLM tool."""

from typing import Any, Protocol

from mcp.types import TextContent

from mcp_rag.auth.jwt_handler import jwt_handler
from mcp_rag.auth.rbac import Permission, require_permission
from mcp_rag.observability.logging import get_logger, log_context
from mcp_rag.security.injection import detect_injection
from mcp_rag.security.validation import GenerateAnswerInput
from mcp_rag.tools.base import BaseTool

logger = get_logger(__name__)


class GeneratorProtocol(Protocol):
    """Interface cho Generator (gọi LLM)."""

    async def generate(
        self,
        query: str,
        context: list[str],
    ) -> str:
        ...


class GenerateAnswerTool(BaseTool):
    """Tool generate câu trả lời với LLM.

    Flow:
    1. Validate input (query + context + token)
    2. Verify JWT → user_id, role
    3. Check RBAC (READ)
    4. Check injection trên query
    5. Gọi LLM (Claude) với context
    6. Trả về answer
    """

    def __init__(self, generator: GeneratorProtocol) -> None:
        self.generator = generator

    @property
    def name(self) -> str:
        return "generate_answer"

    @property
    def description(self) -> str:
        return (
            "Generate a natural language answer to a question using "
            "provided context chunks.\n\n"
            "Use this AFTER search_documents when you have relevant chunks "
            "and need a synthesized answer.\n\n"
            "The answer will include citations in [1], [2] format "
            "referencing the context chunks.\n\n"
            "Example input: {\n"
            '  "query": "What is Kubernetes?",\n'
            '  "context": ["Kubernetes is...", "Docker is..."],\n'
            '  "token": "<JWT token>"\n'
            "}"
        )

    @property
    def input_model(self) -> type[GenerateAnswerInput]:
        return GenerateAnswerInput

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

        # ----- BƯỚC 4: CHECK INJECTION -----
        if detect_injection(params.query):
            logger.warning("injection_detected", user_id=user_id, query=params.query[:100])
            return self.error_response(
                "Query rejected: potential prompt injection detected"
            )

        # Check injection trên từng chunk (data poisoning)
        for i, chunk in enumerate(params.context):
            if detect_injection(chunk):
                logger.warning(
                    "chunk_injection_detected",
                    user_id=user_id,
                    chunk_index=i,
                )
                return self.error_response(
                    f"Context chunk {i} contains suspicious content"
                )

        # ----- BƯỚC 5: GENERATE -----
        with log_context(user_id=user_id):
            logger.info(
                "generate_started",
                query=params.query[:100],
                context_count=len(params.context),
            )

            try:
                answer = await self.generator.generate(
                    query=params.query,
                    context=params.context,
                )
            except Exception as e:
                logger.exception("generate_failed", error=str(e))
                return self.error_response(f"Generation failed: {e}")

            logger.info(
                "generate_completed",
                query=params.query[:100],
                answer_length=len(answer),
            )

            return self.success_response(self._format_answer(answer, params.context))

    def _format_answer(self, answer: str, context: list[str]) -> str:
        """Format answer + context references."""
        lines: list[str] = [
            "## Answer",
            "",
            answer,
            "",
            "## Sources",
            "",
        ]

        for i, chunk in enumerate(context, 1):
            preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
            lines.append(f"[{i}] {preview}")
            lines.append("")

        return "\n".join(lines)
