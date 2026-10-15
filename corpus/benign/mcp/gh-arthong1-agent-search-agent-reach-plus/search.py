"""Free Exa first; existing Tavily is selected explicitly."""
from __future__ import annotations

import json
import os
import tomllib
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from .transport import MAX_BYTES, ReachError, run_cli, validate_limit, validate_query


def check_content(content: str):
    if not content.strip():
        raise ReachError("empty_response", "Exa returned no search content")
    prefix = content[:1500].lower()
    if not any(marker in prefix for marker in ("url:", "http://", "https://")) and any(marker in prefix for marker in ("rate limit", "rate_limit", "quota exceeded", "too many requests")):
        raise ReachError("rate_limited", "Exa free usage limit reached; retry later or explicitly select Tavily")


def tavily_key() -> str:
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return key
    path = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        server = config.get("mcp_servers", {}).get("tavily", {})
        return parse_qs(urlsplit(server.get("url", "")).query).get("tavilyApiKey", [""])[0]
    except (OSError, ValueError):
        return ""


async def web_search(query: str, limit: int = 5, provider: str = "auto") -> dict:
    query = validate_query(query)
    validate_limit(limit, 10)
    if provider not in ("auto", "exa", "tavily"):
        raise ReachError("invalid_input", "provider must be auto, exa or tavily")
    if provider == "tavily":
        key = tavily_key()
        if not key:
            raise ReachError("setup_required", "Tavily key unavailable; keep using Exa or configure TAVILY_API_KEY")
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                async with client.stream("POST", "https://api.tavily.com/search", json={"api_key": key, "query": query, "max_results": limit, "search_depth": "basic", "include_answer": False}) as response:
                    if response.status_code == 429:
                        raise ReachError("rate_limited", "Tavily usage limit reached")
                    response.raise_for_status()
                    data, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ReachError("output_too_large", "Tavily response exceeds 2 MB")
                        data.append(chunk)
                    payload = json.loads(b"".join(data))
            except httpx.HTTPError as e:
                raise ReachError("search_failed", "Tavily request failed; check key or usage quota") from e
        return {"backend": "Tavily (existing account quota)", "data": payload}
    out = await run_cli("mcporter", ["call", "--http-url", "https://mcp.exa.ai/mcp", "--name", "exa-search-" + uuid.uuid4().hex[:8], "--tool", "web_search_exa", "--args", json.dumps({"query": query, "numResults": limit, "objective": "Find relevant public sources with factual excerpts and source URLs for the user's query."}, ensure_ascii=False), "--no-oauth", "--output", "json", "--timeout", "35000"], timeout=40)
    try:
        payload = json.loads(out)
    except ValueError as e:
        raise ReachError("invalid_response", "Exa returned malformed MCP output") from e
    if payload.get("isError"):
        raise ReachError("search_failed", "Exa returned a tool error; retry later or explicitly select existing Tavily")
    content = "\n".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
    check_content(content)
    return {"backend": "Exa", "data": {"content": content}}


async def code_search(query: str, tokens: int = 3000) -> dict:
    query = validate_query(query)
    if type(tokens) is not int or not 1000 <= tokens <= 10000:
        raise ReachError("invalid_input", "tokens must be 1000-10000")
    output = await run_cli("mcporter", ["call", "--http-url", "https://mcp.exa.ai/mcp?tools=get_code_context_exa", "--name", "exa-code-" + uuid.uuid4().hex[:8], "--tool", "get_code_context_exa", "--args", json.dumps({"query": query, "numResults": max(1, min(8, tokens // 1000))}, ensure_ascii=False), "--no-oauth", "--output", "json", "--timeout", "35000"], timeout=40)
    payload = json.loads(output)
    if payload.get("isError"):
        raise ReachError("search_failed", "Exa code context unavailable")
    content = "\n".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
    check_content(content)
    return {"backend": "Exa code context", "data": {"content": content}}
