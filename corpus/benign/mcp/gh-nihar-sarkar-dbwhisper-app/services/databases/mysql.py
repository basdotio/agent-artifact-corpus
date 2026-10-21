"""MySQL database adapter using aiomysql with connection pooling."""

import aiomysql
import logging
from collections import defaultdict
from typing import List, Dict, Any
from .base import BaseDatabase
from app.util.config import settings

logger = logging.getLogger(__name__)


class MySQLDatabase(BaseDatabase):
    """MySQL database adapter using aiomysql with connection pooling."""

    def __init__(self):
        self.pool = None
        self.schema = settings.DB_SCHEMA

    async def connect(self) -> None:
        self.pool = await aiomysql.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            db=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            minsize=2, maxsize=10
        )
        logger.info("MySQL pool created.")

    async def disconnect(self) -> None:
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            logger.info("MySQL pool closed.")

    async def execute_query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        sql = self._inject_limit(sql, limit)
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                if cur.description:
                    return await cur.fetchall()
                return [{"status": "Query executed successfully"}]

    def _inject_limit(self, sql: str, limit: int) -> str:
        stripped = sql.strip().lower()
        if stripped.startswith("select") and "limit" not in stripped:
            return f"{sql.rstrip(';')} LIMIT {limit}"
        return sql

    async def get_schema_metadata(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.ORDINAL_POSITION,
            tc.CONSTRAINT_TYPE, kcu.CONSTRAINT_NAME,
            kcu.REFERENCED_TABLE_NAME AS foreign_table_name,
            kcu.REFERENCED_COLUMN_NAME AS foreign_column_name
        FROM information_schema.COLUMNS c
        LEFT JOIN information_schema.KEY_COLUMN_USAGE kcu
            ON c.TABLE_NAME = kcu.TABLE_NAME AND c.COLUMN_NAME = kcu.COLUMN_NAME AND c.TABLE_SCHEMA = kcu.TABLE_SCHEMA
        LEFT JOIN information_schema.TABLE_CONSTRAINTS tc
            ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
        WHERE c.TABLE_SCHEMA = %s
        ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, (self.schema,))
                rows = await cur.fetchall()
        return self._structure_metadata(rows)

    def _structure_metadata(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        schema_dict = defaultdict(lambda: {"table": "", "columns": []})
        for row in rows:
            table = row["TABLE_NAME"]
            schema_name = row["TABLE_SCHEMA"]
            full_table_name = f"{schema_name}.{table}"
            column = {"name": row["COLUMN_NAME"], "type": row["DATA_TYPE"]}
            if row.get("CONSTRAINT_TYPE") == "PRIMARY KEY":
                column["primary_key"] = True
            elif row.get("CONSTRAINT_TYPE") == "FOREIGN KEY":
                column["foreign_key"] = {
                    "table": f"{schema_name}.{row['foreign_table_name']}",
                    "column": row["foreign_column_name"]
                }
            schema_dict[table]["table"] = full_table_name
            schema_dict[table]["columns"].append(column)
        return list(schema_dict.values())

    def get_dialect_name(self) -> str:
        return "mysql"

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(f"EXPLAIN FORMAT=JSON {sql}")
                row = await cur.fetchone()
                import json
                return json.loads(row["EXPLAIN"]) if row else {}
