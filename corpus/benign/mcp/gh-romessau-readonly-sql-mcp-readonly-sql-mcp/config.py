"""Runtime configuration."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated server settings."""

    database_path: Path
    row_limit: int = 500
    query_timeout_ms: int = 5_000

    def __post_init__(self) -> None:
        if self.row_limit < 1:
            raise ValueError("row limit must be positive")
        if self.query_timeout_ms < 1:
            raise ValueError("query timeout must be positive")

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables."""
        path = os.environ.get("MCP_SQLITE_PATH")
        if not path:
            raise ValueError("MCP_SQLITE_PATH is required")
        return cls(
            database_path=Path(path),
            row_limit=int(os.environ.get("MCP_SQL_ROW_LIMIT", "500")),
            query_timeout_ms=int(os.environ.get("MCP_SQL_TIMEOUT_MS", "5000")),
        )


def parse_args(argv: list[str] | None = None) -> Settings:
    """Parse command-line arguments, falling back to environment values."""
    parser = argparse.ArgumentParser(description="Serve a SQLite database over MCP")
    parser.add_argument("--database", type=Path, default=os.environ.get("MCP_SQLITE_PATH"))
    parser.add_argument(
        "--row-limit", type=int, default=int(os.environ.get("MCP_SQL_ROW_LIMIT", "500"))
    )
    parser.add_argument(
        "--timeout-ms", type=int, default=int(os.environ.get("MCP_SQL_TIMEOUT_MS", "5000"))
    )
    args = parser.parse_args(argv)
    if args.database is None:
        parser.error("--database or MCP_SQLITE_PATH is required")
    return Settings(args.database, args.row_limit, args.timeout_ms)
