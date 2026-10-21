"""File-based cache manager for schema metadata and lightweight objects."""

import os
import json
import time
import hashlib
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SchemaCache:
    """Disk-backed schema cache with TTL."""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, db_type: str, schema: str) -> str:
        h = hashlib.md5(f"{db_type}:{schema}".encode()).hexdigest()
        return os.path.join(self.cache_dir, f"schema_{h}.json")

    def read(self, db_type: str, schema: str, ttl: int = 3600) -> Optional[List[Dict[str, Any]]]:
        path = self._path(db_type, schema)
        if not os.path.exists(path):
            return None
        if time.time() - os.path.getmtime(path) > ttl:
            logger.debug("Schema cache expired for %s.%s", db_type, schema)
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Schema cache HIT for %s.%s", db_type, schema)
            return data
        except Exception as e:
            logger.warning("Schema cache read failed: %s", e)
            return None

    def write(self, db_type: str, schema: str, metadata: List[Dict[str, Any]]) -> None:
        path = self._path(db_type, schema)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info("Schema cache WRITE for %s.%s", db_type, schema)
        except Exception as e:
            logger.warning("Schema cache write failed: %s", e)
