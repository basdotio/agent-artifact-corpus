"""Input validation với Pydantic."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from mcp_rag.config import settings


class SearchInput(BaseModel):
    """Input cho tool search_documents."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_query_length,
        description="Câu truy vấn tìm kiếm",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=settings.max_top_k,
        description="Số lượng kết quả trả về",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Bộ lọc metadata (VD: {\"source\": \"k8s.md\"})",
    )
    token: str = Field(
        ...,
        min_length=10,
        description="JWT token để xác thực",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Chuẩn hóa query và kiểm tra."""
        # Strip whitespace
        v = v.strip()

        # Không được rỗng sau khi strip
        if not v:
            raise ValueError("Query không được rỗng")

        # Không được chỉ có ký tự đặc biệt
        if not any(c.isalnum() for c in v):
            raise ValueError("Query phải chứa ít nhất 1 ký tự chữ/số")

        return v

    @field_validator("filters")
    @classmethod
    def validate_filters(
        cls, v: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Giới hạn số lượng filters và key length."""
        if v is None:
            return None

        # Tối đa 10 filters
        if len(v) > 10:
            raise ValueError("Tối đa 10 filters")

        # Key không được quá dài
        for key in v:
            if not isinstance(key, str) or len(key) > 50:
                raise ValueError(f"Filter key không hợp lệ: {key}")

        return v


class RetrieveChunkInput(BaseModel):
    """Input cho tool retrieve_chunk."""

    chunk_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID của chunk cần lấy",
    )
    token: str = Field(..., min_length=10)

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
        """Chunk ID chỉ chứa chữ, số, dấu gạch."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Chunk ID chỉ được chứa chữ, số, dấu gạch ngang/gạch dưới"
            )
        return v


class GenerateAnswerInput(BaseModel):
    """Input cho tool generate_answer."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_query_length,
    )
    context: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Danh sách chunks dùng làm context",
    )
    token: str = Field(..., min_length=10)

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: list[str]) -> list[str]:
        """Mỗi chunk không quá 10000 ký tự."""
        for i, chunk in enumerate(v):
            if len(chunk) > 10000:
                raise ValueError(
                    f"Chunk {i} quá dài (tối đa 10000 ký tự)"
                )
        return v


class CiteSourcesInput(BaseModel):
    """Input cho tool cite_sources."""

    answer_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    token: str = Field(..., min_length=10)
