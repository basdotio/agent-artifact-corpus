"""FastAPI serving layer for the MCP agent toolkit."""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agent import build_agent, run_ask
from .config import Settings
from .llm import get_llm
from .mcp_client import MCPToolClient
from .server import create_server
from .tracing import init_tracing

log = logging.getLogger(__name__)

settings = Settings.load()
init_tracing(settings)

if settings.mcp_server_url:
    _tool_client = MCPToolClient(url=settings.mcp_server_url,
                                 allowed_tools=settings.allowed_tools)
else:
    _tool_client = MCPToolClient(server=create_server(settings.data_dir),
                                 allowed_tools=settings.allowed_tools)

_agent = build_agent(get_llm(settings), _tool_client)

app = FastAPI(title="MCP Agent Toolkit", version="0.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    tools_used: list[str]
    steps: int
    latency_ms: float


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mock_mode": settings.mock_mode,
            "allowed_tools": list(settings.allowed_tools)}


@app.get("/tools")
async def list_tools() -> dict:
    try:
        tools = await _tool_client.list_tools()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="tool discovery failed") from exc
    return {"tools": tools}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    started = time.perf_counter()
    try:
        result = await run_ask(_agent, req.question)
    except Exception as exc:
        log.exception("ask failed")
        raise HTTPException(status_code=500, detail="internal error") from exc
    answer = (result.get("answer") or "").strip()
    if not answer:
        raise HTTPException(status_code=502, detail="empty answer from agent")
    latency_ms = (time.perf_counter() - started) * 1000
    return AskResponse(
        answer=answer[:4000],
        tools_used=result.get("tools_used", []),
        steps=result.get("steps", 0),
        latency_ms=round(latency_ms, 2),
    )
