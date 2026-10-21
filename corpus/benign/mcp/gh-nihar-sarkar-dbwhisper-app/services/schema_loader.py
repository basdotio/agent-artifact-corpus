"""Legacy schema loader — delegates to database factory + cache."""

import logging
import json
from app.services.db_factory import DatabaseFactory
from app.core.cache import SchemaCache
from app.util.config import settings

logger = logging.getLogger(__name__)
cache = SchemaCache()


async def get_schema_context(schema_name: str = None) -> str:
    """Get schema context as JSON string with caching."""
    schema_name = schema_name or settings.DB_SCHEMA
    cached = cache.read(settings.DB_TYPE, schema_name, ttl=settings.SCHEMA_CACHE_TTL)
    if cached:
        return json.dumps(cached, indent=2)

    db = None
    try:
        db = DatabaseFactory.get_database(settings.DB_TYPE)
        await db.connect()
        metadata = await db.get_schema_metadata()
        cache.write(settings.DB_TYPE, schema_name, metadata)
        return json.dumps(metadata, indent=2)
    except Exception:
        logger.exception("Error loading schema context")
        raise
    finally:
        if db:
            try:
                await db.disconnect()
            except Exception:
                pass
