from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AU_OPENDATA_", env_file=".env")

    max_resource_bytes: int = 50 * 1024 * 1024
    upstream_timeout_seconds: float = 15.0
    head_timeout_seconds: float = 5.0
    download_timeout_seconds: float = 30.0
    resource_budget_seconds: float = 60.0

    metadata_ttl_seconds: int = 3600
    metadata_cache_max_entries: int = 5000
    materialisation_ttl_seconds: int = 86400
    cache_max_bytes: int = 1024 * 1024 * 1024
    cache_dir: Path = Path.home() / ".cache" / "au-opendata-mcp"

    duckdb_memory_limit: str = "1GB"
    max_search_limit: int = 50
    max_org_limit: int = 100
    max_preview_limit: int = 20
    max_query_limit: int = 100
    upstream_retries: int = 2
    query_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
