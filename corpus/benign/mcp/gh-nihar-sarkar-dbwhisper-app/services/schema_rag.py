"""Schema Retrieval-Augmented Generation: select only relevant tables for the LLM prompt.

Uses simple keyword matching + table-name similarity to avoid embedding dependencies.
For production scale, swap in sentence-transformers or OpenAI embeddings.
"""

import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)


class SchemaRAG:
    """Select relevant schema tables based on user query keywords and FK graph expansion."""

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def select(self, full_schema: List[Dict[str, Any]], user_query: str) -> List[Dict[str, Any]]:
        """Return a subset of tables most relevant to the user query."""
        query_lower = user_query.lower()
        query_tokens = set(query_lower.split())

        scored = []
        for table in full_schema:
            score = self._score_table(table, query_tokens, query_lower)
            scored.append((score, table))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [t for _, t in scored[:self.top_k]]

        # FK expansion: include tables referenced by FKs in selected tables
        selected = self._expand_foreign_keys(full_schema, selected)

        logger.info("SchemaRAG selected %d/%d tables", len(selected), len(full_schema))
        return selected

    def _score_table(self, table: Dict[str, Any], query_tokens: Set[str], query_lower: str) -> float:
        table_name = table.get("table", "").lower()
        score = 0.0

        # Table name match
        if table_name in query_lower or table_name.split(".")[-1] in query_lower:
            score += 10.0

        # Column name matches
        for col in table.get("columns", []):
            col_name = col.get("name", "").lower()
            col_type = col.get("type", "").lower()
            if col_name in query_tokens:
                score += 3.0
            if any(tok in col_name for tok in query_tokens):
                score += 1.0
            # Type hints (e.g., "date" in query → date columns matter)
            if col_type in query_tokens:
                score += 0.5

        return score

    def _expand_foreign_keys(self, full_schema: List[Dict[str, Any]], selected: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        selected_names = {t["table"] for t in selected}
        full_by_name = {t["table"]: t for t in full_schema}
        result = list(selected)

        for table in selected:
            for col in table.get("columns", []):
                fk = col.get("foreign_key")
                if fk:
                    fk_table = fk.get("table")
                    if fk_table and fk_table not in selected_names and fk_table in full_by_name:
                        result.append(full_by_name[fk_table])
                        selected_names.add(fk_table)

        return result
