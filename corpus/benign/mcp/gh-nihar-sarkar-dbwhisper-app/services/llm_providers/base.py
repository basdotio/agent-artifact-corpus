"""Base class for all LLM provider clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Standard response wrapper for all LLM providers."""
    content: str
    model: str
    usage: Optional[dict] = None


class BaseLLMClient(ABC):
    """Abstract base class for all LLM provider clients."""

    @abstractmethod
    async def generate_sql(self, schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        """Generate SQL from natural language. Must return LLMResponse."""
        pass

    def _build_prompt(self, schema: str, domain_context: str, dialect: str) -> str:
        """Build the system prompt for SQL generation."""
        base = f"You are an expert {dialect} assistant.Database Schema:{schema}"
        if domain_context and domain_context.strip():
            base += f"Domain Context:{domain_context}"
        base += ("Rules:"
            "- Use fully qualified names like 'schema.table' "
            "- Consider end_date columns for calculations unless the user query mentions inactive status"
            "- Only return the SQL query, no comments or extra text."
            "- If the query could return many rows, add LIMIT 100."
        )
        return base
