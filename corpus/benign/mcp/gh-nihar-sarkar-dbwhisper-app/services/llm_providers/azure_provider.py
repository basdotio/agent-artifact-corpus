"""Azure OpenAI provider implementation with comprehensive multi-model support.

Uses raw httpx instead of the openai SDK to support ALL Azure-hosted model families
including legacy, v1, Responses API, and Azure AI Foundry endpoints.

Supported families:
- OpenAI GPT-5.x series (5.1, 5.2, 5.3, 5.4, 5.5, codex, chat, pro, mini, nano)
- OpenAI o-series reasoning (o1, o1-mini, o3, o3-mini, o3-pro, o4, o4-mini)
- OpenAI GPT-4.x series (4, 4o, 4o-mini, 4.1, 4.1-mini, 4.1-nano)
- Non-OpenAI via Azure AI Foundry: DeepSeek, Meta Llama, Mistral, Cohere, Phi,
  NVIDIA Nemotron, Grok, Kimi, Jamba, MiniMax, gpt-oss, and others.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx

from .base import BaseLLMClient, LLMResponse
from app.util.config import settings

logger = logging.getLogger(__name__)


class AzureAPIPattern(Enum):
    """Azure API endpoint patterns."""
    AZURE_OPENAI_LEGACY = "azure_openai_legacy"
    AZURE_OPENAI_V1 = "azure_openai_v1"
    AZURE_RESPONSES = "azure_responses"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"


@dataclass
class ModelFamilyConfig:
    """Configuration for a model family."""
    family: str
    supported_patterns: list[AzureAPIPattern]
    default_pattern: AzureAPIPattern
    prefers_developer_role: bool = False
    uses_max_completion_tokens: bool = False
    supports_reasoning_effort: bool = False
    supports_temperature: bool = True


class AzureProvider(BaseLLMClient):
    """Azure provider with comprehensive model support and intelligent API routing."""

    name = "azure"

    _MODEL_REGISTRY: dict[str, ModelFamilyConfig] = {
        # GPT-5.x series
        "gpt-5.5": ModelFamilyConfig("gpt-5.5", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.4": ModelFamilyConfig("gpt-5.4", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.3-codex": ModelFamilyConfig("gpt-5.3-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.3-chat": ModelFamilyConfig("gpt-5.3-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2-codex": ModelFamilyConfig("gpt-5.2-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2-chat": ModelFamilyConfig("gpt-5.2-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.2": ModelFamilyConfig("gpt-5.2", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex-max": ModelFamilyConfig("gpt-5.1-codex-max", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex": ModelFamilyConfig("gpt-5.1-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-codex-mini": ModelFamilyConfig("gpt-5.1-codex-mini", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1-chat": ModelFamilyConfig("gpt-5.1-chat", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5.1": ModelFamilyConfig("gpt-5.1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-pro": ModelFamilyConfig("gpt-5-pro", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-codex": ModelFamilyConfig("gpt-5-codex", [AzureAPIPattern.AZURE_RESPONSES, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_RESPONSES, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5": ModelFamilyConfig("gpt-5", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-mini": ModelFamilyConfig("gpt-5-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "gpt-5-nano": ModelFamilyConfig("gpt-5-nano", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),

        # o-series
        "o4-mini": ModelFamilyConfig("o4-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o4": ModelFamilyConfig("o4", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3-pro": ModelFamilyConfig("o3-pro", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3-mini": ModelFamilyConfig("o3-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o3": ModelFamilyConfig("o3", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),
        "o1-mini": ModelFamilyConfig("o1-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=False, supports_temperature=False),
        "o1": ModelFamilyConfig("o1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_RESPONSES], AzureAPIPattern.AZURE_OPENAI_V1, prefers_developer_role=True, uses_max_completion_tokens=True, supports_reasoning_effort=True, supports_temperature=False),

        # GPT-4.x
        "gpt-4.1-nano": ModelFamilyConfig("gpt-4.1-nano", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4.1-mini": ModelFamilyConfig("gpt-4.1-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4.1": ModelFamilyConfig("gpt-4.1", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4o-mini": ModelFamilyConfig("gpt-4o-mini", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4o": ModelFamilyConfig("gpt-4o", [AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_OPENAI_LEGACY], AzureAPIPattern.AZURE_OPENAI_V1),
        "gpt-4-turbo": ModelFamilyConfig("gpt-4-turbo", [AzureAPIPattern.AZURE_OPENAI_LEGACY, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_OPENAI_LEGACY),
        "gpt-4": ModelFamilyConfig("gpt-4", [AzureAPIPattern.AZURE_OPENAI_LEGACY, AzureAPIPattern.AZURE_OPENAI_V1], AzureAPIPattern.AZURE_OPENAI_LEGACY),

        # Azure AI Foundry / non-OpenAI
        "deepseek": ModelFamilyConfig("deepseek", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "llama": ModelFamilyConfig("llama", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "meta-llama": ModelFamilyConfig("meta-llama", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "mistral": ModelFamilyConfig("mistral", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "cohere": ModelFamilyConfig("cohere", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "phi": ModelFamilyConfig("phi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "nemotron": ModelFamilyConfig("nemotron", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "grok": ModelFamilyConfig("grok", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "jamba": ModelFamilyConfig("jamba", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "minimax": ModelFamilyConfig("minimax", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "kimi": ModelFamilyConfig("kimi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "claude": ModelFamilyConfig("claude", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "anthropic": ModelFamilyConfig("anthropic", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "gpt-oss": ModelFamilyConfig("gpt-oss", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "qwen": ModelFamilyConfig("qwen", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "granite": ModelFamilyConfig("granite", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "command": ModelFamilyConfig("command", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "wizard": ModelFamilyConfig("wizard", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "falcon": ModelFamilyConfig("falcon", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "mamba": ModelFamilyConfig("mamba", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "nous": ModelFamilyConfig("nous", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "yi": ModelFamilyConfig("yi", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
        "baichuan": ModelFamilyConfig("baichuan", [AzureAPIPattern.AZURE_AI_FOUNDRY], AzureAPIPattern.AZURE_AI_FOUNDRY),
    }

    def __init__(self) -> None:
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.endpoint = settings.AZURE_OPENAI_ENDPOINT
        self.deployment = settings.AZURE_OPENAI_DEPLOYMENT_ID
        self.api_version = settings.AZURE_OPENAI_API_VERSION or "2024-12-01-preview"
        self.responses_api_version = "2025-04-01-preview"
        self.v1_api_version = ""

        self.client = httpx.AsyncClient(
            headers={"api-key": self.api_key, "Content-Type": "application/json"},
            timeout=httpx.Timeout(120.0, connect=10.0),
        )

    def _detect_model_config(self, model_or_deployment: str) -> ModelFamilyConfig:
        model_lower = model_or_deployment.lower().replace("_", "-").replace(" ", "-")
        best_match: Optional[str] = None
        best_len = 0
        for prefix in self._MODEL_REGISTRY:
            prefix_lower = prefix.lower()
            if model_lower.startswith(prefix_lower) and len(prefix_lower) > best_len:
                best_match = prefix
                best_len = len(prefix_lower)
        if best_match:
            return self._MODEL_REGISTRY[best_match]
        for prefix, config in self._MODEL_REGISTRY.items():
            if prefix.lower() in model_lower:
                return config
        return ModelFamilyConfig(
            family="unknown",
            supported_patterns=[AzureAPIPattern.AZURE_OPENAI_LEGACY],
            default_pattern=AzureAPIPattern.AZURE_OPENAI_LEGACY,
        )

    def _resolve_pattern(self, config: ModelFamilyConfig) -> AzureAPIPattern:
        return config.default_pattern

    def _get_url(self, deployment: str, pattern: AzureAPIPattern) -> str:
        base = self.endpoint.rstrip("/")
        if pattern == AzureAPIPattern.AZURE_OPENAI_LEGACY:
            return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={self.api_version}"
        elif pattern == AzureAPIPattern.AZURE_OPENAI_V1:
            if "/openai/v1" not in base:
                base = f"{base}/openai/v1"
            url = f"{base}/chat/completions"
            if self.v1_api_version:
                url += f"?api-version={self.v1_api_version}"
            return url
        elif pattern == AzureAPIPattern.AZURE_RESPONSES:
            if "/openai/v1" not in base:
                base = f"{base}/openai/v1"
            return f"{base}/responses?api-version={self.responses_api_version}"
        elif pattern == AzureAPIPattern.AZURE_AI_FOUNDRY:
            if ".services.ai.azure.com" in base or (".azure.com" in base and ".openai.azure.com" not in base):
                return f"{base}/chat/completions"
            else:
                if "/openai/v1" not in base:
                    base = f"{base}/openai/v1"
                return f"{base}/chat/completions"
        raise RuntimeError(f"Unsupported API pattern: {pattern}")

    def _build_messages(self, config: ModelFamilyConfig, system_prompt: Optional[str], user_prompt: str) -> list[dict]:
        messages = []
        if system_prompt:
            role = "developer" if config.prefers_developer_role else "system"
            messages.append({"role": role, "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _build_request_body(self, pattern: AzureAPIPattern, config: ModelFamilyConfig,
                            messages: list[dict], deployment: str,
                            temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> dict:
        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            inputs = []
            for msg in messages:
                if msg["role"] in ("system", "developer"):
                    inputs.append({"role": "developer", "content": msg["content"]})
                else:
                    inputs.append({"role": msg["role"], "content": msg["content"]})
            body: dict[str, Any] = {"model": deployment, "input": inputs}
            if max_tokens is not None and max_tokens > 0:
                body["max_output_tokens"] = max_tokens
            body.pop("max_tokens", None)
            body.pop("temperature", None)
            body.pop("top_p", None)
            body.pop("frequency_penalty", None)
            body.pop("presence_penalty", None)
            body.pop("messages", None)
            return body
        else:
            body: dict[str, Any] = {"messages": messages}
            if pattern in (AzureAPIPattern.AZURE_OPENAI_V1, AzureAPIPattern.AZURE_AI_FOUNDRY):
                body["model"] = deployment
            if temperature is not None and config.supports_temperature:
                body["temperature"] = temperature
            if max_tokens is not None:
                if config.uses_max_completion_tokens and pattern != AzureAPIPattern.AZURE_AI_FOUNDRY:
                    body["max_completion_tokens"] = max_tokens
                else:
                    body["max_tokens"] = max_tokens
            return body

    def _parse_response(self, pattern: AzureAPIPattern, response_json: dict) -> str:
        if pattern == AzureAPIPattern.AZURE_RESPONSES:
            text = response_json.get("output_text")
            if text:
                return text
            output = response_json.get("output", [])
            if output and isinstance(output, list):
                content = output[0].get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "")
            return json.dumps(response_json)
        choices = response_json.get("choices", [])
        if choices and isinstance(choices, list):
            message = choices[0].get("message", {})
            return message.get("content", "")
        return json.dumps(response_json)

    async def generate_sql(self, schema: str, domain_context: str, user_query: str, dialect: str) -> LLMResponse:
        system_prompt = self._build_prompt(schema, domain_context, dialect)
        config = self._detect_model_config(self.deployment)
        pattern = self._resolve_pattern(config)
        url = self._get_url(self.deployment, pattern)
        messages = self._build_messages(config, system_prompt, user_query)
        temperature = 0.1 if config.supports_temperature else None
        max_tokens = 4000
        body = self._build_request_body(pattern, config, messages, self.deployment, temperature, max_tokens)
        try:
            response = await self.client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            content = self._parse_response(pattern, data)
            usage = data.get("usage")
            return LLMResponse(content=content.strip(), model=self.deployment, usage=usage)
        except httpx.HTTPStatusError as e:
            logger.error("Azure HTTP error: %s - %s", e.response.status_code, e.response.text)
            raise RuntimeError(f"Azure API error {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            logger.error("Azure API error: %s", e)
            raise
