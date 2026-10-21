"""Real SDK transport with bounded, safe read retries and result validation."""

import asyncio
import json
from datetime import date
from typing import Any
from urllib.parse import urlsplit

import httpx
from jsonschema import Draft202012Validator
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult
from pydantic import ValidationError

from backend.agent.models import AgentError, FindResult, PurchaseResult, WarrantyResult, redact

ALLOWED_TOOLS = frozenset({"find_appliance", "get_purchase_evidence", "evaluate_warranty"})


def contained_agent_error(error: BaseException) -> AgentError | None:
    """SDK task groups may wrap our own already-sanitized validation errors."""
    if isinstance(error, AgentError):
        return error
    if isinstance(error, BaseExceptionGroup):
        for child in error.exceptions:
            found = contained_agent_error(child)
            if found is not None:
                return found
    return None


def parse_result(result: CallToolResult) -> dict[str, Any]:
    if result.isError:
        raise AgentError("MCP tool reported an error; no result was accepted as evidence.")
    try:
        if result.structuredContent is not None:
            value = result.structuredContent
        else:
            blocks = [block.text for block in result.content if block.type == "text"]
            if len(blocks) != 1:
                raise ValueError
            value = json.loads(blocks[0])
        if not isinstance(value, dict) or len(json.dumps(value)) > 64000:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise AgentError("Malformed MCP content; evidence was not accepted.") from None


def validate_result(name: str, value: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(redact(json.dumps(value)))
        model = {"find_appliance": FindResult, "get_purchase_evidence": PurchaseResult,
                 "evaluate_warranty": WarrantyResult}[name].model_validate(value)
        clean = model.model_dump()
        if name == "find_appliance":
            if clean["count"] != len(clean["matches"]) or len({item["id"] for item in clean["matches"]}) != clean["count"]:
                raise ValueError
        else:
            if clean["appliance_id"] != arguments["appliance_id"]:
                raise ValueError
            if name == "evaluate_warranty":
                if date.fromisoformat(clean["evaluation_date"]).isoformat() != clean["evaluation_date"]:
                    raise ValueError
                if arguments.get("evaluation_date") and clean["evaluation_date"] != arguments["evaluation_date"]:
                    raise ValueError
                if clean["status"] != "unknown" and (not clean["source_refs"] or not clean["period_start"] or not clean["period_end"]):
                    raise ValueError
                for field in ("period_start", "period_end"):
                    if clean[field] is not None:
                        if date.fromisoformat(clean[field]).isoformat() != clean[field]:
                            raise ValueError
                if clean["period_start"] and clean["period_end"]:
                    start, end = date.fromisoformat(clean["period_start"]), date.fromisoformat(clean["period_end"])
                    evaluated = date.fromisoformat(clean["evaluation_date"])
                    if end < start:
                        raise ValueError
                    if clean["status"] == "active" and not start <= evaluated <= end:
                        raise ValueError
                    if clean["status"] == "expired" and evaluated <= end:
                        raise ValueError
            else:
                if clean["evidence_status"] == "verified_demo" and (not clean["source_refs"] or not clean["purchase_date"] or not clean["receipt_id"]):
                    raise ValueError
                for recorded in (clean["purchase_date"], clean["warranty_evidence"]["start_date"], clean["warranty_evidence"]["end_date"]):
                    if recorded is not None and date.fromisoformat(recorded).isoformat() != recorded:
                        raise ValueError
        return clean
    except (ValidationError, ValueError, KeyError, TypeError):
        raise AgentError("MCP result failed validation; no factual conclusion was made.") from None


class MCPClient:
    def __init__(self, url: str = "http://127.0.0.1:8000/mcp", *, timeout: float = 8, retries: int = 1) -> None:
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != "/mcp"):
            raise AgentError("Stage 3 MCP endpoint must be a local HTTP /mcp endpoint without credentials.")
        if not 0 < timeout <= 30 or retries not in (0, 1, 2):
            raise AgentError("Invalid MCP timeout or retry bound.")
        self.url, self.timeout, self.retries = url, timeout, retries
        self.protocol: str | None = None
        self.schemas: dict[str, dict[str, Any]] = {}

    async def _request(self, name: str | None = None, arguments: dict[str, Any] | None = None) -> Any:
        for attempt in range(self.retries + 1):
            try:
                async with asyncio.timeout(self.timeout):
                    async with httpx.AsyncClient(timeout=self.timeout, trust_env=False, follow_redirects=False) as http:
                        async with streamable_http_client(self.url, http_client=http) as (read, write, _):
                            async with ClientSession(read, write) as session:
                                initialized = await session.initialize()
                                if date.fromisoformat(initialized.protocolVersion) < date(2025, 11, 25):
                                    raise AgentError("MCP negotiated a protocol older than 2025-11-25.")
                                self.protocol = initialized.protocolVersion
                                listed = (await session.list_tools()).tools
                                schemas = {}
                                for tool in listed:
                                    if tool.name in ALLOWED_TOOLS and tool.annotations and tool.annotations.readOnlyHint is True:
                                        schema = dict(tool.inputSchema)
                                        schema["additionalProperties"] = False
                                        Draft202012Validator.check_schema(schema)
                                        schemas[tool.name] = {"name": tool.name, "description": tool.description or "Read-only appliance tool",
                                                              "input_schema": schema}
                                if set(schemas) != ALLOWED_TOOLS:
                                    raise AgentError("Required read-only MCP tools were not discovered.")
                                self.schemas = schemas
                                if name is None:
                                    return list(schemas.values())
                                self.validate_call(name, arguments or {})
                                return validate_result(name, parse_result(await session.call_tool(name, arguments or {})), arguments or {})
            except AgentError:
                raise
            except Exception as exc:
                # SDK task-group exception messages may contain URLs or peer text. Never expose them.
                safe_error = contained_agent_error(exc)
                if safe_error is not None:
                    raise AgentError(str(safe_error)) from None
                if attempt == self.retries:
                    raise AgentError("MCP unavailable, disconnected, timed out, or invalid protocol response. Start the local server and retry.") from None
                await asyncio.sleep(0.1 * (attempt + 1))

    async def discover(self) -> list[dict[str, Any]]:
        return await self._request()

    def validate_call(self, name: str, arguments: dict[str, Any]) -> None:
        if name not in ALLOWED_TOOLS or name not in self.schemas:
            raise AgentError("Model requested an unavailable or forbidden tool.")
        if not isinstance(arguments, dict) or not Draft202012Validator(self.schemas[name]["input_schema"]).is_valid(arguments):
            raise AgentError("Model supplied malformed tool arguments.")

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.validate_call(name, arguments)
        return await self._request(name, arguments)
