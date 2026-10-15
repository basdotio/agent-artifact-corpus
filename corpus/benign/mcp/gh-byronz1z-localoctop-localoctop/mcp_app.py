"""The /mcp/localoctop/ streamable_http MCP endpoint consumed by Octop's
"custom MCP connector" (transport=streamable_http, Bearer auth).

Built on the official MCP SDK: a lowlevel `mcp.server.Server` served through
`StreamableHTTPSessionManager` (stateful mode, json_response=True so POSTs
answer application/json — the streamable-HTTP spec explicitly allows JSON
instead of an SSE stream, and the Octop connector probe parses it). The SDK
owns the protocol layer: initialize negotiation, the Mcp-Session-Id response
header and per-session validation (unknown/expired ids answer 404), GET
server->client SSE streams, and DELETE session termination.

What this module still owns (unchanged from the hand-rolled version):
  * Bearer auth on every request — the mcp_token maps to the user whose
    bridge session will serve the call. The authenticated user id is stashed
    on the ASGI scope so the SDK request handlers can route tools/call to
    the right bridge ("每用户只能触达自己注册的客户端会话").
  * Session ownership: the SDK additionally binds each MCP session to the
    credential that created it (`scope["user"]`), so a session id can never
    be used with a different token — defense in depth on top of the
    bridge-session keying.
  * The audit trail, kill-switch, and write gating live in ToolService.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from typing import Any

import mcp.types as mcp_types
from fastapi import APIRouter
from mcp.server import Server
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.shared.exceptions import MCPError
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from .audit import AuditLog
from .config import Settings
from .errors import BridgeProtocolError, CODE_AUTH_FAILED
from .protocol import SERVER_NAME, SERVER_VERSION, jsonrpc_error, tools_list
from .sessions import SessionRegistry
from .tools import ToolService

logger = logging.getLogger("localoctop.mcp")

# Scope key under which the authenticated user id travels to the SDK handlers.
SCOPE_USER_KEY = "localoctop_user"
# v0.6.1: scope key for the strict pair id the mcp token belongs to —
# tools/call routes ONLY to the bridge session registered with this pair.
SCOPE_PAIR_KEY = "localoctop_pair"

SERVER_INSTRUCTIONS = (
    "This connector lets you work with files inside the folders the user has "
    "allowed on their own computer. The user's originals stay on their machine; "
    "you work on copies in the cloud and send finished files back.\n"
    "1. Start by looking around: list_allowed_directories, then list_directory, "
    "search_files or get_file_info to find what you need. fetch_to_cloud also "
    "takes a whole folder.\n"
    "2. Read directly only what is directly readable: plain text via read_file "
    "(at most 100 lines / ~48 KB per call; text over 10 MB shows only its "
    "beginning). PDF, Office documents, images, archives, audio/video, non-UTF-8 "
    "text, text over 10 MB, or any file you need whole: call fetch_to_cloud to "
    "copy it to the cloud machine, then process it there with your own file and "
    "command-line tools.\n"
    "3. Send finished files back with deliver_to_local. Unless the user "
    "explicitly asked to replace an original, do NOT set overwrite=true: by "
    "default the file is saved under a new name and you are told the name.\n"
    "4. Long transfers: when the answer says IN PROGRESS, call transfer_status "
    "with the same transfer_id until DONE or FAILED. If the user asks meanwhile, "
    "say honestly that the transfer is still running.\n"
    "5. Every delete, overwrite or modification on the user's machine goes to "
    "the recycle bin first; there is no permanent delete.\n"
    "6. On an error, follow the next step given in the error text. If the same "
    "call fails twice, stop and explain the cause to the user in one or two "
    "plain sentences — do not keep retrying."
)


def to_call_tool_result(result: dict[str, Any]) -> mcp_types.CallToolResult:
    """Render a ToolService result dict ({"content": [...], "isError": b})
    into the SDK's CallToolResult model."""
    content: list[mcp_types.TextContent | mcp_types.EmbeddedResource] = []
    for block in result.get("content", []):
        btype = block.get("type")
        if btype == "text":
            content.append(mcp_types.TextContent(text=str(block.get("text", ""))))
        elif btype == "resource":
            res = block.get("resource", {})
            uri = str(res.get("uri", "")) or "file:///blob"
            mime = res.get("mimeType") or "application/octet-stream"
            if "blob" in res:
                rc: mcp_types.TextResourceContents | mcp_types.BlobResourceContents = (
                    mcp_types.BlobResourceContents(uri=uri, mimeType=mime, blob=str(res["blob"]))
                )
            else:
                rc = mcp_types.TextResourceContents(uri=uri, mimeType=mime, text=str(res.get("text", "")))
            content.append(mcp_types.EmbeddedResource(resource=rc))
        else:  # defensive: unknown block types are relayed as text
            content.append(mcp_types.TextContent(text=str(block)))
    return mcp_types.CallToolResult(content=content, isError=bool(result.get("isError", False)))


