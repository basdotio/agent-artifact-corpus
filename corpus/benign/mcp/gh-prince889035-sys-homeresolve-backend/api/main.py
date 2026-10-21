"""Local FastAPI facade over existing agent and repair services. Run as a module."""

import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.agent.demo_provider import DemoProvider
from backend.agent.mcp_client import MCPClient
from backend.agent.models import AgentError, Conversation, redact
from backend.agent.orchestrator import Agent
from backend.agent.providers import AnthropicProvider
from backend.agent.ollama_provider import OllamaProvider
from backend.api.models import (AppInfo, ApplianceDetail, ApproveRequest, AuditEvent, ChatRequest,
                                ChatResponse, Health, Proposal, ProposalRequest, RejectRequest, RepairCase)
from backend.api.security import COOKIE, SessionLimitError, SessionStore
from backend.domain import InputError
from backend.repair_repository import DEFAULT_DB, RepairRepository
from backend.repair_service import ConflictError, RepairService

HOUSEHOLD = "Demo Hearth Household"


@dataclass(frozen=True)
class Settings:
    db_path: Path = DEFAULT_DB
    mcp_url: str = "http://127.0.0.1:8000/mcp"
    frontend_origin: str = "http://127.0.0.1:5173"
    mode: str = "demo"
    allow_paid: bool = False
    evaluation_date: str = "2026-10-17"

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(db_path=Path(os.getenv("HOMERESOLVE_WEB_DB", str(DEFAULT_DB))),
                   mcp_url=os.getenv("HOMERESOLVE_MCP_URL", cls.mcp_url),
                   frontend_origin=os.getenv("HOMERESOLVE_FRONTEND_ORIGIN", cls.frontend_origin),
                   mode=os.getenv("HOMERESOLVE_WEB_MODE", "demo"),
                   allow_paid=os.getenv("HOMERESOLVE_ALLOW_PAID_LLM") == "1")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    origin = urlsplit(settings.frontend_origin)
    if (origin.scheme != "http" or origin.hostname != "127.0.0.1" or origin.path or origin.query
            or origin.fragment or origin.username or not origin.port):
        raise ValueError("Frontend origin must be an exact loopback HTTP origin with a port")
    if settings.mode not in ("demo", "llm", "ollama"):
        raise ValueError("Invalid server-side mode")
    provider = (AnthropicProvider(allow_paid=settings.allow_paid) if settings.mode == "llm" else
                OllamaProvider() if settings.mode == "ollama" else DemoProvider())
    repairs = RepairService(RepairRepository(settings.db_path))
    sessions = SessionStore()
    app = FastAPI(title="HomeResolve local demo API", docs_url=None, redoc_url=None)
    app.state.repairs, app.state.sessions = repairs, sessions
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-CSRF-Token"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        request_origin = request.headers.get("origin")
        if request_origin is not None and request_origin != settings.frontend_origin:
            return JSONResponse({"detail": "Origin is not permitted for this local demo."}, status_code=403)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            session = sessions.get(request.cookies.get(COOKIE))
            token = request.headers.get("x-csrf-token", "")
            if (request_origin != settings.frontend_origin or session is None or not token or not token.isascii()
                    or not secrets.compare_digest(token, session.csrf)
                    or request.headers.get("sec-fetch-site") == "cross-site"):
                return JSONResponse({"detail": "Local session or CSRF check failed. Refresh the application."}, status_code=403)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"detail": "Use an application/json request."}, status_code=415)
            if len(await request.body()) > 16000:
                return JSONResponse({"detail": "Request is too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request, exc):
        return JSONResponse({"detail": "Invalid request fields. Check your input and explicit confirmation."}, status_code=422)

    @app.exception_handler(ConflictError)
    async def conflict(request, exc):
        return JSONResponse({"detail": "This proposal is already decided, or the idempotency request conflicts."}, status_code=409)

    @app.exception_handler(AgentError)
    async def agent_error(request, exc):
        return JSONResponse({"detail": redact(str(exc))}, status_code=409)

    @app.exception_handler(InputError)
    async def input_error(request, exc):
        return JSONResponse({"detail": "Record not found or invalid in the local demo household."}, status_code=404)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return JSONResponse({"detail": "Local storage is unavailable. Retry without changing your request."}, status_code=503)

    @app.exception_handler(SessionLimitError)
    async def session_capacity(request, exc):
        return JSONResponse({"detail": "Local browser session capacity reached. Reuse an open session or retry after sessions expire."},
                            status_code=503, headers={"Retry-After": "3600"})

    @app.exception_handler(Exception)
    async def unknown_error(request, exc):
        return JSONResponse({"detail": "The local service could not complete the operation."}, status_code=500)

    def browser(request: Request):
        session = sessions.get(request.cookies.get(COOKIE))
        if session is None:
            raise HTTPException(403, "Refresh the application to initialize a local session.")
        return session

    def conversation(session, identifier: str):
        state = session.conversations.get(identifier)
        if state is None:
            raise HTTPException(410, "Conversation expired or is unavailable. Start a new conversation; saved records remain.")
        return state

    def make_agent() -> Agent:
        return Agent(MCPClient(settings.mcp_url), provider, repairs, evaluation_date=settings.evaluation_date)

    def detail(identifier: str) -> ApplianceDetail:
        matches = repairs.catalog.find(identifier)["matches"]
        item = next((item for item in matches if item["id"] == identifier and item["household"] == HOUSEHOLD), None)
        if item is None:
            raise HTTPException(404, "Appliance not found.")
        return ApplianceDetail(appliance=item, purchase=repairs.catalog.evidence(identifier),
                               warranty=repairs.catalog.warranty(identifier, settings.evaluation_date))

    @app.get("/api/health", response_model=Health)
    def health():
        return Health()

    @app.get("/api/app-info", response_model=AppInfo)
    def app_info(request: Request, response: Response):
        session = sessions.get(request.cookies.get(COOKIE))
        if session is None:
            identifier, session = sessions.create()
            response.set_cookie(COOKIE, identifier, httponly=True, samesite="strict", max_age=3600, path="/api")
        return AppInfo(mode=settings.mode, mode_label="DEMO MODE — deterministic agent routing" if settings.mode == "demo"
                       else "LOCAL LLM MODE — Ollama; no deterministic fallback" if settings.mode == "ollama"
                       else "LLM MODE — Anthropic opt-in; live verification unverified", household=HOUSEHOLD,
                       evaluation_date=settings.evaluation_date, csrf_token=session.csrf)

    @app.get("/api/appliances", response_model=list[ApplianceDetail])
    def appliances():
        return [detail(item["id"]) for item in repairs.catalog.find(HOUSEHOLD)["matches"]]

    @app.get("/api/appliances/{identifier}", response_model=ApplianceDetail)
    def appliance(identifier: str):
        return detail(identifier)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, request: Request):
        session = browser(request)
        fingerprint = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
        if body.request_id in session.responses:
            prior, reply = session.responses[body.request_id]
            if prior != fingerprint:
                raise HTTPException(409, "Request ID was already used with different input.")
            return reply
        if session.lock.locked():
            raise HTTPException(409, "A conversation operation is in progress. Please wait.")
        async with session.lock:
            if body.conversation_id:
                state = conversation(session, body.conversation_id)
            else:
                state = Conversation(household_id=HOUSEHOLD)
                if len(session.conversations) >= 16:
                    session.conversations.popitem(last=False)
                session.conversations[state.conversation_id] = state
            agent = make_agent()
            try:
                reply = await asyncio.wait_for(agent.respond(state, body.message), timeout=180 if settings.mode == "ollama" else 90)
            except TimeoutError:
                raise HTTPException(504, "Agent timed out. Retry the request after checking the local MCP server.") from None
            # Adapt only the CLI-specific next-step instruction; preserve every evidence fact.
            message = reply.text.replace(
                "Next: use /prepare <issue description> to save a pending local proposal for human review.",
                "Next: use the problem description form to prepare a proposal for your review.")
            response = ChatResponse(conversation_id=state.conversation_id, status=reply.status, message=message,
                                    tools=reply.tools, local_tools=reply.local_tools, protocol=agent.client.protocol, selected=state.selected,
                                    purchase=state.evidence.get("get_purchase_evidence"),
                                    warranty=state.evidence.get("evaluate_warranty"), candidates=state.candidates, phase=state.phase)
            session.responses[body.request_id] = (fingerprint, response)
            if len(session.responses) > 32:
                session.responses.popitem(last=False)
            return response

    @app.post("/api/proposals", response_model=Proposal)
    async def prepare(body: ProposalRequest, request: Request):
        session = browser(request)
        if session.lock.locked():
            raise HTTPException(409, "A conversation operation is in progress. Please wait.")
        async with session.lock:
            state = conversation(session, body.conversation_id)
            return await make_agent().prepare_proposal(state, body.issue_description)

    @app.get("/api/proposals", response_model=list[Proposal])
    def proposals():
        return repairs.list_repair_proposals(HOUSEHOLD)

    @app.get("/api/proposals/{identifier}", response_model=Proposal)
    def proposal(identifier: str):
        return repairs.get_repair_proposal(HOUSEHOLD, identifier)

    @app.post("/api/proposals/{identifier}/approve", response_model=RepairCase)
    def approve(identifier: str, body: ApproveRequest):
        return repairs.approve_repair_proposal(HOUSEHOLD, identifier, body.decision)

    @app.post("/api/proposals/{identifier}/reject", response_model=Proposal)
    def reject(identifier: str, body: RejectRequest):
        return repairs.reject_repair_proposal(HOUSEHOLD, identifier, body.decision)

    @app.get("/api/cases", response_model=list[RepairCase])
    def cases():
        return repairs.list_repair_cases(HOUSEHOLD)

    @app.get("/api/cases/{identifier}", response_model=RepairCase)
    def case(identifier: str):
        return repairs.get_repair_case(HOUSEHOLD, identifier)

    @app.get("/api/cases/{identifier}/audit", response_model=list[AuditEvent])
    def audit(identifier: str):
        saved = repairs.get_repair_case(HOUSEHOLD, identifier)
        return repairs.get_audit_history(HOUSEHOLD, saved["proposal_id"])

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=int(os.getenv("HOMERESOLVE_API_PORT", "8001")), proxy_headers=False)
