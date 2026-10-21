"""Request metrics collection and structured logging."""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import uuid
import json

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Structured metrics for every MCP tool invocation."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time: float = field(default_factory=time.time)
    llm_provider: str = ""
    db_type: str = ""
    schema_cache_hit: bool = False
    sql_cache_hit: bool = False
    table_count_total: int = 0
    table_count_selected: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    db_query_time_ms: float = 0.0
    total_time_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None
    sql: Optional[str] = None
    dialect: str = ""
    row_count: int = 0
    returned_rows: int = 0
    has_more: bool = False

    def finalize(self) -> None:
        self.total_time_ms = round((time.time() - self.start_time) * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "llm_provider": self.llm_provider,
            "db_type": self.db_type,
            "dialect": self.dialect,
            "schema_cache_hit": self.schema_cache_hit,
            "sql_cache_hit": self.sql_cache_hit,
            "tables_total": self.table_count_total,
            "tables_selected": self.table_count_selected,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "db_query_time_ms": self.db_query_time_ms,
            "total_time_ms": self.total_time_ms,
            "success": self.success,
            "error": self.error,
            "row_count": self.row_count,
            "returned_rows": self.returned_rows,
            "has_more": self.has_more,
        }

    def log(self) -> None:
        self.finalize()
        logger.info("REQUEST_METRICS %s", json.dumps(self.to_dict()))
