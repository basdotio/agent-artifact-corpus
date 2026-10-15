"""GitHub owner-authenticated HTTP MCP frontend, intended behind a local TLS proxy.

Run ``python -m app.server``. Importing this module never reads private config,
opens a socket, creates keys, starts a server, or connects to GitHub.
"""
from __future__ import annotations

import asyncio
import datetime
import ipaddress
import os
from types import SimpleNamespace
from typing import Annotated
from urllib.parse import urlsplit
import uuid

from cryptography.fernet import Fernet
from fastmcp import FastMCP
from fastmcp.exceptions import AuthorizationError
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware.authorization import AuthMiddleware
from key_value.aio.stores.filetree import FileTreeStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from mcp.server.auth.provider import AuthorizeError, RegistrationError
from pydantic import Field
from starlette.responses import PlainTextResponse

from app.config import Settings, validate_private_directory
from app.cimd import TrustedCIMDClientManager, is_url_client_id
from app.health_tools import register as register_health
from app.management_tools import BrokerClient, register as register_management

MAX_HTTP_BODY = 1048576
FORWARDING_HEADERS = {b"forwarded", b"cf-connecting-ip", b"cf-visitor", b"x-real-ip", b"true-client-ip"}


def owner_check(owner_id: str):
    """Compare immutable GitHub numeric identity, never a mutable display name."""
    def check(ctx) -> bool:
        if (not isinstance(owner_id, str) or not owner_id.isascii()
                or not owner_id.isdecimal() or not owner_id or int(owner_id) <= 0):
            return False
        token = getattr(ctx, "token", None)
        if token is None:
            return False
        claims = getattr(token, "claims", None)
        subject = claims.get("sub") if isinstance(claims, dict) else None
        return type(subject) is str and subject == owner_id and "read:user" in (getattr(token, "scopes", None) or [])
    return check


class OwnerMiddleware(AuthMiddleware):
    """Retain FastMCP global authorization and close its intentional stdio bypass."""
    def __init__(self, owner_id: str):
        self.check_owner = owner_check(owner_id)
        super().__init__(auth=self.check_owner)

    def authorized(self) -> bool:
        return self.check_owner(SimpleNamespace(token=get_access_token()))

    async def on_list_tools(self, context, call_next):
        if not self.authorized():
            return []
        return await super().on_list_tools(context, call_next)

    async def on_call_tool(self, context, call_next):
        if not self.authorized():
            raise AuthorizationError("Access is restricted to the configured GitHub owner")
        return await super().on_call_tool(context, call_next)


class ExactRedirectGitHubProvider(GitHubProvider):
    """The upstream allowlist supports patterns; this server requires exact URLs.

    In FastMCP 4.0.10 its pattern matcher does not compare URL queries. Enforce
    equality at registration, authorization, and stored transaction redirects.
    CIMD is optional and resolves only operator-approved metadata and JWKS URLs.
    """
    def __init__(self, *, exact_redirect_uris: tuple[str, ...], trusted_metadata_uris: tuple[str, ...] = (),
                 trusted_jwks_uris: tuple[str, ...] = (), **kwargs):
        self.exact_redirect_uris = frozenset(exact_redirect_uris)
        self.trusted_metadata_uris = frozenset(trusted_metadata_uris)
        super().__init__(allowed_client_redirect_uris=list(exact_redirect_uris), enable_cimd=False, **kwargs)
        if trusted_metadata_uris:
            # FastMCP 4.0.10 consults this manager when creating discovery/token
            # routes, retaining its private_key_jwt authenticator unchanged.
            self._cimd_manager = TrustedCIMDClientManager(
                metadata_uris=trusted_metadata_uris, jwks_uris=trusted_jwks_uris,
                redirects=exact_redirect_uris, default_scope=self._default_scope_str,
            )

    async def get_client(self, client_id: str):
        if is_url_client_id(client_id):
            if client_id not in self.trusted_metadata_uris or self._cimd_manager is None:
                return None
            # Never accept persisted or stale CIMD records or DCR records that
            # shadow trusted URL identifiers (upstream supports a legacy fallback).
            return await self._cimd_manager.get_client(client_id)
        return await super().get_client(client_id)

    def _validate_client_redirect_uri(self, redirect_uri: str) -> bool:
        return str(redirect_uri) in self.exact_redirect_uris

    async def register_client(self, client_info) -> None:
        if client_info.client_id and is_url_client_id(client_info.client_id):
            raise RegistrationError("invalid_client_metadata", "URL identifiers must use trusted client metadata")
        if not client_info.redirect_uris or any(
                str(uri) not in self.exact_redirect_uris for uri in client_info.redirect_uris):
            raise RegistrationError("invalid_redirect_uri", "An exact configured HTTPS callback is required")
        await super().register_client(client_info)

    async def authorize(self, client, params) -> str:
        if str(params.redirect_uri) not in self.exact_redirect_uris:
            raise AuthorizeError(error="invalid_request", error_description="An exact configured HTTPS callback is required")
        return await super().authorize(client, params)


def make_storage(settings: Settings):
    validate_private_directory(settings.state_dir)
    return FernetEncryptionWrapper(
        key_value=FileTreeStore(data_directory=settings.state_dir, auto_create=True),
        fernet=Fernet(settings.encryption_key.encode("ascii")),
    )


