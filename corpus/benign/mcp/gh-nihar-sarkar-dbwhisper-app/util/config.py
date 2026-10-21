from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    """Application configuration with backward compatibility and new tuning knobs."""

    # LLM Provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "azure")
    LLM_PROVIDER_FALLBACK: str = os.getenv("LLM_PROVIDER_FALLBACK", "")

    # OpenAI / ChatGPT
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Azure OpenAI / Azure AI
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    AZURE_OPENAI_DEPLOYMENT_ID: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_ID", "")

    # Kimi (Moonshot AI)
    KIMI_API_KEY: str = os.getenv("KIMI_API_KEY", "")
    KIMI_BASE_URL: str = os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    KIMI_MODEL: str = os.getenv("KIMI_MODEL", "moonshot-v1-8k")

    # Claude (Anthropic)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # AWS Bedrock
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    # Database
    DB_TYPE: str = os.getenv("DB_TYPE", "postgresql")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "public")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/app.db")

    # Domain Context
    DOMAIN_CONTEXT_DIR: str = os.getenv("DOMAIN_CONTEXT_DIR", "./context")

    # Server
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "3004"))

    # Performance & Caching
    SCHEMA_CACHE_TTL: int = int(os.getenv("SCHEMA_CACHE_TTL", "3600"))
    SQL_CACHE_ENABLED: bool = os.getenv("SQL_CACHE_ENABLED", "true").lower() == "true"
    CONVERSATION_ENABLED: bool = os.getenv("CONVERSATION_ENABLED", "true").lower() == "true"
    MAX_RESULT_ROWS: int = int(os.getenv("MAX_RESULT_ROWS", "100"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    CIRCUIT_BREAKER_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "5"))
    CIRCUIT_BREAKER_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60"))
    EXPLAIN_MAX_COST: float = float(os.getenv("EXPLAIN_MAX_COST", "100000"))

    # Legacy backward compatibility
    @property
    def MODEL_URL(self) -> str:
        return self.AZURE_OPENAI_ENDPOINT

    @property
    def MODEL_API_KEY(self) -> str:
        return self.AZURE_OPENAI_API_KEY

    @property
    def MODEL_API_VERSION(self) -> str:
        return self.AZURE_OPENAI_API_VERSION

    @property
    def MODEL_NAME(self) -> str:
        return self.AZURE_OPENAI_DEPLOYMENT_ID


settings = Settings()
