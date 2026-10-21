from dataclasses import dataclass, field
from typing import Dict, List, Set, Protocol, Optional, Any
from pathlib import Path
from .schema.formatter import format_schema

@dataclass
class TableInfo:
    table_name: str
    columns: List[Dict[str, Any]]
    relationships: Dict[str, Dict[str, Any]]
    fully_loaded: bool = False

    def format_schema(self) -> str:
        """Format the schema information for the table, with smart relationship grouping.
        
        Returns:
            A formatted string containing the table's complete schema information.
        """
        return format_schema(
            self.table_name,
            self.columns,
            self.relationships
        )

@dataclass
class SchemaCache:
    tables: Dict[str, TableInfo]
    last_updated: float
    all_table_names: Set[str]  # Set of all table names in the database

class SchemaManager(Protocol):
    """Protocol defining the interface for schema management"""
    def is_cache_valid(self, cache_type: str, key: str) -> bool: ...
    def update_cache(self, cache_type: str, key: str, data: Any) -> None: ...
    async def save_cache(self, cache: Optional[SchemaCache] = None) -> None: ...