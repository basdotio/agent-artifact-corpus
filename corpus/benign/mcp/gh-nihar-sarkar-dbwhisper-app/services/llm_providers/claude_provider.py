"""Anthropic Claude provider for SQL generation."""

from anthropic import AsyncAnthropic
from .base import BaseLLMClient, LLMResponse
from app.util.config import settings
import logging

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMClient):
    """Anthropic Claude provider for SQL generation."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    async def generate_sql(self, schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        """Generate SQL using Anthropic Messages API."""
        system_prompt = self._build_prompt(schema, domain_context, dialect)
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_query}]
            )
            return LLMResponse(
                content=response.content[0].text.strip(),
                model=self.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                } if response.usage else None
            )
        except Exception as e:
            logger.error("Claude API error: %s", e)
            raise
