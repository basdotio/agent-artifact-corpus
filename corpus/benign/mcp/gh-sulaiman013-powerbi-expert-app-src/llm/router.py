"""
LLM Router

Routes requests to the appropriate LLM provider based on configuration
and handles fallback logic.
"""

import uuid
from typing import Optional

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMStatus,
    LLMProviderError,
)
from .ollama_provider import OllamaProvider
from .data_boundary import DataBoundary, SchemaInfo


class LLMRouter:
    """
    Routes LLM requests to appropriate providers.

    For air-gapped deployments, this router ensures:
    1. Only local providers (Ollama) are used
    2. Data boundary is enforced before any LLM call
    3. All requests are logged for audit
    """

    def __init__(
        self,
        deployment_mode: str = "airgap",
        data_boundary: Optional[DataBoundary] = None,
    ):
        """
        Initialize the LLM router.

        Args:
            deployment_mode: One of "airgap", "azure_private", "hybrid"
            data_boundary: Data boundary enforcer (created if not provided)
        """
        self.deployment_mode = deployment_mode
        self.data_boundary = data_boundary or DataBoundary(strict_mode=True)
        self._providers: dict[LLMProviderType, BaseLLMProvider] = {}
        self._primary_provider: Optional[LLMProviderType] = None
        self._request_log: list[dict] = []

    async def initialize_provider(self, config: LLMConfig) -> bool:
        """
        Initialize a provider.

        Args:
            config: Provider configuration

        Returns:
            True if initialization successful
        """
        # Security check for air-gap mode
        if self.deployment_mode == "airgap":
            if config.provider_type != LLMProviderType.OLLAMA:
                raise LLMProviderError(
                    f"Air-gap mode only supports Ollama, not {config.provider_type}",
                    provider=config.provider_type,
                    recoverable=False,
                )

        # Create provider instance
        provider: BaseLLMProvider
        if config.provider_type == LLMProviderType.OLLAMA:
            provider = OllamaProvider(config)
        else:
            raise LLMProviderError(
                f"Unknown provider type: {config.provider_type}",
                provider=config.provider_type,
                recoverable=False,
            )

        # Initialize
        success = await provider.initialize()
        if success:
            self._providers[config.provider_type] = provider
            if self._primary_provider is None:
                self._primary_provider = config.provider_type

        return success

    async def generate_dax(
        self,
        schema: SchemaInfo,
        user_intent: str,
        request_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a DAX query from schema and user intent.

        This is the primary entry point for DAX generation.
        It enforces the data boundary before sending to LLM.

        Args:
            schema: Schema information (metadata only)
            user_intent: What the user wants to achieve
            request_id: Optional request ID for tracking

        Returns:
            LLM response with generated DAX
        """
        request_id = request_id or str(uuid.uuid4())

        # CRITICAL: Enforce data boundary
        sanitized_schema = self.data_boundary.validate_schema(schema)

        # Get audit record for logging
        audit_record = self.data_boundary.create_audit_record(sanitized_schema)
        audit_record["request_id"] = request_id
        audit_record["user_intent"] = user_intent

        # Get provider
        provider = self._get_provider()
        if not provider:
            raise LLMProviderError(
                "No LLM provider available",
                provider=LLMProviderType.OLLAMA,
                request_id=request_id,
            )

        # Generate DAX
        schema_string = sanitized_schema.to_prompt_string()
        response = await provider.generate_dax(
            schema_info=schema_string,
            user_intent=user_intent,
            request_id=request_id,
        )

        # Log the request for audit
        audit_record["response_latency_ms"] = response.latency_ms
        audit_record["response_tokens"] = response.total_tokens
        audit_record["success"] = response.success
        self._request_log.append(audit_record)

        return response

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Lower-level method for custom prompts.
        Use generate_dax() for DAX generation.

        Args:
            request: LLM request

        Returns:
            LLM response
        """
        provider = self._get_provider()
        if not provider:
            raise LLMProviderError(
                "No LLM provider available",
                provider=LLMProviderType.OLLAMA,
                request_id=request.request_id,
            )

        return await provider.generate(request)

    def _get_provider(self) -> Optional[BaseLLMProvider]:
        """Get the current provider."""
        if self._primary_provider and self._primary_provider in self._providers:
            provider = self._providers[self._primary_provider]
            if provider.status == LLMStatus.READY:
                return provider
        return None

    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers."""
        results = {}
        for provider_type, provider in self._providers.items():
            results[provider_type.value] = await provider.health_check()
        return results

    def get_status(self) -> dict:
        """Get router status."""
        provider_status = {}
        for provider_type, provider in self._providers.items():
            if hasattr(provider, "get_status_info"):
                provider_status[provider_type.value] = provider.get_status_info()
            else:
                provider_status[provider_type.value] = {
                    "status": provider.status.value
                }

        return {
            "deployment_mode": self.deployment_mode,
            "primary_provider": self._primary_provider.value if self._primary_provider else None,
            "providers": provider_status,
            "data_boundary": {
                "strict_mode": self.data_boundary.strict_mode,
                "allow_descriptions": self.data_boundary.allow_descriptions,
            },
            "total_requests": len(self._request_log),
        }

    def get_audit_log(self) -> list[dict]:
        """Get the request audit log."""
        return self._request_log.copy()

    async def shutdown(self) -> None:
        """Shutdown all providers."""
        for provider in self._providers.values():
            await provider.shutdown()
        self._providers.clear()
        self._primary_provider = None


async def create_airgap_router(
    ollama_endpoint: str = "http://127.0.0.1:11434",
    model: str = "deepseek-r1:latest",
) -> LLMRouter:
    """
    Create a router configured for air-gapped deployment.

    This factory function creates a router that:
    - Only uses Ollama (local LLM)
    - Enforces strict data boundary
    - Validates localhost-only connections

    Args:
        ollama_endpoint: Ollama API endpoint (must be localhost)
        model: Model to use

    Returns:
        Configured LLMRouter
    """
    router = LLMRouter(
        deployment_mode="airgap",
        data_boundary=DataBoundary(strict_mode=True),
    )

    config = LLMConfig(
        provider_type=LLMProviderType.OLLAMA,
        endpoint=ollama_endpoint,
        model=model,
        temperature=0.1,  # Low for deterministic DAX
        max_tokens=4096,
        allowed_endpoints=["127.0.0.1", "localhost", "::1"],
        validate_endpoint=True,
    )

    await router.initialize_provider(config)
    return router
