"""Factory for creating database adapters based on configuration."""

import logging
from .databases.base import BaseDatabase
from .databases.postgres import PostgreSQLDatabase
from .databases.mysql import MySQLDatabase
from .databases.mssql import MSSQLDatabase
from .databases.sqlite import SQLiteDatabase
from .databases.oracle import OracleDatabase

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Factory for creating database adapters based on configuration."""

    _databases = {
        "postgresql": PostgreSQLDatabase,
        "mysql": MySQLDatabase,
        "mssql": MSSQLDatabase,
        "sqlite": SQLiteDatabase,
        "oracle": OracleDatabase,
    }

    @staticmethod
    def get_database(db_type: str) -> BaseDatabase:
        db_type = db_type.lower().strip()
        if db_type not in DatabaseFactory._databases:
            raise ValueError(f"Unsupported database type: '{db_type}'. Supported: {list(DatabaseFactory._databases.keys())}")
        logger.info("Using database adapter: %s", db_type)
        return DatabaseFactory._databases[db_type]()
