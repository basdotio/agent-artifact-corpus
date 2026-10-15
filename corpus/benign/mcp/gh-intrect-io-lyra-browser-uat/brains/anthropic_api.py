"""The persona played by a Claude model over the Anthropic Messages API.

A manual tool-use loop rather than the SDK's tool runner: tool results here
carry image blocks next to the text, browser actions in one turn run strictly
in order with the rest refused after a failure, and the same loop shape serves
the OpenAI-compatible brain. Messages are only ever appended to.
"""

from __future__ import annotations

import base64
from typing import Any

from ..report import BrainInfo
from ..spec import BrainSpec
from .base import BrainError, BrainSession, LoopBrain

DEFAULT_MODEL = "claude-opus-5-5"
NOT_EXECUTED = "Not executed: an earlier action in this turn failed."
NUDGE = (
    "You stopped without calling finish. Continue the run, or call finish now with "
    "the outcome so far."
)
CUT_OFF = "Your last turn was cut off by the output limit. Continue from where you were."
MAX_NUDGES = 3

# USD per million tokens (input, output, cache read), from the Claude API price
# list as of 2026-09-25. An estimate for the report, not a bill; unknown models
# report no cost.
_PRICES: dict[str, tuple[float, float, float]] = {
    "claude-fable-5-1": (10.0, 50.0, 1.0),
    "claude-fable-5": (10.0, 50.0, 1.0),
    "claude-opus-5-5": (4.0, 20.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 0.50),
    "claude-opus-4": (5.0, 25.0, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0, 0.20),
    "claude-sonnet-5": (2.0, 10.0, 0.20),
    "claude-sonnet-4": (3.0, 15.0, 0.30),
    "claude-haiku-4": (1.0, 5.0, 0.10),
}


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int, cache_read: int
) -> float | None:
    for prefix, (inp, out, cached) in sorted(_PRICES.items(), key=lambda kv: -len(kv[0])):
        if model.startswith(prefix):
            return round(
                (input_tokens * inp + output_tokens * out + cache_read * cached) / 1_000_000, 4
            )
    return None


class AnthropicBrain(LoopBrain):
    backend = "anthropic"

    def __init__(self, spec: BrainSpec) -> None:
        self.spec = spec
        self.model = spec.model or DEFAULT_MODEL

    def _client(self) -> Any:
        try:
            import anthropic
        except ImportError as exc:
            raise BrainError(
                "the anthropic SDK is not installed: pip install 'lyra-browser[uat]'"
            ) from exc
        # Credentials come from the environment or an `ant auth login` profile; the
        # SDK resolves them and says so if there are none.
        return anthropic.AsyncAnthropic()

    def _tools(self, session: BrainSession) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in session.tools
        ]

    @staticmethod
    def _result_content(outcome) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"type": "text", "text": outcome.text or "{}"}]
        for png in outcome.images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.b64encode(png).decode("ascii"),
                    },
                }
            )
        return content

    async def run(self, session: BrainSession) -> BrainInfo:
        import anthropic

        client = self._client()
        system = [
            {"type": "text", "text": session.system_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": session.task_prompt}]
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.spec.max_tokens,
            "system": system,
            "tools": self._tools(session),
            # Browser actions are order-dependent: one call per turn.
            "tool_choice": {"type": "auto", "disable_parallel_tool_use": True},
        }
        if self.spec.effort:
            request["output_config"] = {"effort": self.spec.effort}
        request.update(self.spec.extra)

        info = BrainInfo(backend=self.backend, model=self.model)
        nudges = 0
        for _ in range(self.spec.max_turns):
            try:
                response = await client.messages.create(messages=messages, **request)
            except anthropic.AuthenticationError as exc:
                raise BrainError(f"anthropic: authentication failed: {exc.message}") from exc
            except anthropic.BadRequestError as exc:
                raise BrainError(f"anthropic: request rejected: {exc.message}") from exc
            except anthropic.APIStatusError as exc:
                raise BrainError(f"anthropic: API error {exc.status_code}: {exc.message}") from exc
            except anthropic.APIConnectionError as exc:
                raise BrainError(f"anthropic: connection failed: {exc}") from exc
            info.turns += 1
            usage = getattr(response, "usage", None)
            if usage is not None:
                info.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
                info.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
                info.cache_read_tokens += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
                info.cache_write_tokens += int(
                    getattr(usage, "cache_creation_input_tokens", 0) or 0
                )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                category = getattr(details, "category", None) if details else None
                raise BrainError(f"anthropic: the model refused (category {category})")
            tool_uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
            if not tool_uses:
                if session.finished:
                    break
                if response.stop_reason == "max_tokens":
                    messages.append({"role": "user", "content": CUT_OFF})
                    continue
                nudges += 1
                if nudges > MAX_NUDGES:
                    break
                messages.append({"role": "user", "content": NUDGE})
                continue

            results: list[dict[str, Any]] = []
            failed = False
            for use in tool_uses:
                if failed:
                    results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": use.id,
                            "content": NOT_EXECUTED,
                            "is_error": True,
                        }
                    )
                    continue
                outcome = await session.call(use.name, dict(use.input or {}))
                block: dict[str, Any] = {
                    "type": "tool_result",
                    "tool_use_id": use.id,
                    "content": self._result_content(outcome),
                }
                if outcome.is_error:
                    block["is_error"] = True
                    failed = True
                results.append(block)
            messages.append({"role": "user", "content": results})
            if session.finished:
                break
        info.cost_usd = estimate_cost(
            self.model, info.input_tokens, info.output_tokens, info.cache_read_tokens
        )
        return info