class MCPEndpoint:
    """Implements the MCP streamable-HTTP surface for one deployment.

    The instance is itself the ASGI app mounted at the MCP paths: it runs the
    Bearer check, then hands the request to the SDK session manager.
    """

    def __init__(self, settings: Settings, registry: SessionRegistry, audit: AuditLog):
        self.settings = settings
        self.registry = registry
        self.audit = audit
        self.tools = ToolService(settings, registry, audit)

        server = Server(
            SERVER_NAME,
            version=SERVER_VERSION,
            instructions=SERVER_INSTRUCTIONS,
            on_list_tools=self._on_list_tools,
            on_call_tool=self._on_call_tool,
        )
        # json_response=True: POSTs answer application/json (what the Octop
        # connector probe parses) instead of an SSE stream per request.
        self.manager = StreamableHTTPSessionManager(app=server, json_response=True, stateless=False)
        self._manager_task: asyncio.Task | None = None
        self._manager_started = asyncio.Event()
        self._manager_lock = asyncio.Lock()
        self._stop = asyncio.Event()

    # ------------------------------------------------------------- lifecycle
    async def _ensure_manager(self) -> None:
        """Start the SDK session manager on first use, idempotently.

        Lazy (rather than lifespan-bound) startup keeps the endpoint usable
        from tests that drive the app through httpx.ASGITransport, which
        never emits ASGI lifespan events.
        """
        if self._manager_task is not None:
            await self._manager_started.wait()
            return
        async with self._manager_lock:
            if self._manager_task is None:
                self._manager_task = asyncio.get_running_loop().create_task(self._run_manager())
        await self._manager_started.wait()

    async def _run_manager(self) -> None:
        async with self.manager.run():
            self._manager_started.set()
            await self._stop.wait()

    async def shutdown(self) -> None:
        """Stop the session manager (called from the app lifespan)."""
        if self._manager_task is None:
            return
        self._stop.set()
        try:
            await asyncio.wait_for(self._manager_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._manager_task.cancel()

    # ------------------------------------------------------------------ auth
    @staticmethod
    def _bearer_from_scope(scope: Scope) -> str | None:
        for key, value in scope.get("headers", []):
            if key.lower() == b"authorization":
                raw = value.decode("latin-1")
                if raw.lower().startswith("bearer "):
                    return raw[7:].strip()
        return None

    @staticmethod
    def _user_from_ctx(ctx: Any) -> str:
        """Recover the authenticated user id inside SDK request handlers.

        The ASGI entry below stashes it on the scope before the SDK sees the
        request; the SDK carries the request through to the handler context.
        """
        request = getattr(ctx, "request", None)
        user = request.scope.get(SCOPE_USER_KEY) if request is not None else None
        if not user:
            # Unreachable in practice: every request is authenticated before
            # it reaches the transport.
            raise MCPError(code=CODE_AUTH_FAILED, message="missing bearer token")
        return user

    @staticmethod
    def _pair_from_ctx(ctx: Any) -> str:
        """Recover the authenticated pair id inside SDK request handlers
        (stashed alongside the user id by the ASGI entry)."""
        request = getattr(ctx, "request", None)
        return request.scope.get(SCOPE_PAIR_KEY) if request is not None else ""

    # ------------------------------------------------------------ ASGI entry
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover - mounted on http only
            return

        token = self._bearer_from_scope(scope)
        try:
            # MCP direction only: a bridge_token (client WSS) never passes
            # the connector Bearer check. v0.6.1: the token also resolves to
            # its strict pair — unpaired mcp tokens are rejected here with
            # CODE_MCP_UNPAIRED (they have no routing target).
            user_id, pair_id = self.settings.pair_route_mcp(token)
        except BridgeProtocolError as exc:
            # Same wire shape as before the SDK swap: JSON-RPC error body with
            # our domain code, HTTP 401.
            response = JSONResponse(
                jsonrpc_error(None, exc.code, exc.message),
                status_code=401,
                headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
            return

        # Hand the identity to the SDK: handlers read it off the scope, and
        # the session manager binds each new session to this credential so a
        # session can never be used with a different token.
        scope[SCOPE_USER_KEY] = user_id
        scope[SCOPE_PAIR_KEY] = pair_id
        scope["user"] = AuthenticatedUser(
            AccessToken(token=token or "", client_id=f"localoctop:{user_id}", scopes=[])
        )

        await self._ensure_manager()
        await self.manager.handle_request(scope, receive, send)

    # ---------------------------------------------------------- SDK handlers
    async def _on_list_tools(self, ctx: Any, params: Any) -> mcp_types.ListToolsResult:
        self._user_from_ctx(ctx)  # authz: only authenticated users list tools
        write_enabled = self.settings.allow_write or bool(self.settings.write_allowlist)
        return mcp_types.ListToolsResult(
            tools=[
                mcp_types.Tool(
                    name=schema["name"],
                    description=schema["description"],
                    inputSchema=dict(schema["inputSchema"]),
                    annotations=(mcp_types.ToolAnnotations(**schema["annotations"])
                                 if "annotations" in schema else None),
                )
                for schema in tools_list(write_enabled)
            ]
        )

    async def _on_call_tool(self, ctx: Any, params: Any) -> mcp_types.CallToolResult:
        user_id = self._user_from_ctx(ctx)
        pair_id = self._pair_from_ctx(ctx)
        arguments = params.arguments if isinstance(params.arguments, dict) else {}
        try:
            result = await self.tools.call_tool(user_id, pair_id, params.name, arguments)
            return to_call_tool_result(result)
        except BridgeProtocolError as exc:
            # Routing/protocol failures ride in the JSON-RPC error object with
            # our domain codes (the connector probe parses them). Tool-level
            # failures (denied path, timeout, ...) come back as isError
            # results instead, per the MCP spec.
            raise MCPError(code=exc.code, message=exc.message) from exc
        except Exception:
            # Last-resort net for anything between the call coming in and the
            # result going out that the tool layer did not turn into a normal
            # or isError result (a bug, an unexpected type, a malformed
            # result block, ...). The model must NEVER receive a raw
            # exception string it cannot act on: answer a normal tool result
            # (isError=true) that says what happened, carries a reference id
            # for the logs, and names the next step. asyncio.CancelledError
            # is BaseException and is NOT caught here — cancellation travels
            # up untouched.
            ref = secrets.token_hex(4)
            logger.error("internal error while handling tool %r for user %r (ref %s)",
                         params.name, user_id, ref, exc_info=True)
            return mcp_types.CallToolResult(
                content=[mcp_types.TextContent(text=(
                    f"The localoctop service hit an internal problem while handling "
                    f"{params.name}. Nothing may have been done. "
                    f"Reference for the administrator: {ref}. "
                    f"You can try the exact same call once more; if it fails again, "
                    f"tell the user the localoctop service has an internal problem "
                    f"and give them the reference {ref} — do not keep retrying."
                ))],
                isError=True,
            )


def build_router(settings: Settings, registry: SessionRegistry, audit: AuditLog, mcp_path: str) -> APIRouter:
    """Mount the MCP endpoint at mcp_path (must end with '/'; both the bare
    and trailing-slash forms are registered so connector probes that forget
    the slash still work)."""
    endpoint = MCPEndpoint(settings, registry, audit)
    r = APIRouter()
    paths = {mcp_path}
    if mcp_path.endswith("/"):
        paths.add(mcp_path[:-1])
    else:
        paths.add(mcp_path + "/")

    for p in sorted(paths):
        # The endpoint instance is a raw ASGI callable (scope/receive/send),
        # which starlette's Route detects and mounts without request/response
        # wrapping — required so the SDK can own the HTTP exchange.
        r.add_route(p, endpoint, methods=["POST", "GET", "DELETE"])
    r.localoctop_endpoint = endpoint  # type: ignore[attr-defined]  # lifespan shutdown hook
    return r
