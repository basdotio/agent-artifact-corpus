"""
datashaper.llm
===========

LLM provider abstraction layer.

``LLMClient`` is the abstract interface every provider must implement.
``OpenAIClient`` and ``GeminiClient`` are the two concrete implementations.
``_build_client()`` is the factory used by ``GenericLabeler``.

Provider-specific SDK imports are deferred to ``__init__`` so that a missing
optional dependency (e.g. ``openai`` when using Gemini only) raises at
instantiation time rather than at server startup.

Concurrency constants
---------------------
``_PARALLEL_BATCHES``  — how many LLM calls are fired simultaneously.
``_BATCH_DELAY``       — seconds between consecutive chunks of parallel calls;
                         helps avoid rate-limit bursts.
``_RETRY_DELAY``       — seconds to wait before starting a retry round.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod

from .models import T

# ---------------------------------------------------------------------------
# Concurrency knobs — tune these if you hit rate limits
# ---------------------------------------------------------------------------

_PARALLEL_BATCHES = 5    # batches sent to the LLM simultaneously
_BATCH_DELAY      = 1.0  # seconds to wait between chunks of parallel batches
_RETRY_DELAY      = 2.0  # seconds to wait before each retry round

# Conservative defaults that balance cost and quality for each provider
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
}

# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Common interface for all LLM providers."""

    @abstractmethod
    async def parse_structured_output(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T: ...


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in the environment.")
        import openai
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def parse_structured_output(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        # Append a JSON reminder to the user turn; the response_format
        # parameter enforces JSON mode on the OpenAI side.
        augmented_user = f"{user_prompt}\n\nReturn valid JSON only — no markdown, no prose."
        response = await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": augmented_user},
            ],
            response_format={"type": "json_object"},
            timeout=300,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response.")
        return response_model(**json.loads(content))


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


class GeminiClient(LLMClient):
    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")
        from google import genai
        self._client = genai.Client(api_key=api_key)

    async def parse_structured_output(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        from google.genai import types

        # Gemini does not support a separate system role via this API surface,
        # so we prepend the system prompt to the user message.
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model.model_json_schema(),
        )
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)])],
            config=config,
        )
        return response_model(**json.loads(response.text))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _build_client(provider: str) -> LLMClient:
    """Return a fully initialised LLMClient for the given provider name."""
    if provider == "openai":
        return OpenAIClient()
    if provider == "gemini":
        return GeminiClient()
    raise ValueError(f"Unknown provider '{provider}'. Choose 'openai' or 'gemini'.")
