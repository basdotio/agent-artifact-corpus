"""The persona played by a model behind an OpenAI-compatible chat completions API.

One brain, three presets: OpenRouter, Ollama Cloud, and any endpoint given by
``base_url`` (``openai-compat``). Tool calling is the function-calling dialect;
images from ``screenshot``/``read_image`` are sent as a user message with data
URLs right after the tool results, because the ``tool`` role carries text only.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from ..report import BrainInfo
from ..spec import BrainSpec
from .anthropic_api import CUT_OFF, MAX_NUDGES, NOT_EXECUTED, NUDGE
from .base import BrainError, BrainSession, LoopBrain


@dataclass(frozen=True, slots=True)
class Preset:
    base_url: str | None
    api_key_env: str
    # Whether the endpoint accepts ``parallel_tool_calls``; Ollama rejects unknown
    # parameters, so there we rely on the prompt and sequential execution instead.
    parallel_tool_calls_param: bool
    extra_headers: dict[str, str] | None = None
    # Sent as ``extra_body``: OpenRouter reports what a request cost when asked.
    extra_body: dict[str, Any] | None = None


PRESETS: dict[str, Preset] = {
    "openrouter": Preset(
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        parallel_tool_calls_param=True,
        extra_headers={
            "HTTP-Referer": "https://github.com/Intrect-io/lyra-browser",
            "X-Title": "lyra-browser UAT",
        },
        extra_body={"usage": {"include": True}},
    ),
    "ollama": Preset(
        base_url="https://ollama.com/v1",
        api_key_env="OLLAMA_API_KEY",
        parallel_tool_calls_param=False,
    ),
    "openai-compat": Preset(
        base_url=None, api_key_env="OPENAI_API_KEY", parallel_tool_calls_param=True
    ),
}


class OpenAICompatBrain(LoopBrain):
    def __init__(self, spec: BrainSpec) -> None:
        self.spec = spec
        self.backend = spec.backend
        preset = PRESETS.get(spec.backend)
        if preset is None:
            raise BrainError(f"not an OpenAI-compatible backend: {spec.backend}")
        self.preset = preset
        self.base_url = spec.base_url or preset.base_url
        self.api_key_env = spec.api_key_env or preset.api_key_env
        if not self.base_url:
            raise BrainError(f"{spec.backend}: base_url is required")
        if not spec.model:
            raise BrainError(f"{spec.backend}: a model name is required (--model)")
        self.model = spec.model

    def _client(self) -> Any:
        try:
            import openai
        except ImportError as exc:
            raise BrainError(
                "the openai SDK is not installed: pip install 'lyra-browser[uat]'"
            ) from exc
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise BrainError(f"{self.backend}: set {self.api_key_env} in the environment")
        return openai.AsyncOpenAI(
            base_url=self.base_url, api_key=api_key, default_headers=self.preset.extra_headers
        )

    def _tools(self, session: BrainSession) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in session.tools
        ]

    async def run(self, session: BrainSession) -> BrainInfo:
        import openai

        client = self._client()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": session.system_prompt},
            {"role": "user", "content": session.task_prompt},
        ]
        request: dict[str, Any] = {
            "model": self.model,
            "tools": self._tools(session),
            "max_tokens": self.spec.max_tokens,
        }
        if self.preset.parallel_tool_calls_param:
            request["parallel_tool_calls"] = False
        if self.preset.extra_body:
            request["extra_body"] = dict(self.preset.extra_body)
        request.update(self.spec.extra)

        info = BrainInfo(backend=self.backend, model=self.model)
        nudges = 0
        for _ in range(self.spec.max_turns):
            try:
                response = await client.chat.completions.create(messages=messages, **request)
            except openai.AuthenticationError as exc:
                raise BrainError(f"{self.backend}: authentication failed: {exc}") from exc
            except openai.BadRequestError as exc:
                raise BrainError(f"{self.backend}: request rejected: {exc}") from exc
            except openai.APIStatusError as exc:
                raise BrainError(f"{self.backend}: API error {exc.status_code}: {exc}") from exc
            except openai.APIConnectionError as exc:
                raise BrainError(f"{self.backend}: connection failed: {exc}") from exc
            info.turns += 1
            usage = getattr(response, "usage", None)
            if usage is not None:
                info.input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                info.output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
                details = getattr(usage, "prompt_tokens_details", None)
                info.cache_read_tokens += int(getattr(details, "cached_tokens", 0) or 0)
                # Not part of the OpenAI schema: OpenRouter adds what the request cost.
                cost = getattr(usage, "cost", None)
                if isinstance(cost, int | float):
                    info.cost_usd = round((info.cost_usd or 0.0) + float(cost), 6)
            if not response.choices:
                raise BrainError(f"{self.backend}: empty response")
            choice = response.choices[0]
            message = choice.message
            tool_calls = list(getattr(message, "tool_calls", None) or [])

            assistant: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
            if tool_calls:
                assistant["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments or "{}",
                        },
                    }
                    for call in tool_calls
                ]
            messages.append(assistant)

            if not tool_calls:
                if session.finished:
                    break
                if getattr(choice, "finish_reason", "") == "length":
                    messages.append({"role": "user", "content": CUT_OFF})
                    continue
                nudges += 1
                if nudges > MAX_NUDGES:
                    break
                messages.append({"role": "user", "content": NUDGE})
                continue

            images: list[tuple[str, bytes]] = []
            failed = False
            for call in tool_calls:
                if failed:
                    messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": NOT_EXECUTED}
                    )
                    continue
                try:
                    args = json.loads(call.function.arguments or "{}")
                    if not isinstance(args, dict):
                        raise ValueError("arguments must be a JSON object")
                except ValueError as exc:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": f"Error: tool arguments were not valid JSON ({exc}).",
                        }
                    )
                    failed = True
                    continue
                outcome = await session.call(call.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": outcome.text or "{}"}
                )
                images.extend((call.function.name, png) for png in outcome.images)
                if outcome.is_error:
                    failed = True
            if images:
                content: list[dict[str, Any]] = [
                    {"type": "text", "text": "Images from the tool results above, in order."}
                ]
                for _name, png in images:
                    content.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64,"
                                + base64.b64encode(png).decode("ascii")
                            },
                        }
                    )
                messages.append({"role": "user", "content": content})
            if session.finished:
                break
        return info
