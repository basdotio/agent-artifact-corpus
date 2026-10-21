"""Local-only Ollama chat/tool adapter using the documented non-streaming HTTP API."""

import asyncio
import json
import os
import re
from collections import deque
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from backend.agent.models import AgentError, ModelTurn, ResponsePlan, ToolCall
from backend.agent.prompts import SYSTEM_PROMPT

DEFAULT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"


def convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate the existing provider-neutral tool blocks into Ollama messages."""
    output: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    names: dict[str, str] = {}
    for message in messages:
        content = message["content"]
        if isinstance(content, str):
            output.append({"role": message["role"], "content": content})
        elif message["role"] == "assistant":
            calls = []
            for block in content:
                names[block["id"]] = block["name"]
                calls.append({"function": {"name": block["name"], "arguments": block["input"]}})
            output.append({"role": "assistant", "content": "", "tool_calls": calls})
        else:
            for block in content:
                output.append({"role": "tool", "tool_name": names[block["tool_use_id"]],
                               "content": block["content"]})
    return output


def parse_ollama(body: dict[str, Any]) -> ModelTurn:
    try:
        if body.get("done") is not True or body.get("done_reason") not in (None, "stop"):
            raise ValueError
        message = body["message"]
        if message["role"] != "assistant":
            raise ValueError
        calls = message.get("tool_calls", [])
        if not isinstance(calls, list) or len(calls) > 8:
            raise ValueError
        if calls:
            return ModelTurn(calls=[ToolCall(call_id=c.get("id") or str(uuid4()), name=c["function"]["name"],
                                             arguments=c["function"]["arguments"]) for c in calls])
        return ModelTurn(final=ResponsePlan.model_validate(json.loads(message["content"])))
    except (KeyError, ValueError, TypeError):
        raise AgentError("Local LLM returned malformed or truncated tool/response content.") from None


class OllamaProvider:
    """Never pulls models, follows redirects, uses proxies, or contacts cloud hosts."""

    def __init__(self, *, endpoint: str | None = None, model: str | None = None,
                 timeout: float = 45, load_timeout: float = 90,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.endpoint = endpoint or os.getenv("HOMERESOLVE_OLLAMA_URL", "http://127.0.0.1:11434")
        parsed = urlsplit(self.endpoint)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.username or parsed.password):
            raise AgentError("Ollama endpoint must be a loopback HTTP origin without credentials or a path.")
        try:
            if parsed.port == 0:
                raise ValueError
        except ValueError:
            raise AgentError("Invalid Ollama endpoint port.") from None
        self.endpoint = self.endpoint.rstrip("/")
        self.model = model or os.getenv("HOMERESOLVE_OLLAMA_MODEL", DEFAULT_MODEL)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?", self.model) or "cloud" in self.model.casefold():
            raise AgentError("Choose an installed local model tag; cloud models are not permitted.")
        if not 0 < timeout <= 60:
            raise AgentError("Invalid local provider timeout.")
        if not 0 < load_timeout <= 90:
            raise AgentError("Invalid local model load timeout.")
        self.timeout, self._transport = timeout, transport
        self.load_timeout = load_timeout
        self.metadata_timeout = min(5, timeout)
        self.completion_timeout = self.metadata_timeout + load_timeout + timeout
        # Safe, bounded metadata only: no messages, document text, or credentials.
        self.observations: deque[dict[str, Any]] = deque(maxlen=64)

    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                       context: dict[str, Any]) -> ModelTurn:
        started = perf_counter()
        phase, phase_started = "readiness", started
        try:
            payload = {"model": self.model, "stream": False, "think": False, "keep_alive": "2m",
                       "messages": convert_messages(messages),
                       "tools": [{"type": "function", "function": {"name": t["name"],
                                   "description": t["description"], "parameters": t["input_schema"]}} for t in tools],
                       "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 512}}
            # Once evidence is complete, constrain the model's answer contract, not its facts.
            # Tool selections before this phase are always produced by the model.
            names = {r["name"] for r in context.get("turn_results", [])}
            selected = context.get("selected")
            if (selected and context.get("request", "").strip().casefold() == selected["id"].casefold()
                    and names == {"find_appliance"}):
                payload["messages"].append({"role": "system", "content":
                    "The user supplied an appliance ID to resolve the previous clarification. "
                    "Discovery selected one appliance, but no purchase or warranty evidence has been read. "
                    "Continue the investigation with get_purchase_evidence and evaluate_warranty for that "
                    "selected ID before returning a response plan. Do not invent source references."})
            if "evaluate_warranty" in names or "get_repair_history" in names:
                payload.pop("tools")
                schema = ResponsePlan.model_json_schema()
                if "get_repair_history" in names:
                    schema["properties"] = {"action": {"type": "string", "enum": ["history"]}}
                    schema["required"] = ["action"]
                    selected_ids = re.findall(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b", context.get("request", ""))
                    if selected_ids:
                        schema["properties"]["proposal_id"] = {"enum": [None, *selected_ids]}
                else:
                    schema["properties"].pop("proposal_id")
                    schema["properties"]["action"]["enum"] = ["report", "prepare", "clarify", "unsupported"]
                    schema["required"] = ["action", "appliance_id", "warranty_status", "source_refs"]
                payload["format"] = schema
                payload["messages"].append({"role": "system", "content":
                    "Now return only the final response-plan JSON. Use action history for saved-history questions, "
                    "otherwise report or prepare. Copy actual status and references exactly. "
                    "Include source_refs even if empty; copy every source from the warranty tool. "
                    "Unknown warranty status is the string unknown, not null. Do not add prose or fields."})
            if len(json.dumps(payload)) > 60000:
                raise AgentError("Local LLM request exceeds the bounded context.")
            async with asyncio.timeout(self.completion_timeout):
                async with httpx.AsyncClient(transport=self._transport, timeout=self.timeout,
                                             trust_env=False, follow_redirects=False) as client:
                    # Confirm it is installed and not a local alias pointing at a cloud model.
                    async with asyncio.timeout(self.metadata_timeout):
                        shown = await client.post(self.endpoint + "/api/show", json={"model": self.model})
                        if shown.status_code != 200:
                            raise AgentError("Local model is unavailable. Install it explicitly or select demo mode; no download was attempted.")
                        info = shown.json()
                        if info.get("remote_host") or info.get("remote_model") or info.get("details", {}).get("format") != "gguf":
                            raise AgentError("Only an installed local GGUF model is permitted.")
                        if "tools" not in info.get("capabilities", []):
                            raise AgentError("The configured local model does not support tool calling.")
                        loaded = await client.get(self.endpoint + "/api/ps")
                        if loaded.status_code != 200:
                            raise AgentError("Local model readiness is unavailable. Retry explicitly; no fallback was attempted.")
                        ready = any(item.get("name") == self.model and item.get("context_length") == 8192
                                    for item in loaded.json()["models"])
                    if not ready:
                        # Empty chat loads only the validated installed model, with the same context as inference.
                        phase, phase_started = "model_load", perf_counter()
                        async with asyncio.timeout(self.load_timeout):
                            warm = await client.post(self.endpoint + "/api/chat", timeout=self.load_timeout, json={
                                "model": self.model, "messages": [], "stream": False, "keep_alive": "2m",
                                "options": {"num_ctx": 8192}})
                        if warm.status_code != 200 or warm.json().get("done") is not True or warm.json().get("done_reason") != "load":
                            raise AgentError("Local model loading failed. Retry explicitly; no fallback or download was attempted.")
                        self.observations.append({"model": self.model, "phase": phase, "outcome": "ok",
                                                  "elapsed_seconds": round(perf_counter() - phase_started, 3)})
                    phase, phase_started = "generation", perf_counter()
                    async with asyncio.timeout(self.timeout):
                        response = await client.post(self.endpoint + "/api/chat", json=payload)
                    if response.status_code != 200:
                        raise AgentError("Local LLM unavailable or overloaded. Retry explicitly or select demo mode.")
                    if len(response.content) > 64000:
                        raise AgentError("Local LLM response exceeded the allowed size.")
                    body = response.json()
                    observation = {"model": self.model, "phase": phase,
                                   "elapsed_seconds": round(perf_counter() - phase_started, 3),
                                   "outcome": "invalid_response"}
                    for key in ("total_duration", "load_duration", "prompt_eval_count", "eval_count"):
                        if type(body.get(key)) is int and body[key] >= 0:
                            observation[key] = body[key]
                    self.observations.append(observation)
                    turn = parse_ollama(body)
                    observation.update(outcome="ok", generated_calls=[{"call_id": c.call_id, "name": c.name} for c in turn.calls])
                    return turn
        except (TimeoutError, httpx.TimeoutException):
            self.observations.append({"model": self.model, "phase": phase, "outcome": "timeout",
                                      "elapsed_seconds": round(perf_counter() - phase_started, 3)})
            label = "model loading" if phase == "model_load" else "generation" if phase == "generation" else "readiness check"
            raise AgentError(f"Local LLM {label} timed out. Retry explicitly; no fallback or download was attempted.") from None
        except AgentError:
            raise
        except Exception:
            raise AgentError("Local LLM unavailable, timed out, or returned invalid data. No fallback or download was attempted.") from None