def make_provider(settings: Settings, *, storage=None) -> ExactRedirectGitHubProvider:
    """Never use fallback signing keys or an unencrypted production token store."""
    return ExactRedirectGitHubProvider(
        exact_redirect_uris=settings.redirect_uris,
        trusted_metadata_uris=settings.trusted_client_metadata_uris,
        trusted_jwks_uris=settings.trusted_jwks_uris,
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        base_url=settings.base_url,
        redirect_path="/auth/callback",
        required_scopes=["read:user"],
        jwt_signing_key=settings.signing_key.encode("utf-8"),
        client_storage=make_storage(settings) if storage is None else storage,
        require_authorization_consent=True,
        fallback_refresh_token_expiry_seconds=86400,
        fastmcp_access_token_expiry_seconds=900,
    )


async def probe(challenge: Annotated[str, Field(strict=True, min_length=1, max_length=256)]) -> dict:
    """Echo a literal challenge with the frontend hostname, UTC time, and a nonsecret nonce."""
    return {"challenge": challenge, "hostname": os.uname().nodename,
            "utc_time": datetime.datetime.now(datetime.timezone.utc).isoformat(), "nonce": uuid.uuid4().hex}


def make_server(settings: Settings, *, provider=None, broker: BrokerClient | None = None) -> FastMCP:
    server = FastMCP("Homelab MCP", auth=make_provider(settings) if provider is None else provider,
                     middleware=[OwnerMiddleware(settings.owner_id)])
    server.tool(probe, annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
    register_health(server, settings.health_snapshot)
    if settings.enable_execution:
        register_management(server, broker if broker is not None else BrokerClient(settings.broker_socket))
    return server


class LoopbackProxyGuard:
    """Guard every HTTP route, including OAuth, before any application consumes it.

    The TLS proxy must preserve the exact configured public Host. Only a local
    peer is accepted; forwarded headers never grant trust. Request URLs use the
    configured HTTPS scheme rather than client-supplied forwarding information.
    This is not an authentication replacement: every tool also requires OAuth.
    """
    def __init__(self, app, *, base_url: str, allowed_origins: set[str] | None = None,
                 max_body: int = MAX_HTTP_BODY):
        self.app = app
        self.base_url = base_url
        self.authority = urlsplit(base_url).netloc.encode("ascii")
        self.allowed_origins = {base_url.encode("ascii")} | {origin.encode("ascii") for origin in (allowed_origins or set())}
        self.max_body = max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        if scope["type"] != "http":
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return
        peer = scope.get("client")
        try:
            local = bool(peer) and ipaddress.ip_address(peer[0]).is_loopback
        except ValueError:
            local = False
        if not local:
            return await PlainTextResponse("Loopback proxy required", status_code=403)(scope, receive, send)
        headers = [(key.lower(), value) for key, value in scope.get("headers", [])]
        hosts = [value for key, value in headers if key == b"host"]
        origins = [value for key, value in headers if key == b"origin"]
        lengths = [value for key, value in headers if key == b"content-length"]
        if len(hosts) != 1 or hosts[0] != self.authority:
            return await PlainTextResponse("Invalid Host", status_code=421)(scope, receive, send)
        if len(origins) > 1 or (origins and origins[0] not in self.allowed_origins):
            return await PlainTextResponse("Invalid Origin", status_code=403)(scope, receive, send)
        if len(lengths) > 1 or (lengths and (not lengths[0].isdigit() or len(lengths[0]) > 10)):
            return await PlainTextResponse("Invalid Content-Length", status_code=400)(scope, receive, send)
        if lengths and int(lengths[0]) > self.max_body:
            return await PlainTextResponse("Request body too large", status_code=413)(scope, receive, send)
        body = bytearray()
        try:
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    if message["type"] != "http.request":
                        continue
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > self.max_body:
                        return await PlainTextResponse("Request body too large", status_code=413)(scope, receive, send)
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await PlainTextResponse("Request body timed out", status_code=408)(scope, receive, send)
        if lengths and int(lengths[0]) != len(body):
            return await PlainTextResponse("Content-Length mismatch", status_code=400)(scope, receive, send)
        clean_scope = dict(scope)
        clean_scope["headers"] = [(key, value) for key, value in headers
                                  if key not in FORWARDING_HEADERS and not key.startswith(b"x-forwarded-")]
        clean_scope["scheme"] = "https"
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        await self.app(clean_scope, replay, send)


def make_app(settings: Settings, *, provider=None, broker=None):
    server = make_server(settings, provider=provider, broker=broker)
    origins = {settings.base_url} | {f"{urlsplit(uri).scheme}://{urlsplit(uri).netloc}" for uri in settings.redirect_uris}
    inner = server.http_app(path="/mcp", json_response=True, stateless_http=True,
                            allowed_hosts=[urlsplit(settings.base_url).netloc], allowed_origins=sorted(origins))
    return LoopbackProxyGuard(inner, base_url=settings.base_url, allowed_origins=origins)


def from_environment():
    return make_app(Settings.from_environment())


def main() -> None:
    import uvicorn
    os.umask(0o077)
    settings = Settings.from_environment()
    uvicorn.run(make_app(settings), host="127.0.0.1", port=settings.port,
                proxy_headers=False, access_log=False, log_level="warning",
                limit_concurrency=64, timeout_keep_alive=5)


if __name__ == "__main__":
    main()
