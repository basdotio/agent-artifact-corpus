from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TransportTypes(Enum):
    STDIO = "stdio"
    STREAMABLE_HTTP = "http"
    SSE = "sse"


class LLM_Providers(Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"


class MCP_Settings(BaseSettings):
    """
    Settings for the MCP server.
    This class uses Pydantic to manage configuration settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    LLM_PROVIDER: LLM_Providers = LLM_Providers.OPENAI
    # If provider is OPENAI, the API KEY is required.
    LLM_API_KEY: Optional[str] = Field(
        default=None,
        description="API key for the LLM provider. Required if provider is OPENAI.",
    )
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_BASE_URL: Optional[str] = None

    # Hosting config
    HOST: str = "0.0.0.0"
    PORT: int = 8888
    TRANSPORT_TYPE: TransportTypes = TransportTypes.STREAMABLE_HTTP
