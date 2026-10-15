"""FastAPI application assembly.

    create_app(settings) -> FastAPI

Wires together:
    POST/GET/DELETE {mcp_path}   the MCP streamable-HTTP surface for Octop
    WS      {ws_path}            the outbound bridge endpoint for clients
    GET     /healthz             liveness/readiness (bridge counts included)
    GET     /admin/sessions      ops view of connected bridges (loopback /
                                 admin-token guarded)
    POST    /admin/tokens/reload v0.6.0 hot-reload of the env-derived tokens

A background asyncio task (started in the lifespan) re-reads the token env
vars every `token_poll_interval` seconds and reconciles them into the live
token store — see config.reload_tokens_from_env and T3-SERVER-HOTRELOAD.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import __version__
from .audit import AuditLog
from .bridge_ws import build_router as build_ws_router
from .config import Settings, load_settings
from .errors import BridgeProtocolError, CODE_AUTH_FAILED
from .mcp_app import build_router as build_mcp_router
from .sessions import SessionRegistry
from .transfers import TransferManager

logger = logging.getLogger("localoctop")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    registry = SessionRegistry(request_timeout=settings.bridge_timeout)
    audit = AuditLog(settings.audit_log_path)

    mcp_router = build_mcp_router(settings, registry, audit, settings.mcp_path)

    async def _token_poll_loop() -> None:
        """v0.6.0 热加载 poller: every interval, re-read the token env vars
        and reconcile them into the live store (no-op when unchanged).
        Docker containers pin their env at creation, so this mainly covers
        k8s / direct-process deployments; the reliable Docker path for a
        changed .env is still `docker compose up -d` (or the admin reload
        endpoint when the in-container env has already been updated)."""
        from .config import reload_tokens_from_env

        while True:
            await asyncio.sleep(settings.token_poll_interval)
            try:
                reload_tokens_from_env(settings, logger=logger)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("token poll reload failed; retrying next interval")

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI):
        # The MCP SDK session manager starts lazily on the first request (so
        # ASGI hosts that never emit lifespan events — e.g. httpx's
        # ASGITransport in tests — still work); the lifespan only owns the
        # orderly shutdown.
        poll_task: asyncio.Task | None = None
        if settings.token_poll_interval > 0:
            poll_task = asyncio.create_task(_token_poll_loop())
        app.state._token_poll_task = poll_task
        yield
        if poll_task is not None:
            poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poll_task
        await transfers.aclose()
        endpoint = getattr(mcp_router, "localoctop_endpoint", None)
        if endpoint is not None:
            await endpoint.shutdown()

    app = FastAPI(
        title="localoctop adapter",
        version=__version__,
        docs_url=None,       # no interactive docs in production
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.registry = registry
    app.state.audit = audit

    app.include_router(mcp_router)
    app.include_router(build_ws_router(settings, registry, settings.ws_path))

    # Out-of-band file transfer (experiment branch): the bridge moves file
    # bytes over these HTTP routes; MCP tools only start/observe transfers.
    transfers = TransferManager(settings, registry, settings.mcp_path.rstrip("/") + "/transfer")
    app.state.transfers = transfers
    app.include_router(transfers.build_router())
    mcp_router.localoctop_endpoint.tools.transfers = transfers  # type: ignore[attr-defined]

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        sessions = registry.snapshot()
        return {
            "status": "ok",
            "version": __version__,
            "bridges_connected": len(sessions),
            "disabled": settings.disabled,
            "write_globally_enabled": settings.allow_write,
        }

    @app.get("/admin/sessions")
    async def admin_sessions(request: Request) -> JSONResponse:
        # Guarded by an admin token when configured; otherwise loopback-only.
        admin_token = settings.static_tokens.get("__admin__") or _env_admin_token()
        auth = request.headers.get("authorization", "")
        authorized = False
        if admin_token:
            authorized = auth == f"Bearer {admin_token}"
        else:
            client = request.client
            authorized = bool(client and client.host in ("127.0.0.1", "::1", "localhost"))
        if not authorized:
            err = BridgeProtocolError(CODE_AUTH_FAILED, "admin access denied")
            return JSONResponse({"error": err.to_dict()}, status_code=403)
        return JSONResponse({"sessions": registry.snapshot(), "pairs": settings.token_store.list_pairs()})

    # ---- token management (任务书 v1.1 §七: split mcp/bridge tokens) ----

    async def _admin_guard(request: Request) -> bool:
        admin_token = settings.static_tokens.get("__admin__") or _env_admin_token()
        auth = request.headers.get("authorization", "")
        if admin_token:
            return auth == f"Bearer {admin_token}"
        client = request.client
        return bool(client and client.host in ("127.0.0.1", "::1", "localhost"))

    @app.post("/admin/tokens/issue")
    async def admin_issue_token(request: Request) -> JSONResponse:
        """Mint one token. Body: {"user_id": str, "kind": "mcp"|"bridge"|"pair"}.
        The plaintext is returned exactly once; only its SHA-256 hash is kept.
        v0.6.1: kind="pair" mints one strict pair (mcp + bridge bound 1:1) —
        the normal issuance mode; bare mcp/bridge remain for compatibility
        but produce UNPAIRED tokens that cannot route ([用户裁定] 成对签发)."""
        from .tokens import KIND_BRIDGE, KIND_MCP, KIND_PAIR

        if not await _admin_guard(request):
            err = BridgeProtocolError(CODE_AUTH_FAILED, "admin access denied")
            return JSONResponse({"error": err.to_dict()}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"code": -32602, "message": "invalid JSON body"}}, status_code=400)
        user_id = str(body.get("user_id", "")).strip()
        kind = str(body.get("kind", "")).strip().lower()
        if not user_id:
            return JSONResponse({"error": {"code": -32602, "message": "user_id is required"}}, status_code=400)
        if kind not in (KIND_MCP, KIND_BRIDGE, KIND_PAIR):
            return JSONResponse(
                {"error": {"code": -32602, "message": "kind must be 'mcp', 'bridge' or 'pair'"}}, status_code=400)
        if kind == KIND_PAIR:
            mcp_token, bridge_token = settings.token_store.issue_pair(user_id)
            return JSONResponse({
                "user_id": user_id,
                "kind": KIND_PAIR,
                # shown once; only the SHA-256 hashes are stored
                "mcp_token": mcp_token,
                "bridge_token": bridge_token,
            })
        token = settings.token_store.issue(kind, user_id)
        return JSONResponse({
            "user_id": user_id,
            "kind": kind,
            "token": token,  # shown once; only the SHA-256 hash is stored
        })

    @app.post("/admin/tokens/revoke")
    async def admin_revoke_tokens(request: Request) -> JSONResponse:
        """Revoke tokens. Body: {"user_id": str, "kind": "mcp"|"bridge"} —
        each direction is revoked independently; or {"pair_id": str} to
        revoke one strict pair on both sides at once (v0.6.1 成对吊销)."""
        from .tokens import KIND_BRIDGE, KIND_MCP

        if not await _admin_guard(request):
            err = BridgeProtocolError(CODE_AUTH_FAILED, "admin access denied")
            return JSONResponse({"error": err.to_dict()}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": {"code": -32602, "message": "invalid JSON body"}}, status_code=400)
        pair_id = str(body.get("pair_id", "")).strip()
        if pair_id:
            revoked = settings.token_store.revoke_pair(pair_id)
            return JSONResponse({"pair_id": pair_id, "revoked": revoked})
        user_id = str(body.get("user_id", "")).strip()
        kind = str(body.get("kind", "")).strip().lower()
        if not user_id or kind not in (KIND_MCP, KIND_BRIDGE):
            return JSONResponse(
                {"error": {"code": -32602, "message": "user_id and kind ('mcp'|'bridge'), or pair_id, are required"}},
                status_code=400)
        revoked = settings.token_store.revoke_user(kind, user_id)
        return JSONResponse({"user_id": user_id, "kind": kind, "revoked": revoked})

    @app.get("/admin/tokens")
    async def admin_list_tokens(request: Request, user_id: str = "") -> JSONResponse:
        """List token metadata (kind/hint/created/revoked — never plaintext),
        plus the v0.6.1 pairing table: which mcp/bridge tokens form a pair
        (pair_id), whether the pair is complete, and which pair's bridge is
        currently online (resolved against the live session registry)."""
        from .tokens import KIND_BRIDGE, KIND_MCP

        if not await _admin_guard(request):
            err = BridgeProtocolError(CODE_AUTH_FAILED, "admin access denied")
            return JSONResponse({"error": err.to_dict()}, status_code=403)
        tokens = []
        for kind in (KIND_MCP, KIND_BRIDGE):
            for rec in settings.token_store.list_user(kind, user_id):
                if not user_id or rec["user_id"] == user_id:
                    tokens.append(rec)
        online = {s["pair_id"] for s in registry.snapshot() if s.get("pair_id")}
        pairs = [
            {**p, "bridge_online": p["pair_id"] in online}
            for p in settings.token_store.list_pairs()
            if not user_id or p["user_id"] == user_id
        ]
        return JSONResponse({"tokens": tokens, "pairs": pairs})

    @app.post("/admin/tokens/reload")
    async def admin_reload_tokens(request: Request) -> JSONResponse:
        """v0.6.0 热加载: immediately re-read the token env vars and update
        the live token table. Admin-guarded like the other /admin endpoints.

        使用方式: 运维改宿主机 .env 后 `docker compose up -d` 一次性重建仍
        是最可靠路径（docker 语义下 env 在容器创建时固定，宿主机改 .env
        不会同步进运行中的容器）；本 API 用于同容器内 env 已更新的场景
        （如 k8s ConfigMap 注入、自动化脚本 `docker exec` 改 env 后调用）
        与 CI/自动化调用。

        Response (user ids only — token plaintexts never appear):
            {"reloaded": true,
             "mcp_users": [...], "bridge_users": [...],
             "added": {...}, "removed": {...}}
        """
        if not await _admin_guard(request):
            err = BridgeProtocolError(CODE_AUTH_FAILED, "admin access denied")
            return JSONResponse({"error": err.to_dict()}, status_code=403)

        from .config import reload_tokens_from_env
        from .tokens import KIND_BRIDGE, KIND_MCP

        diff = reload_tokens_from_env(settings, logger=logger)

        def _users(kind: str) -> list[str]:
            table = settings.token_store._table_locked(kind)
            return sorted({rec.user_id for rec in table.values() if not rec.revoked})

        return JSONResponse({
            "reloaded": True,
            "mcp_users": _users(KIND_MCP),
            "bridge_users": _users(KIND_BRIDGE),
            "added": diff["mcp"]["added"] + diff["bridge"]["added"],
            "removed": diff["mcp"]["removed"] + diff["bridge"]["removed"],
        })

    return app


def _env_admin_token() -> str:
    import os

    return os.environ.get("LOCALOCTOP_ADMIN_TOKEN", "")
