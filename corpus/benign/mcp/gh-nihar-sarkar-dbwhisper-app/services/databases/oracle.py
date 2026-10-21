"""Oracle database adapter using oracledb."""

import oracledb
import json
import logging
from collections import defaultdict
from typing import List, Dict, Any
from .base import BaseDatabase
from app.util.config import settings

logger = logging.getLogger(__name__)


class OracleDatabase(BaseDatabase):
    """Oracle database adapter using oracledb."""

    def __init__(self):
        self.pool = None
        self.schema = settings.DB_SCHEMA.upper()

    async def connect(self) -> None:
        if settings.DATABASE_URL:
            self.pool = oracledb.create_pool(settings.DATABASE_URL, min=2, max=10)
        else:
            dsn = f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            self.pool = oracledb.create_pool(
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                dsn=dsn,
                min=2, max=10
            )
        logger.info("Oracle pool created.")

    async def disconnect(self) -> None:
        if self.pool:
            self.pool.close()
            self.pool = None
            logger.info("Oracle pool closed.")

    async def execute_query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        sql = self._inject_limit(sql, limit)
        with self.pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                return [{"status": "Query executed successfully"}]

    def _inject_limit(self, sql: str, limit: int) -> str:
        stripped = sql.strip().lower()
        if stripped.startswith("select") and "fetch first" not in stripped and "rownum" not in stripped:
            return f"{sql.rstrip(';')} FETCH FIRST {limit} ROWS ONLY"
        return sql

    async def get_schema_metadata(self) -> List[Dict[str, Any]]:
        query = """
        SELECT
            c.OWNER AS table_schema, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.COLUMN_ID AS ordinal_position,
            ac.CONSTRAINT_TYPE, acc.CONSTRAINT_NAME,
            acc2.TABLE_NAME AS foreign_table_name, acc2.COLUMN_NAME AS foreign_column_name
        FROM ALL_TAB_COLUMNS c
        LEFT JOIN ALL_CONS_COLUMNS acc
            ON c.TABLE_NAME = acc.TABLE_NAME AND c.COLUMN_NAME = acc.COLUMN_NAME AND c.OWNER = acc.OWNER
        LEFT JOIN ALL_CONSTRAINTS ac
            ON acc.CONSTRAINT_NAME = ac.CONSTRAINT_NAME AND acc.OWNER = ac.OWNER
        LEFT JOIN ALL_CONS_COLUMNS acc2
            ON ac.R_CONSTRAINT_NAME = acc2.CONSTRAINT_NAME AND ac.OWNER = acc2.OWNER
        WHERE c.OWNER = :schema_name
        ORDER BY c.TABLE_NAME, c.COLUMN_ID
        """
        with self.pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"schema_name": self.schema})
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                raw_rows = [dict(zip(columns, row)) for row in rows]
        return self._structure_metadata(raw_rows)

    def _structure_metadata(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        schema_dict = defaultdict(lambda: {"table": "", "columns": []})
        for row in rows:
            table = row["TABLE_NAME"]
            schema_name = row["TABLE_SCHEMA"]
            full_table_name = f"{schema_name}.{table}"
            column = {"name": row["COLUMN_NAME"], "type": row["DATA_TYPE"]}
            if row.get("CONSTRAINT_TYPE") == "P":
                column["primary_key"] = True
            elif row.get("CONSTRAINT_TYPE") == "R":
                column["foreign_key"] = {
                    "table": f"{schema_name}.{row['FOREIGN_TABLE_NAME']}",
                    "column": row["FOREIGN_COLUMN_NAME"]
                }
            schema_dict[table]["table"] = full_table_name
            schema_dict[table]["columns"].append(column)
        return list(schema_dict.values())

    def get_dialect_name(self) -> str:
        return "oracle"

    async def explain_query(self, sql: str) -> Dict[str, Any]:
        with self.pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(f"EXPLAIN PLAN FOR {sql}")
                cur.execute("SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY())")
                rows = cur.fetchall()
                return {"plan": [r[0] for r in rows]}
