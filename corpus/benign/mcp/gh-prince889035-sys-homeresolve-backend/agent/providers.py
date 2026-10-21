"""Anthropic Messages HTTP adapter. No SDK/dependency changes; no automatic paid retries."""

import asyncio
import json
import os
from typing import Any, Protocol

import httpx
from pydantic import ValidationError

from backend.agent.models import AgentError, ModelTurn, ResponsePlan, ToolCall
from backend.agent.prompts import SYSTEM_PROMPT


class Provider(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                       context: dict[str, Any]) -> ModelTurn: ...


def parse_message(body: dict[str, Any]) -> ModelTurn:
    try:
        content = body["content"]
        if not isinstance(content, list) or not content or len(content) > 8:
            raise ValueError
        calls = []
        texts = []
        for block in content:
            if block["type"] == "tool_use":
                calls.append(ToolCall(call_id=block["id"], name=block["name"], arguments=block["input"]))
            elif block["type"] == "text" and isinstance(block["text"], str):
                texts.append(block["text"])
            else:
                raise ValueError
        if calls:
            if body["stop_reason"] != "tool_use" or len({call.call_id for call in calls}) != len(calls):
                raise ValueError
            return ModelTurn(calls=calls)
        if body["stop_reason"] != "end_turn" or len(texts) != 1:
            raise ValueError
        return ModelTurn(final=ResponsePlan.model_validate(json.loads(texts[0])))
    except (KeyError, TypeError, ValueError, ValidationError):
        raise AgentError("Provider returned malformed or truncated tool/response content.") from None


class AnthropicProvider:
    """Use a fixed provider host; credentials only from the environment."""

    def __init__(self, *, allow_paid: bool = False, transport: httpx.AsyncBaseTransport | None = None,
                 timeout: float = 20) -> None:
        if not allow_paid:
            raise AgentError("LLM mode requires explicit --allow-paid-api opt-in. Demo mode uses no external inference.")
        self._key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = os.environ.get("HOMERESOLVE_MODEL", "claude-haiku-4-5-20251001")
        if not self._key or self._key.startswith("replace-"):
            raise AgentError("Set ANTHROPIC_API_KEY in the environment before opting into LLM mode.")
        if not 0 < timeout <= 30:
            raise AgentError("Invalid provider timeout.")
        self._transport, self.timeout = transport, timeout
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                       context: dict[str, Any]) -> ModelTurn:
        try:
            async with asyncio.timeout(self.timeout):
                async with httpx.AsyncClient(transport=self._transport, timeout=self.timeout,
                                             trust_env=False, follow_redirects=False) as client:
                    response = await client.post("https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": self._key, "anthropic-version": "2023-06-01"},
                        json={"model": self.model, "max_tokens": 768, "system": SYSTEM_PROMPT,
                              "tools": tools, "messages": messages})
                    if response.status_code == 429:
                        raise AgentError("LLM rate limit reached. No automatic paid retry; try again later or use demo mode.")
                    if response.status_code != 200:
                        raise AgentError("LLM provider unavailable or rejected configuration. No provider details were logged.")
                    if len(response.content) > 64000:
                        raise AgentError("LLM response exceeded the allowed size.")
                    body = response.json()
                    turn = parse_message(body)
                    usage = body.get("usage", {})
                    for field in self.usage:
                        count = usage.get(field, 0)
                        if isinstance(count, int) and count >= 0:
                            self.usage[field] += count
                    return turn
        except AgentError:
            raise
        except Exception:
            raise AgentError("LLM provider request timed out, failed, or returned invalid data. No paid retry was attempted.") from None
