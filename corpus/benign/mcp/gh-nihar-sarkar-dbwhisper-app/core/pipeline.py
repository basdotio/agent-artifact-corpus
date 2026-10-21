"""Composable pipeline architecture for query processing."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from app.core.metrics import RequestMetrics

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Mutable context passed through every pipeline stage."""
    user_query: str
    thread_id: Optional[str] = None
    full_schema: List[Dict[str, Any]] = field(default_factory=list)
    selected_schema: List[Dict[str, Any]] = field(default_factory=list)
    schema_json: str = ""
    domain_context: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    generated_sql: str = ""
    validated_sql: str = ""
    result: List[Dict[str, Any]] = field(default_factory=list)
    output: str = ""
    metrics: RequestMetrics = field(default_factory=RequestMetrics)
    error: Optional[str] = None
    db: Any = None
    llm_client: Any = None
    schema_cache_hit: bool = False
    sql_cache_hit: bool = False


class PipelineStage(ABC):
    """Base class for all pipeline stages."""

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> None:
        """Execute the stage. Mutates ctx in place. Raises on fatal error."""
        pass


class PipelineRunner:
    """Executes a list of stages sequentially, stopping on first error."""

    @staticmethod
    async def run(stages: List[PipelineStage], ctx: PipelineContext) -> None:
        for stage in stages:
            if ctx.error:
                break
            try:
                await stage.run(ctx)
            except Exception as e:
                ctx.error = str(e)
                logger.exception("Pipeline stage failed: %s", stage.__class__.__name__)
