"""The /mcp/localoctop/ws endpoint that employee bridges dial into.

Flow:
  1. Accept the WebSocket; extract the token from ?token= or the
     Authorization: Bearer header and resolve it to a user_id.
  2. Wait for the client's register frame ({"type":"register",...}).
  3. Register the session (replacing any stale one for the same user).
  4. Read loop: route responses to pending callers; answer pings; watch for
     idle timeout.
  5. On disconnect: unregister, failing any in-flight calls.

Auth failures close the socket with policy-violation status 4401/4403
rather than an HTTP 401, because the handshake has already completed by the
time we see the register frame in some deployments; both paths are covered.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from .config import Settings
from .errors import BridgeProtocolError, CODE_AUTH_FAILED
from .sessions import BridgeSession, SessionRegistry

logger = logging.getLogger("localoctop.bridge_ws")

CLOSE_AUTH_FAILED = 4401
CLOSE_BAD_REGISTER = 4403
CLOSE_IDLE = 4408

router = APIRouter()


class BridgeWSEndpoint:
    """Bundles the WS route with its dependencies so tests can construct it
    with fakes. `build_router(settings, registry)` wires the production app."""

    def __init__(self, settings: Settings, registry: SessionRegistry):
        self.settings = settings
        self.registry = registry

    def extract_token(self, ws: WebSocket) -> str | None:
        token = ws.query_params.get("token")
        if token:
            return token
        auth = ws.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return None

    async def handle(self, ws: WebSocket) -> None:
        token = self.extract_token(ws)
        try:
            # Bridge direction only: an mcp_token (Octop connector Bearer)
            # never passes the client WSS auth. v0.6.1: also resolve the
            # strict pair this bridge token belongs to — the session records
            # it so MCP calls route by pair, not by user name. This is NOT
            # device binding: it just says "this bridge was registered by
            # that pair's bridge token".
            user_id, pair_id = self.settings.pair_route_bridge(token)
        except BridgeProtocolError as exc:
            logger.warning("ws auth failed from %s: %s", ws.client, exc.message)
            # Reject before completing the handshake when possible.
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await ws.accept()
        session: BridgeSession | None = None
        try:
            session = await self._await_register(ws, user_id)
            session.pair_id = pair_id
            await self.registry.register(session)
            await self._read_loop(ws, session)
        except WebSocketDisconnect as exc:
            logger.info("bridge disconnected: user=%s code=%s", user_id, getattr(exc, "code", "?"))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("bridge ws error: user=%s", user_id)
        finally:
            if session is not None:
                await self.registry.unregister(user_id, session)
            # Best-effort close; the socket may already be gone.
            try:
                await ws.close()
            except Exception:
                pass

    async def _await_register(self, ws: WebSocket, user_id: str) -> BridgeSession:
        """Read exactly one frame and require it to be the register frame."""
        raw = await asyncio.wait_for(ws.receive_json(), timeout=15)
        if not isinstance(raw, dict) or raw.get("type") != "register":
            logger.warning("user %s: first frame is not a register frame", user_id)
            await ws.close(code=CLOSE_BAD_REGISTER, reason="expected register frame")
            raise WebSocketDisconnect(code=CLOSE_BAD_REGISTER)

        # Defense in depth: the token in the register frame must match the
        # one that authenticated the handshake.
        reg_token = raw.get("token")
        if reg_token is not None:
            try:
                reg_user = self.settings.authenticate_bridge(reg_token)
            except BridgeProtocolError:
                reg_user = None
            if reg_user != user_id:
                logger.warning("user %s: register token mismatch", user_id)
                await ws.close(code=CLOSE_AUTH_FAILED, reason="token mismatch")
                raise WebSocketDisconnect(code=CLOSE_AUTH_FAILED)

        return BridgeSession(
            user_id=user_id,
            client_id=str(raw.get("client_id", "")) or f"anon-{int(time.time())}",
            websocket=ws,
            hostname=str(raw.get("hostname", "")),
            allowed_dirs=[str(d) for d in raw.get("allowed_dirs", []) if isinstance(d, str)][:32],
            write_enabled=bool(raw.get("write_enabled", False)),
            version=str(raw.get("version", "")),
        )

    async def _read_loop(self, ws: WebSocket, session: BridgeSession) -> None:
        idle = self.settings.idle_timeout
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_json(), timeout=idle)
            except asyncio.TimeoutError:
                logger.warning("user %s: bridge idle for %.0fs, closing", session.user_id, idle)
                await ws.close(code=CLOSE_IDLE, reason="idle timeout")
                return
            session.touch()
            if not isinstance(raw, dict):
                continue

            # Response frames carry an id we issued; route them.
            if "id" in raw and ("result" in raw or "error" in raw):
                if not self.registry.deliver(session.user_id, raw["id"], raw):
                    logger.debug("user %s: unmatched response id=%r", session.user_id, raw["id"])
                continue

            # Control frames.
            ftype = raw.get("type")
            if ftype == "ping":
                await ws.send_json({"id": raw.get("id"), "result": {"type": "pong"}})
                continue
            if ftype == "register":
                # Re-register on the same socket: update metadata in place.
                session.client_id = str(raw.get("client_id", session.client_id))
                session.allowed_dirs = [str(d) for d in raw.get("allowed_dirs", []) if isinstance(d, str)][:32]
                session.write_enabled = bool(raw.get("write_enabled", session.write_enabled))
                continue

            logger.debug("user %s: ignoring unknown frame type=%r", session.user_id, ftype)


def build_router(settings: Settings, registry: SessionRegistry, ws_path: str) -> APIRouter:
    """Return an APIRouter serving the bridge WS endpoint at ws_path."""
    endpoint = BridgeWSEndpoint(settings, registry)
    r = APIRouter()

    @r.websocket(ws_path)
    async def bridge_ws(ws: WebSocket) -> None:  # pragma: no cover - thin wrapper
        await endpoint.handle(ws)

    return r
