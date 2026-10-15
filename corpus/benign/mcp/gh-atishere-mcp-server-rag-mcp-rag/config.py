"""Configuration settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    # ==========================================================
    # APP
    # ==========================================================
    app_name: str = "mcp-server-rag"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    debug: bool = False

    # ==========================================================
    # AUTH
    # ==========================================================
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_expiry_minutes: int = Field(30, ge=5, le=1440)

    # ==========================================================
    # DATABASE
    # ==========================================================
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/db"
    db_pool_size: int = Field(10, ge=1, le=100)
    db_max_overflow: int = Field(20, ge=0, le=100)
    db_echo: bool = False

    # ==========================================================
    # REDIS
    # ==========================================================
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = Field(50, ge=1, le=500)
    cache_ttl_seconds: int = Field(3600, ge=60)

    # ==========================================================
    # RAG ENGINE
    # ==========================================================
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = Field(384, ge=64, le=4096)
    embedding_batch_size: int = Field(32, ge=1, le=256)

    chunk_size: int = Field(512, ge=128, le=2048)
    chunk_overlap: int = Field(50, ge=0, le=512)

    top_k: int = Field(10, ge=1, le=100)
    rerank_top_k: int = Field(5, ge=1, le=50)

    # CRAG
    crag_enabled: bool = True
    crag_correct_threshold: float = Field(0.8, ge=0.0, le=1.0)
    crag_incorrect_threshold: float = Field(0.3, ge=0.0, le=1.0)
    crag_max_retries: int = Field(1, ge=0, le=3)

    # ==========================================================
    # LLM (Optional)
    # ==========================================================
    anthropic_api_key: str | None = None
    llm_model: str = "claude-3-5-sonnet-20241022"
    llm_max_tokens: int = Field(2048, ge=1, le=8192)
    llm_temperature: float = Field(0.0, ge=0.0, le=1.0)

    # ==========================================================
    # SECURITY ← ĐÂY LÀ 2 FIELD BỊ THIẾU
    # ==========================================================
    rate_limit_per_minute: int = Field(60, ge=1, le=10000)
    rate_limit_burst: int = Field(10, ge=1, le=100)
    max_query_length: int = Field(500, ge=10, le=5000)      # ← Field 1
    max_top_k: int = Field(50, ge=1, le=200)                # ← Field 2

    # ==========================================================
    # OBSERVABILITY
    # ==========================================================
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "mcp-server-rag"
    metrics_enabled: bool = True

    # ==========================================================
    # PYDANTIC CONFIG
    # ==========================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================
    # PROPERTIES
    # ==========================================================
    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_url_safe(self) -> str:
        """Database URL đã ẩn password (để log)."""
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", self.database_url)


# ============================================================
# SINGLETON
# ============================================================
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
