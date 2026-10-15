"""Model-independent authorization, validation, budgets and retry policy."""
import asyncio
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .server import ALLOWED_TOOLS
from .telemetry import window
from .state import State


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    service: Literal["checkout-api", "recommendations-worker"]
    start: str
    end: str
    limit: int = Field(default=50, ge=1, le=100)


class Gateway:
    def __init__(self, client, state: State, timeout: float = 5, attempts: int = 2, max_calls: int = 24):
        self.client, self.state = client, state
        self.timeout, self.max_attempts, self.max_calls = timeout, attempts, max_calls

    async def call(self, name: str, arguments: dict) -> dict:
        # This immutable allowlist runs BEFORE any MCP dispatch or model-supplied argument handling.
        if name not in ALLOWED_TOOLS:
            self.state.event("permission_denied", tool=name)
            return {"error": {"code": "PERMISSION_DENIED", "retryable": False}}
        try:
            query = Query.model_validate(arguments)
            window(query.start, query.end)
        except (ValueError, TypeError):
            self.state.event("invalid_arguments", tool=name)
            return {"error": {"code": "INVALID_ARGUMENTS", "retryable": False}}
        args = query.model_dump()
        key = hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()
        data = self.state.data
        if key in data["cache"]:
            self.state.event("cache_hit", tool=name)
            return data["cache"][key]
        while data["attempts"].get(key, 0) < self.max_attempts:
            if data["tool_calls"] >= self.max_calls:
                raise RuntimeError("Tool call budget exhausted; progress saved")
            attempt = data["attempts"].get(key, 0) + 1
            data["attempts"][key] = attempt
            data["tool_calls"] += 1
            self.state.event("tool_start", tool=name, attempt=attempt, arguments=args)
            retryable = False
            try:
                result = await asyncio.wait_for(self.client.call_tool(name, args), timeout=self.timeout)
                payload = result.data
                if not isinstance(payload, dict):
                    raise ValueError("Invalid tool response")
                if "error" in payload:
                    # Only the fixed server's structured transient code grants a retry.
                    retryable = payload["error"].get("code") == "TEMPORARY_UNAVAILABLE"
                    if retryable:
                        data["failure_consumed"] = True
                    code = payload["error"].get("code", "TOOL_ERROR")
                else:
                    for record in payload["records"]:
                        data["evidence"][record["id"]] = record
                    data["cache"][key] = payload
                    self.state.event("tool_success", tool=name, attempt=attempt, records=len(payload["records"]))
                    return payload
            except TimeoutError:
                code, retryable = "TIMEOUT", True
            except Exception:
                # Do not leak exception strings or retry validation/programming errors.
                code = "TOOL_ERROR"
            self.state.event("tool_error", tool=name, attempt=attempt, code=code, retryable=retryable)
            if not retryable:
                payload = {"error": {"code": code, "retryable": False}}
                data["cache"][key] = payload
                self.state.save()
                return payload
            if attempt < self.max_attempts:
                await asyncio.sleep(0.1 * attempt)
        self.state.event("retry_exhausted", tool=name)
        return {"error": {"code": "RETRY_EXHAUSTED", "retryable": False}}
