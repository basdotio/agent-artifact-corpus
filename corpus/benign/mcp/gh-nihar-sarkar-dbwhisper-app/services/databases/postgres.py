"""PostgreSQL database adapter using asyncpg with connection pooling."""

import asyncpg
import json
import logging
from collections import defaultdict
from typing import List, Dict, Any
from .base import BaseDatabase
from app.util.config import settings

logger = logging.getLogger(__name__)


class PostgreSQLDatabase(BaseDatabase):
    """PostgreSQL database adapter using asyncpg with connection pooling."""

    def __init__(self):
        self.pool = None
        self.schema = settings.DB_SCHEMA

    async def connect(self) -> None:
        if settings.DATABASE_URL:
            self.pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=2, max_size=10)
        else:
            self.pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                min_size=2, max_size=10
            )
        logger.info("PostgreSQL pool created.")

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("PostgreSQL pool closed.")

    async def execute_query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        sql = self._inject_limit(sql, limit)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql)
            if rows:
                return [dict(r) for r in rows]
            return [{"status": "Query executed successfully"}]

    def _inject_limit(self, sql: str, limit: int) -> str:
        stripped = sql.strip().lower()
        if stripped.startswith("select") and "limit" not in stripped:
            return f"{sql.rstrip(';')} LIMIT {limit}"
        return sql

    async def get_schema_metadata(self) -> List[Dict[str, Any]]:
        query = """
        SELECT DISTINCT
            c.table_schema, c.table_name, c.column_name, c.data_type, c.ordinal_position,
            tc.constraint_type, kcu.constraint_name,
            ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name AND c.table_schema = kcu.table_schema
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema
        LEFT JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name AND tc.table_schema = ccu.table_schema
        WHERE c.table_schema = $1
        ORDER BY c.table_name, c.ordinal_position;
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, self.schema)
        return self._structure_metadata(rows)

    def _structure_metadata(self, rows: List[asyncpg.Record]) -> List[Dict[str, Any]]:
        schema_dict = defaultdict(lambda: {"table": "", "columns": []})
        for row in rows:
            table = row["table_name"]
            schema_name = row["table_schema"]
            full_table_name = f"{schema_name}.{table}"
            column = {"name": row["column_name"], "type": row["data_type"]}
            if row.get("constraint_type") == "PRIMARY KEY":
                column["primary_key"] = True
            elif row.get("constraint_type") == "FOREIGN KEY":
                column["foreign_key"] = {
                    "table": f"{schema_name}.{row['foreign_table_name']}",
                    "column": row["foreign_column_name"]
                }
            schema_dict[table]["table"] = full_table_name
            schema_dict[table]["columns"].append(column)
        return list(schema_dict.values())

    def get_dialect_name(self) -> str:
        return "postgresql"

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(f"EXPLAIN (FORMAT JSON) {sql}")
            return json.loads(row[0])[0] if row else {}
