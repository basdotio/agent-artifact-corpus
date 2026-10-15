"""
Azure AI Foundry LLM Provider

Enterprise-grade LLM inference using Azure OpenAI Service.
Ideal for Power BI integration - same Microsoft ecosystem.

Features:
- GPT-4o, GPT-4, GPT-3.5-turbo models
- Enterprise compliance (SOC2, HIPAA, GDPR)
- Data privacy - your data doesn't train models
- Regional deployment for data residency
"""

import asyncio
import logging
import time
import os
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("powerbi-v3-webui")

from .base_provider import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderType,
    LLMRequest,
    LLMResponse,
    LLMStatus,
    LLMConnectionError,
    LLMTimeoutError,
    LLMProviderError,
)


def _clean_azure_endpoint(endpoint: str) -> str:
    """
    Clean up Azure endpoint URL to get just the base URL.

    Users might paste full URLs like:
    - https://resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
    - https://resource.openai.azure.com/openai/deployments/model/chat/completions

    We need just: https://resource.cognitiveservices.azure.com/
    """
    if not endpoint:
        return endpoint

    # Parse the URL
    parsed = urlparse(endpoint)

    # Rebuild with just scheme and netloc (host)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    logger.info(f"[AZURE] Cleaned endpoint: {endpoint} -> {base_url}")
    return base_url


@dataclass
class AzureConfig:
    """Azure AI Foundry configuration."""
    endpoint: str  # e.g., https://your-resource.openai.azure.com/
    api_key: str
    deployment_name: str  # e.g., gpt-4o
    api_version: str = "2024-12-01-preview"  # Updated for newer models like GPT-5-mini


