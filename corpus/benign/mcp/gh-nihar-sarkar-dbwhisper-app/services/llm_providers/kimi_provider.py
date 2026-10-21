"""Kimi (Moonshot AI) provider for SQL generation."""

from openai import AsyncOpenAI
from .base import BaseLLMClient, LLMResponse
from app.util.config import settings
import logging

logger = logging.getLogger(__name__)


class KimiProvider(BaseLLMClient):
    """Kimi (Moonshot AI) provider for SQL generation."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.KIMI_API_KEY, base_url=settings.KIMI_BASE_URL)
        self.model = settings.KIMI_MODEL

    async def generate_sql(self, schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        """Generate SQL using Kimi Chat Completions API."""
        system_prompt = self._build_prompt(schema, domain_context, dialect)
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.1,
            )
            return LLMResponse(
                content=response.choices[0].message.content.strip(),
                model=self.model,
                usage=response.usage.model_dump() if response.usage else None
            )
        except Exception as e:
            logger.error("Kimi API error: %s", e)
            raise
