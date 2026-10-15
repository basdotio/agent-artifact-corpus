import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


@dataclass(frozen=True)
class Settings:
    MCP_SERVER_DEFAULT_PORT: int = field(
        default_factory=lambda: int(os.environ.get("MCP_SERVER_DEFAULT_PORT", "8000"))
    )
    MCP_SERVER_DEFAULT_TRANSPORT: str = field(
        default_factory=lambda: os.environ.get("MCP_SERVER_DEFAULT_TRANSPORT", "stdio")
    )
    LONG_RUNNING_TASK_FAKE_DELAY: int = field(
        default_factory=lambda: int(os.environ.get("LONG_RUNNING_TASK_FAKE_DELAY", "5"))
    )
    HTTP_REQUEST_TIMEOUT: int = field(
        default_factory=lambda: int(os.environ.get("HTTP_REQUEST_TIMEOUT", "10"))
    )
    HTTP_REQUEST_TLS_VERIFY: bool = field(
        default_factory=lambda: (
            os.environ.get("HTTP_REQUEST_TLS_VERIFY", "True").lower()
            in ["true", "1", "yes"]
        )
    )


settings = Settings()
