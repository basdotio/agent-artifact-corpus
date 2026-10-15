"""Model adapters. One method, ``chat``: messages and tools in, one assistant turn out.

Only Ollama (local open-weight models) is implemented. Frontier adapters come later; each paid
run is approved separately.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class Reply:
    content: str
    tool_calls: list[dict[str, Any]]  # [{"id", "name", "arguments"}]
    thinking: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    seconds: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)


class ModelError(RuntimeError):
    pass


class MalformedToolCall(ModelError):
    """The model wrote a tool call its server could not parse: the model's failure, not the framework's."""


class OllamaModel:
    """Ollama's native /api/chat, which (unlike its OpenAI endpoint) honours num_ctx and think."""

    def __init__(self, name: str, *, effort: str | None = None, num_ctx: int = 32768,
                 base_url: str = "http://127.0.0.1:11434", timeout: float = 600.0,
                 temperature: float | None = None, seed: int | None = None) -> None:
        self.name, self.effort, self.num_ctx = name, effort, num_ctx
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.temperature, self.seed = temperature, seed

    def describe(self) -> dict[str, Any]:
        return {"provider": "ollama", "model": self.name, "effort": self.effort, "num_ctx": self.num_ctx,
                "temperature": self.temperature, "seed": self.seed}

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Reply:
        options: dict[str, Any] = {"num_ctx": self.num_ctx}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.seed is not None:
            options["seed"] = self.seed
        body: dict[str, Any] = {"model": self.name, "stream": False, "messages": [_to_ollama(m) for m in messages],
                                "tools": tools, "options": options}
        if self.effort:
            body["think"] = self.effort
        last: Exception | None = None
        for attempt in range(3):
            started = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=body)
                if response.status_code >= 500 and "error parsing tool call" in response.text:
                    raise MalformedToolCall(response.text[:400])
                if response.status_code >= 500:
                    raise ModelError(f"ollama HTTP {response.status_code}: {response.text[:200]}")
                if response.status_code != 200:
                    # A 4xx is not transient (bad request, unknown model): do not retry.
                    raise ModelError(f"ollama HTTP {response.status_code}: {response.text[:300]}")
                data = response.json()
                break
            except (httpx.HTTPError, ModelError) as exc:
                last = exc
                if isinstance(exc, MalformedToolCall) or (isinstance(exc, ModelError) and "HTTP 4" in str(exc)):
                    raise
                await asyncio.sleep(3 * (attempt + 1))
        else:
            raise ModelError(f"ollama failed after retries: {last}")
        message = data.get("message") or {}
        calls = []
        for i, call in enumerate(message.get("tool_calls") or []):
            fn = call.get("function") or {}
            args = fn.get("arguments")
            calls.append({"id": call.get("id") or f"call_{i}", "name": fn.get("name", ""),
                          "arguments": args if isinstance(args, dict) else {}})
        return Reply(
            content=message.get("content") or "",
            tool_calls=calls,
            thinking=message.get("thinking") or "",
            usage={"prompt_tokens": data.get("prompt_eval_count") or 0, "completion_tokens": data.get("eval_count") or 0},
            seconds=round(time.monotonic() - started, 2),
        )


def _to_ollama(message: dict[str, Any]) -> dict[str, Any]:
    """The runner's neutral message format to Ollama's."""
    if message["role"] == "assistant" and message.get("tool_calls"):
        return {"role": "assistant", "content": message.get("content") or "",
                "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}} for c in message["tool_calls"]]}
    if message["role"] == "tool":
        return {"role": "tool", "content": message["content"], "tool_name": message.get("name", "")}
    return {"role": message["role"], "content": message.get("content") or ""}


def make_model(spec: str, *, effort: str | None, **kwargs: Any) -> Any:
    provider, _, name = spec.partition(":")
    if provider == "ollama" and name:
        return OllamaModel(name, effort=effort, **kwargs)
    if provider == "claude-code" and name:
        from .claude_code import ClaudeCodeModel
        return ClaudeCodeModel(name, effort=effort, **kwargs)
    raise ValueError(f"unsupported model {spec!r}; use ollama:<model> or claude-code:<sonnet|opus|model id>")
