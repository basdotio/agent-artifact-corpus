"""
Azure AI Foundry - Claude Provider

Supports Claude models deployed via Azure AI Foundry (Microsoft Foundry).
Uses the Anthropic Messages API format.

Endpoint format: https://<resource>.services.ai.azure.com/anthropic/v1/messages
Auth header: x-api-key (NOT api-key)

Reference: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/how-to/use-foundry-models-claude
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx

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


@dataclass
class AzureClaudeConfig:
    """Azure AI Foundry Claude configuration."""
    endpoint: str  # e.g., https://xxx.services.ai.azure.com
    api_key: str
    model_name: str = "claude-haiku-4-5"


class AzureClaudeProvider(BaseLLMProvider):
    """
    Azure AI Foundry provider for Claude models.

    Endpoint format: https://<resource>.services.ai.azure.com
    Full URL: https://<resource>.services.ai.azure.com/anthropic/v1/messages

    Authentication uses 'x-api-key' header (NOT 'api-key').
    """

    def __init__(self, config: LLMConfig, azure_config: AzureClaudeConfig):
        super().__init__(config)
        self.azure_config = azure_config
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        """Initialize the Azure Claude provider."""
        try:
            # Build base URL - extract the resource URL
            base_url = self.azure_config.endpoint.rstrip('/')

            # Remove any paths if user included them
            if '/anthropic/v1/messages' in base_url:
                base_url = base_url.replace('/anthropic/v1/messages', '')
            if '/anthropic/v1' in base_url:
                base_url = base_url.replace('/anthropic/v1', '')
            if '/anthropic' in base_url:
                base_url = base_url.replace('/anthropic', '')

            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "x-api-key": self.azure_config.api_key,  # Microsoft Foundry uses x-api-key
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
            )

            # Test connection
            if await self.health_check():
                self._status = LLMStatus.READY
                return True
            else:
                self._status = LLMStatus.ERROR
                self._error_message = "Failed to connect to Azure Claude"
                return False

        except Exception as e:
            self._status = LLMStatus.ERROR
            self._error_message = str(e)
            return False

    async def health_check(self) -> bool:
        """Check if Azure Claude is accessible."""
        try:
            if not self._client:
                return False

            # Simple test request - POST to /anthropic/v1/messages
            response = await self._client.post(
                "/anthropic/v1/messages",
                json={
                    "model": self.azure_config.model_name,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                timeout=15,
            )

            self._last_health_check = time.time()
            # 200 = success, 400 = API reachable but bad request
            return response.status_code in [200, 400]

        except Exception:
            return False

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Azure Claude (Anthropic API)."""
        if not self._client or self._status != LLMStatus.READY:
            raise LLMConnectionError(
                "Azure Claude provider not initialized",
                provider=LLMProviderType.AZURE_PRIVATE,
                request_id=request.request_id,
            )

        start_time = time.time()

        # Build Anthropic API request
        # Note: Anthropic uses "system" as a top-level field, not in messages
        payload = {
            "model": self.azure_config.model_name,
            "max_tokens": request.max_tokens or self.config.max_tokens,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }

        # Add system prompt if provided
        if request.system_prompt:
            payload["system"] = request.system_prompt

        # Add temperature if not default
        if request.temperature or self.config.temperature:
            payload["temperature"] = request.temperature or self.config.temperature

        # Retry logic
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.post(
                    "/anthropic/v1/messages",
                    json=payload,
                    timeout=self.config.timeout,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    raise LLMProviderError(
                        f"Azure Claude returned status {response.status_code}: {error_detail}",
                        provider=LLMProviderType.AZURE_PRIVATE,
                        request_id=request.request_id,
                    )

                data = response.json()
                latency_ms = (time.time() - start_time) * 1000

                # Extract response (Anthropic format)
                content = ""
                content_blocks = data.get("content", [])
                for block in content_blocks:
                    if block.get("type") == "text":
                        content += block.get("text", "")

                usage = data.get("usage", {})

                return LLMResponse(
                    content=content,
                    model=self.azure_config.model_name,
                    provider=LLMProviderType.AZURE_PRIVATE,
                    latency_ms=latency_ms,
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                    total_tokens=(usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
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
                    f"Cannot connect to Azure Claude: {e}",
                    provider=LLMProviderType.AZURE_PRIVATE,
                    request_id=request.request_id,
                    recoverable=True,
                )

        # All retries exhausted
        raise LLMTimeoutError(
            f"Azure Claude request timed out after {self.config.max_retries} attempts",
            provider=LLMProviderType.AZURE_PRIVATE,
            request_id=request.request_id,
        )

    async def shutdown(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def close(self) -> None:
        """Alias for shutdown() - clean up HTTP client."""
        await self.shutdown()


def create_azure_claude_provider(
    endpoint: str,
    api_key: str,
    model_name: str = "claude-haiku-4-5",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    timeout: float = 60,
) -> AzureClaudeProvider:
    """
    Create an Azure Claude provider.

    Args:
        endpoint: Azure AI Foundry endpoint URL
        api_key: Azure API key
        model_name: Claude model name (e.g., claude-haiku-4-5)
        temperature: Generation temperature
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Configured AzureClaudeProvider
    """
    config = LLMConfig(
        provider_type=LLMProviderType.AZURE_PRIVATE,
        endpoint=endpoint,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    azure_config = AzureClaudeConfig(
        endpoint=endpoint,
        api_key=api_key,
        model_name=model_name,
    )

    return AzureClaudeProvider(config, azure_config)
