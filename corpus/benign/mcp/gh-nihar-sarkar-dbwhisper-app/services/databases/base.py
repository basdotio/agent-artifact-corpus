"""Abstract base class for all database adapters."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseDatabase(ABC):
    """Abstract base class for all database adapters."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection (pool)."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection (pool)."""
        pass

    @abstractmethod
    async def execute_query(self, sql: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as a list of dicts."""
        pass

    @abstractmethod
    async def get_schema_metadata(self) -> List[Dict[str, Any]]:
        """Return structured schema as list of table dicts."""
        pass

    @abstractmethod
    def get_dialect_name(self) -> str:
        """Return SQL dialect name for LLM prompts."""
        pass

    @abstractmethod
    async def explain_query(self, sql: str) -> Dict[str, Any]:
        """Return EXPLAIN plan as dict."""
        pass
