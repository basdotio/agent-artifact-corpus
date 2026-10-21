"""Concrete pipeline stages for the query processing pipeline."""

import json
import logging
import re
import hashlib
import os
from typing import Optional

from app.core.pipeline import PipelineStage, PipelineContext
from app.services.db_factory import DatabaseFactory
from app.services.llm_factory import LLMFactory
from app.services.schema_rag import SchemaRAG
from app.services.domain_context import load_domain_context, DomainContextRAG
from app.services.sql_validator import SQLValidator
from app.services.sql_cache import SQLCache
from app.core.cache import SchemaCache
from app.util.config import settings

logger = logging.getLogger(__name__)

schema_cache = SchemaCache()
sql_cache = SQLCache()


class ConnectDatabaseStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        ctx.db = DatabaseFactory.get_database(settings.DB_TYPE)
        await ctx.db.connect()
        ctx.metrics.db_type = settings.DB_TYPE


class LoadSchemaStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        cached = schema_cache.read(settings.DB_TYPE, settings.DB_SCHEMA, ttl=settings.SCHEMA_CACHE_TTL)
        if cached:
            ctx.full_schema = cached
            ctx.metrics.schema_cache_hit = True
            logger.info("Schema loaded from cache")
        else:
            ctx.full_schema = await ctx.db.get_schema_metadata()
            schema_cache.write(settings.DB_TYPE, settings.DB_SCHEMA, ctx.full_schema)
            ctx.metrics.schema_cache_hit = False
            logger.info("Schema introspected from database")
        ctx.metrics.table_count_total = len(ctx.full_schema)


class SelectSchemaStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        rag = SchemaRAG(top_k=settings.RAG_TOP_K)
        ctx.selected_schema = rag.select(ctx.full_schema, ctx.user_query)
        ctx.schema_json = json.dumps(ctx.selected_schema, indent=2)
        ctx.metrics.table_count_selected = len(ctx.selected_schema)


class LoadDomainContextStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        if settings.DOMAIN_CONTEXT_DIR and os.path.exists(settings.DOMAIN_CONTEXT_DIR):
            rag = DomainContextRAG(settings.DOMAIN_CONTEXT_DIR)
            ctx.domain_context = rag.retrieve(ctx.user_query, top_k=3)
            if not ctx.domain_context:
                ctx.domain_context = await load_domain_context(settings.DOMAIN_CONTEXT_DIR)
        else:
            ctx.domain_context = ""


class CheckSQLCacheStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        if not settings.SQL_CACHE_ENABLED:
            return
        schema_hash = hashlib.md5(ctx.schema_json.encode()).hexdigest()
        cached_sql = sql_cache.get(schema_hash, ctx.user_query)
        if cached_sql:
            ctx.generated_sql = cached_sql
            ctx.metrics.sql_cache_hit = True
            logger.info("SQL loaded from cache")


class GenerateSQLStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        if ctx.generated_sql:
            return  # cache hit

        llm_client = LLMFactory.get_client(settings.LLM_PROVIDER)
        dialect = ctx.db.get_dialect_name()
        ctx.metrics.llm_provider = settings.LLM_PROVIDER
        ctx.metrics.dialect = dialect

        response = await llm_client.generate_sql(ctx.schema_json, ctx.domain_context, ctx.user_query, dialect)
        ctx.generated_sql = response.content
        ctx.metrics.prompt_tokens = response.usage.get("prompt_tokens", 0) if response.usage else 0
        ctx.metrics.completion_tokens = response.usage.get("completion_tokens", 0) if response.usage else 0

        if settings.SQL_CACHE_ENABLED:
            schema_hash = hashlib.md5(ctx.schema_json.encode()).hexdigest()
            sql_cache.put(schema_hash, ctx.user_query, ctx.generated_sql)


class ValidateSQLStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        sql = ctx.generated_sql
        sql_clean = extract_sql_from_markdown(sql)
        if sql_clean:
            sql = sql_clean
        ctx.generated_sql = sql

        # AST validation
        result = SQLValidator.validate(sql, max_cost=settings.EXPLAIN_MAX_COST)
        if not result["valid"]:
            ctx.error = f"SQL validation failed: {result['error']}"
            return

        for w in result.get("warnings", []):
            logger.warning("SQL warning: %s", w)

        # EXPLAIN cost check
        cost_result = await SQLValidator.check_cost(ctx.db, sql, max_cost=settings.EXPLAIN_MAX_COST)
        if not cost_result["valid"]:
            ctx.error = cost_result["error"]
            return

        ctx.validated_sql = sql


class ExecuteSQLStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        import time
        t0 = time.time()
        ctx.result = await ctx.db.execute_query(ctx.validated_sql, limit=settings.MAX_RESULT_ROWS)
        ctx.metrics.db_query_time_ms = round((time.time() - t0) * 1000, 2)
        ctx.metrics.row_count = len(ctx.result)
        ctx.metrics.returned_rows = min(len(ctx.result), settings.MAX_RESULT_ROWS)
        ctx.metrics.has_more = len(ctx.result) >= settings.MAX_RESULT_ROWS


class FormatOutputStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        output = {
            "sql": ctx.validated_sql,
            "results": ctx.result,
            "meta": {
                "row_count": ctx.metrics.row_count,
                "returned": ctx.metrics.returned_rows,
                "has_more": ctx.metrics.has_more,
                "execution_time_ms": ctx.metrics.db_query_time_ms,
                "schema_tables_total": ctx.metrics.table_count_total,
                "schema_tables_selected": ctx.metrics.table_count_selected,
                "schema_cache_hit": ctx.metrics.schema_cache_hit,
                "sql_cache_hit": ctx.metrics.sql_cache_hit,
                "llm_provider": ctx.metrics.llm_provider,
                "dialect": ctx.metrics.dialect,
            }
        }
        ctx.output = json.dumps(output, indent=2, default=str)


class DisconnectDatabaseStage(PipelineStage):
    async def run(self, ctx: PipelineContext) -> None:
        if ctx.db:
            try:
                await ctx.db.disconnect()
            except Exception:
                pass


def extract_sql_from_markdown(text: str) -> Optional[str]:
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
