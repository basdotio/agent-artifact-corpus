"""
Ollama LLM Provider

Local LLM inference using Ollama for air-gapped deployments.
Ollama runs entirely on localhost - no external network access required.

Supported models:
- mistral:7b-instruct (recommended for DAX generation)
- llama3:8b-instruct
- phi3:mini
- codellama:7b
"""

import asyncio
import re
import time
import uuid
from typing import Optional
from urllib.parse import urlparse

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


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider for local LLM inference.

    Ollama must be running locally on the specified endpoint.
    For air-gapped deployments, this is the recommended provider.

    Features:
    - Runs entirely offline
    - No data leaves localhost
    - Supports multiple open-source models
    - GPU acceleration (if available)
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._model_loaded = False

    async def initialize(self) -> bool:
        """
        Initialize the Ollama provider.

        Validates:
        1. Endpoint is localhost (security check)
        2. Ollama is running
        3. Required model is available
        """
        try:
            # Security check: ensure endpoint is localhost
            if not self._validate_localhost_only():
                self._status = LLMStatus.ERROR
                self._error_message = "Ollama endpoint must be localhost for air-gapped deployment"
                return False

            # Create HTTP client with restricted settings
            self._client = httpx.AsyncClient(
                base_url=self.config.endpoint,
                timeout=httpx.Timeout(self.config.timeout),
                # Security: disable redirects to prevent SSRF
                follow_redirects=False,
                # Security: limit response size
                limits=httpx.Limits(max_keepalive_connections=5),
            )

            # Check if Ollama is running
            if not await self.health_check():
                self._status = LLMStatus.ERROR
                self._error_message = "Cannot connect to Ollama"
                return False

            # Check if model is available
            if not await self._check_model_available():
                self._status = LLMStatus.ERROR
                self._error_message = f"Model {self.config.model} not available in Ollama"
                return False

            self._status = LLMStatus.READY
            return True

        except Exception as e:
            self._status = LLMStatus.ERROR
            self._error_message = str(e)
            return False

    def _validate_localhost_only(self) -> bool:
        """
        Ensure Ollama endpoint is localhost only.

        This is a CRITICAL security check for air-gapped deployments.
        Ollama should NEVER be exposed on a network interface.
        """
        parsed = urlparse(self.config.endpoint)
        host = parsed.hostname or ""

        allowed_localhost = {"127.0.0.1", "localhost", "::1"}
        return host.lower() in allowed_localhost

    def _process_thinking_response(self, content: str) -> str:
        """
        Process responses from reasoning models that use thinking tags.

        Models like Qwen3 and DeepSeek-R1 wrap internal reasoning in <think>...</think> tags.
        This extracts the actual answer content.

        Args:
            content: Raw response content from the model

        Returns:
            Processed content with thinking extracted or shown appropriately
        """
        if not content:
            return ""

        # Check if response contains thinking tags
        think_pattern = r'<think>(.*?)</think>'
        think_match = re.search(think_pattern, content, re.DOTALL)

        if think_match:
            # Extract content after </think> tag
            after_think = re.sub(think_pattern, '', content, flags=re.DOTALL).strip()

            if after_think:
                # Return the actual answer (content after thinking)
                return after_think
            else:
                # If only thinking content exists, return a summary
                thinking_content = think_match.group(1).strip()
                if thinking_content:
                    # Return thinking as collapsed details for transparency
                    return f"<details><summary>🤔 Model Reasoning</summary>\n\n{thinking_content}\n</details>\n\n*The model processed your request but did not generate a visible response. Try rephrasing your question.*"
                return "*No response generated. Try rephrasing your question.*"

        return content

    async def health_check(self) -> bool:
        """Check if Ollama is running and responsive."""
        try:
            if not self._client:
                return False

            response = await self._client.get("/api/tags")
            self._last_health_check = time.time()
            return response.status_code == 200

        except httpx.ConnectError:
            return False
        except Exception:
            return False

    async def _check_model_available(self) -> bool:
        """Check if the configured model is available in Ollama."""
        try:
            if not self._client:
                return False

            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                return False

            data = response.json()
            models = data.get("models", [])

            # Model name might have tag (e.g., "mistral:7b-instruct")
            model_base = self.config.model.split(":")[0]

            for model in models:
                model_name = model.get("name", "")
                if model_name.startswith(model_base):
                    self._model_loaded = True
                    return True

            return False

        except Exception:
            return False

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response using Ollama.

        Args:
            request: LLM request with system/user prompts

        Returns:
            LLM response with generated content
        """
        if not self._client or self._status != LLMStatus.READY:
            raise LLMConnectionError(
                "Ollama provider not initialized",
                provider=LLMProviderType.OLLAMA,
                request_id=request.request_id,
            )

        start_time = time.time()

        # Build request payload
        payload = {
            "model": self.config.model,
            "prompt": request.user_prompt,
            "system": request.system_prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature or self.config.temperature,
                "num_predict": request.max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }

        # Retry logic
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                response = await self._client.post(
                    "/api/generate",
                    json=payload,
                    timeout=self.config.timeout,
                )

                if response.status_code != 200:
                    raise LLMProviderError(
                        f"Ollama returned status {response.status_code}",
                        provider=LLMProviderType.OLLAMA,
                        request_id=request.request_id,
                    )

                data = response.json()
                latency_ms = (time.time() - start_time) * 1000

                # Process thinking mode responses (Qwen3, DeepSeek-R1, etc.)
                raw_content = data.get("response", "")

                # Debug logging to diagnose empty responses
                import logging
                logger = logging.getLogger("powerbi-v3-webui")
                logger.info(f"[OLLAMA DEBUG] Raw response length: {len(raw_content)}")
                logger.info(f"[OLLAMA DEBUG] Raw response first 500 chars: {raw_content[:500] if raw_content else 'EMPTY'}")
                logger.info(f"[OLLAMA DEBUG] Response contains <think>: {'<think>' in raw_content}")

                processed_content = self._process_thinking_response(raw_content)
                logger.info(f"[OLLAMA DEBUG] Processed content length: {len(processed_content)}")

                return LLMResponse(
                    content=processed_content,
                    model=self.config.model,
                    provider=LLMProviderType.OLLAMA,
                    latency_ms=latency_ms,
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                    total_tokens=(
                        (data.get("prompt_eval_count") or 0) +
                        (data.get("eval_count") or 0)
                    ) or None,
                    request_id=request.request_id,
                    raw_response={
                        "model": data.get("model"),
                        "done": data.get("done"),
                        "total_duration": data.get("total_duration"),
                    },
                )

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                continue

            except httpx.ConnectError as e:
                raise LLMConnectionError(
                    f"Cannot connect to Ollama: {e}",
                    provider=LLMProviderType.OLLAMA,
                    request_id=request.request_id,
                    recoverable=True,
                )

        # All retries exhausted
        raise LLMTimeoutError(
            f"Ollama request timed out after {self.config.max_retries} attempts",
            provider=LLMProviderType.OLLAMA,
            request_id=request.request_id,
        )

    async def shutdown(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._status = LLMStatus.OFFLINE

    async def pull_model(self, model: Optional[str] = None) -> bool:
        """
        Pull a model from Ollama library.

        Note: This requires internet access, so it should only be used
        during initial setup, NOT in air-gapped production.

        Args:
            model: Model to pull (defaults to configured model)

        Returns:
            True if successful
        """
        if not self._client:
            return False

        target_model = model or self.config.model

        try:
            # This is a streaming endpoint, but we'll wait for completion
            response = await self._client.post(
                "/api/pull",
                json={"name": target_model},
                timeout=600,  # Models can take a while to download
            )
            return response.status_code == 200

        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        """List all available models in Ollama."""
        if not self._client:
            return []

        try:
            response = await self._client.get("/api/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception:
            return []

    def get_status_info(self) -> dict:
        """Get detailed status information."""
        return {
            "provider": "ollama",
            "status": self._status.value,
            "endpoint": self.config.endpoint,
            "model": self.config.model,
            "model_loaded": self._model_loaded,
            "last_health_check": self._last_health_check,
            "error": self._error_message,
            "is_localhost": self._validate_localhost_only(),
        }


def create_ollama_provider(
    endpoint: str = "http://127.0.0.1:11434",
    model: str = "deepseek-r1:latest",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: int = 300,  # 5 minutes for reasoning models like DeepSeek-R1
) -> OllamaProvider:
    """
    Factory function to create an Ollama provider.

    Args:
        endpoint: Ollama API endpoint (must be localhost)
        model: Model to use
        temperature: Generation temperature (low = more deterministic)
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Configured OllamaProvider instance
    """
    config = LLMConfig(
        provider_type=LLMProviderType.OLLAMA,
        endpoint=endpoint,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        # For Ollama, only localhost is allowed
        allowed_endpoints=["127.0.0.1", "localhost", "::1"],
        validate_endpoint=True,
    )
    return OllamaProvider(config)
