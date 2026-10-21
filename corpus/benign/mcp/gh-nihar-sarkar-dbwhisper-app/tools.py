"""MCP tools with pipeline-based query processing."""

import json
import logging
from app.core.pipeline import PipelineContext, PipelineRunner
from app.core.metrics import RequestMetrics
from app.services.pipeline_stages import (
    ConnectDatabaseStage,
    LoadSchemaStage,
    SelectSchemaStage,
    LoadDomainContextStage,
    CheckSQLCacheStage,
    GenerateSQLStage,
    ValidateSQLStage,
    ExecuteSQLStage,
    FormatOutputStage,
    DisconnectDatabaseStage,
)
from app.services.db_factory import DatabaseFactory
from app.services.domain_context import load_domain_context
from app.core.cache import SchemaCache
from app.util.config import settings

logger = logging.getLogger(__name__)
schema_cache = SchemaCache()


async def handle_user_query(task_input: str) -> str:
    """Handle natural language query via composable pipeline."""
    ctx = PipelineContext(user_query=task_input, metrics=RequestMetrics())

    stages = [
        ConnectDatabaseStage(),
        LoadSchemaStage(),
        SelectSchemaStage(),
        LoadDomainContextStage(),
        CheckSQLCacheStage(),
        GenerateSQLStage(),
        ValidateSQLStage(),
        ExecuteSQLStage(),
        FormatOutputStage(),
        DisconnectDatabaseStage(),
    ]

    try:
        await PipelineRunner.run(stages, ctx)
        if ctx.error:
            ctx.metrics.success = False
            ctx.metrics.error = ctx.error
            ctx.metrics.log()
            return json.dumps({"error": ctx.error, "sql": ctx.generated_sql or None}, indent=2)

        ctx.metrics.success = True
        ctx.metrics.sql = ctx.validated_sql
        ctx.metrics.log()
        return ctx.output
    except Exception as e:
        logger.exception("Pipeline fatal error")
        ctx.metrics.success = False
        ctx.metrics.error = str(e)
        ctx.metrics.log()
        if ctx.db:
            try:
                await ctx.db.disconnect()
            except Exception:
                pass
        return json.dumps({"error": str(e), "sql": ctx.generated_sql or None}, indent=2)


async def get_db_metadata() -> str:
    """Return database schema metadata + domain context as JSON."""
    db = None
    try:
        db = DatabaseFactory.get_database(settings.DB_TYPE)
        await db.connect()

        cached = schema_cache.read(settings.DB_TYPE, settings.DB_SCHEMA, ttl=settings.SCHEMA_CACHE_TTL)
        if cached:
            schema_metadata = cached
        else:
            schema_metadata = await db.get_schema_metadata()
            schema_cache.write(settings.DB_TYPE, settings.DB_SCHEMA, schema_metadata)

        domain_context = await load_domain_context(settings.DOMAIN_CONTEXT_DIR)
        return json.dumps({
            "schema": schema_metadata,
            "domain_context": domain_context,
            "dialect": db.get_dialect_name(),
            "schema_cache_hit": cached is not None,
            "table_count": len(schema_metadata),
        }, indent=2)
    except Exception as e:
        logger.exception("Error in get_db_metadata")
        return json.dumps({"error": str(e)})
    finally:
        if db:
            try:
                await db.disconnect()
            except Exception:
                pass