class AzureOpenAIProvider(BaseLLMProvider):
    """
    Azure OpenAI provider for enterprise LLM inference.

    Benefits for Power BI:
    - Same Microsoft ecosystem
    - Enterprise security & compliance
    - Data privacy guarantees
    - Fast inference with GPT-4o
    """

    def __init__(self, config: LLMConfig, azure_config: AzureConfig):
        super().__init__(config)
        self.azure_config = azure_config
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        """Initialize the Azure OpenAI provider."""
        try:
            # Clean and normalize the endpoint URL
            base_url = _clean_azure_endpoint(self.azure_config.endpoint)

            logger.info(f"[AZURE] Initializing with endpoint: {base_url}")
            logger.info(f"[AZURE] Deployment: {self.azure_config.deployment_name}")
            logger.info(f"[AZURE] API Version: {self.azure_config.api_version}")

            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "api-key": self.azure_config.api_key,
                    "Content-Type": "application/json",
                },
            )

            # Test connection with a simple request
            if await self.health_check():
                self._status = LLMStatus.READY
                logger.info("[AZURE] Successfully connected to Azure OpenAI")
                return True
            else:
                self._status = LLMStatus.ERROR
                self._error_message = "Failed to connect to Azure OpenAI - health check failed"
                logger.error(f"[AZURE] {self._error_message}")
                return False

        except Exception as e:
            self._status = LLMStatus.ERROR
            self._error_message = str(e)
            logger.error(f"[AZURE] Initialization error: {e}", exc_info=True)
            return False

    async def health_check(self) -> bool:
        """Check if Azure OpenAI is accessible."""
        try:
            if not self._client:
                logger.error("[AZURE] Health check failed: no client")
                return False

            # Simple completions request to verify connectivity
            url = f"/openai/deployments/{self.azure_config.deployment_name}/chat/completions?api-version={self.azure_config.api_version}"

            logger.info(f"[AZURE] Health check URL: {url}")

            response = await self._client.post(
                url,
                json={
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1,
                },
            )

            logger.info(f"[AZURE] Health check response status: {response.status_code}")

            self._last_health_check = time.time()

            # 200 = success, 400 = bad request but API reachable
            if response.status_code in [200, 400]:
                return True
            else:
                # Log the error response for debugging
                logger.error(f"[AZURE] Health check failed with status {response.status_code}: {response.text[:500]}")
                return False

        except Exception as e:
            logger.error(f"[AZURE] Health check exception: {e}", exc_info=True)
            return False

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Azure OpenAI."""
        if not self._client or self._status != LLMStatus.READY:
            raise LLMConnectionError(
                "Azure OpenAI provider not initialized",
                provider=LLMProviderType.AZURE_PRIVATE,
                request_id=request.request_id,
            )

        start_time = time.time()

        # Build messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})

        # Build request payload
        # Note: Newer models use max_completion_tokens instead of max_tokens
        # Some models (like GPT-5-mini) don't support temperature/top_p customization
        payload = {
            "messages": messages,
            "max_completion_tokens": request.max_tokens or self.config.max_tokens,
        }

        # Only add temperature/top_p for models that support them
        # GPT-5-mini and similar preview models may reject non-default values
        temp = request.temperature or self.config.temperature
        if temp is not None and temp != 1.0:
            # Try with temperature first, will retry without if model rejects it
            payload["temperature"] = temp
        if self.config.top_p is not None and self.config.top_p != 1.0:
            payload["top_p"] = self.config.top_p

        url = f"/openai/deployments/{self.azure_config.deployment_name}/chat/completions?api-version={self.azure_config.api_version}"

        # Retry logic with smart parameter handling
        last_error: Optional[Exception] = None
        retry_without_temp = False

        for attempt in range(self.config.max_retries + 1):  # +1 for potential temp retry
            try:
                # If we got an unsupported temperature error, retry without it
                if retry_without_temp:
                    payload.pop("temperature", None)
                    payload.pop("top_p", None)
                    logger.info("[AZURE] Retrying without temperature/top_p parameters")

                response = await self._client.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                )

                if response.status_code != 200:
                    error_detail = response.text

                    # Check if the error is about unsupported temperature/top_p
                    # Models like GPT-5-mini don't support custom temperature values
                    if response.status_code == 400 and "unsupported_value" in error_detail:
                        if ("temperature" in error_detail or "top_p" in error_detail) and not retry_without_temp:
                            logger.warning(f"[AZURE] Model doesn't support temperature/top_p, retrying without them")
                            retry_without_temp = True
                            continue

                    raise LLMProviderError(
                        f"Azure OpenAI returned status {response.status_code}: {error_detail}",
                        provider=LLMProviderType.AZURE_PRIVATE,
                        request_id=request.request_id,
                    )

                data = response.json()
                latency_ms = (time.time() - start_time) * 1000

                # Extract response
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {})

                return LLMResponse(
                    content=content,
                    model=self.azure_config.deployment_name,
                    provider=LLMProviderType.AZURE_PRIVATE,
                    latency_ms=latency_ms,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    request_id=request.request_id,
                    raw_response=data,
                )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                continue

            except httpx.ConnectError as e:
                raise LLMConnectionError(
                    f"Cannot connect to Azure OpenAI: {e}",
                    provider=LLMProviderType.AZURE_PRIVATE,
                    request_id=request.request_id,
                    recoverable=True,
                )

        # All retries exhausted
        raise LLMTimeoutError(
            f"Azure OpenAI request timed out after {self.config.max_retries} attempts",
            provider=LLMProviderType.AZURE_PRIVATE,
            request_id=request.request_id,
        )

    async def shutdown(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


def create_azure_provider(
    endpoint: str,
    api_key: str,
    deployment_name: str = "gpt-4o",
    api_version: str = "2024-12-01-preview",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    timeout: float = 60,
) -> AzureOpenAIProvider:
    """
    Create an Azure OpenAI provider.

    Args:
        endpoint: Azure OpenAI endpoint URL
        api_key: Azure OpenAI API key
        deployment_name: Model deployment name (e.g., gpt-4o)
        api_version: API version
        temperature: Generation temperature
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Configured AzureOpenAIProvider
    """
    config = LLMConfig(
        provider_type=LLMProviderType.AZURE_PRIVATE,
        endpoint=endpoint,
        model=deployment_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    azure_config = AzureConfig(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment_name,
        api_version=api_version,
    )

    return AzureOpenAIProvider(config, azure_config)


def create_azure_provider_from_env() -> Optional[AzureOpenAIProvider]:
    """
    Create Azure provider from environment variables.

    Required env vars:
    - AZURE_OPENAI_ENDPOINT
    - AZURE_OPENAI_API_KEY
    - AZURE_OPENAI_DEPLOYMENT (optional, defaults to gpt-4o)
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    if not endpoint or not api_key:
        return None

    return create_azure_provider(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment,
    )
