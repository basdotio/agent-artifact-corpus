"""SQLite database adapter using aiosqlite."""

import aiosqlite
import logging
from typing import List, Dict, Any
from .base import BaseDatabase
from app.util.config import settings

logger = logging.getLogger(__name__)


class SQLiteDatabase(BaseDatabase):
    """SQLite database adapter using aiosqlite."""

    def __init__(self):
        self.conn = None
        self.db_path = settings.SQLITE_DB_PATH

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        logger.info("SQLite connected at %s", self.db_path)

    async def disconnect(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None
            logger.info("SQLite disconnected.")

    async def execute_query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        sql = self._inject_limit(sql, limit)
        async with self.conn.execute(sql) as cur:
            if cur.description:
                columns = [desc[0] for desc in cur.description]
                rows = await cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            return [{"status": "Query executed successfully"}]

    def _inject_limit(self, sql: str, limit: int) -> str:
        stripped = sql.strip().lower()
        if stripped.startswith("select") and "limit" not in stripped:
            return f"{sql.rstrip(';')} LIMIT {limit}"
        return sql

    async def get_schema_metadata(self) -> List[Dict[str, Any]]:
        async with self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") as cur:
            tables = [row[0] for row in await cur.fetchall()]

        result = []
        for table in tables:
            async with self.conn.execute(f"PRAGMA table_info({table})") as cur:
                col_info = {row[1]: {"type": row[2], "pk": row[5]} for row in await cur.fetchall()}

            async with self.conn.execute(f"PRAGMA foreign_key_list({table})") as cur:
                fk_info = {}
                for row in await cur.fetchall():
                    fk_info[row[3]] = {"table": row[2], "column": row[4]}

            columns = []
            for col_name, info in col_info.items():
                col = {"name": col_name, "type": info["type"]}
                if info["pk"]:
                    col["primary_key"] = True
                if col_name in fk_info:
                    col["foreign_key"] = {
                        "table": fk_info[col_name]["table"],
                        "column": fk_info[col_name]["column"]
                    }
                columns.append(col)

            result.append({"table": table, "columns": columns})
        return result

    def get_dialect_name(self) -> str:
        return "sqlite"

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        async with self.conn.execute(f"EXPLAIN QUERY PLAN {sql}") as cur:
            rows = await cur.fetchall()
            return {"plan": [{"detail": r[3]} for r in rows]}
