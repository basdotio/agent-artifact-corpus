"""Legacy database executor — delegates to database factory."""

import logging
import json
from app.services.db_factory import DatabaseFactory
from app.util.config import settings

logger = logging.getLogger(__name__)


async def run_sql_query(query: str) -> str:
    """Execute SQL query and return JSON string result."""
    db = None
    try:
        db = DatabaseFactory.get_database(settings.DB_TYPE)
        await db.connect()
        result = await db.execute_query(query)
        return json.dumps(result, indent=2, default=str)
    except Exception:
        logger.exception("Error executing SQL query")
        return json.dumps({"error": "Execution failed"})
    finally:
        if db:
            try:
                await db.disconnect()
            except Exception:
                pass
