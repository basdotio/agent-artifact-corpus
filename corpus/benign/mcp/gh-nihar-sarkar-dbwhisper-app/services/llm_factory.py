"""Factory for creating LLM provider clients with circuit breaker and fallback."""

import logging
from .llm_providers.base import BaseLLMClient, LLMResponse
from .llm_providers.openai_provider import OpenAIProvider
from .llm_providers.azure_provider import AzureProvider
from .llm_providers.claude_provider import ClaudeProvider
from .llm_providers.kimi_provider import KimiProvider
from .llm_providers.bedrock_provider import BedrockProvider
from app.core.circuit_breaker import CircuitBreakerRegistry
from app.util.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM provider clients with circuit breaker and fallback."""

    _providers = {
        "openai": OpenAIProvider,
        "azure": AzureProvider,
        "claude": ClaudeProvider,
        "kimi": KimiProvider,
        "bedrock": BedrockProvider,
    }

    @staticmethod
    def get_client(provider: str) -> BaseLLMClient:
        provider = provider.lower().strip()
        if provider not in LLMFactory._providers:
            raise ValueError(f"Unsupported LLM provider: '{provider}'. Supported: {list(LLMFactory._providers.keys())}")
        logger.info("Using LLM provider: %s", provider)
        return LLMFactory._providers[provider]()

    @staticmethod
    async def generate_with_fallback(schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        """Generate SQL with primary provider, falling back on failure."""
        primary = settings.LLM_PROVIDER
        fallback = settings.LLM_PROVIDER_FALLBACK

        cb = CircuitBreakerRegistry.get(primary)
        client = LLMFactory.get_client(primary)
        wrapped = cb.call(client.generate_sql)

        try:
            return await wrapped(schema, domain_context, user_query, dialect)
        except Exception as e:
            logger.warning("Primary provider %s failed: %s", primary, e)
            if fallback and fallback != primary:
                logger.info("Trying fallback provider: %s", fallback)
                fb_client = LLMFactory.get_client(fallback)
                return await fb_client.generate_sql(schema, domain_context, user_query, dialect)
            raise
