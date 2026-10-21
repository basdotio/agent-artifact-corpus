"""Simple file-based SQL cache for exact + near-exact query matches."""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SQLCache:
    """Disk-backed cache mapping (schema_hash + query_hash) -> generated SQL."""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"sql_{key}.json")

    def get(self, schema_hash: str, user_query: str) -> Optional[str]:
        q_hash = hashlib.md5(user_query.lower().strip().encode()).hexdigest()
        key = f"{schema_hash}_{q_hash}"
        path = self._path(key)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("SQL cache HIT")
                return data.get("sql")
            except Exception:
                pass
        return None

    def put(self, schema_hash: str, user_query: str, sql: str) -> None:
        q_hash = hashlib.md5(user_query.lower().strip().encode()).hexdigest()
        key = f"{schema_hash}_{q_hash}"
        path = self._path(key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"sql": sql, "query": user_query}, f)
            logger.info("SQL cache WRITE")
        except Exception as e:
            logger.warning("SQL cache write failed: %s", e)
