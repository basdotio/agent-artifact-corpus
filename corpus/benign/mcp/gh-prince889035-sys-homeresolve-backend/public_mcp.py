"""Optional isolated read-only MCP runtime. No API, repair storage or LLM imports."""

import asyncio
import os
import re
import time
from collections import deque
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from backend.server import READ_ONLY, evaluate_warranty, find_appliance, get_purchase_evidence


@dataclass(frozen=True)
class Settings:
    bind: str = "127.0.0.1"
    port: int = 8002
    public_host: str | None = None

    def __post_init__(self):
        if self.bind not in ("127.0.0.1", "0.0.0.0") or not 1 <= self.port <= 65535:
            raise ValueError("Invalid read-only MCP bind/port")
        if self.public_host and (len(self.public_host) > 253 or not re.fullmatch(
                r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", self.public_host)):
            raise ValueError("Public host must be an exact lowercase DNS hostname")
        if self.bind == "0.0.0.0" and not self.public_host:
            raise ValueError("External binding requires HOMERESOLVE_PUBLIC_HOST; never use the local API here")

    @classmethod
    def from_environment(cls):
        return cls(bind=os.getenv("HOMERESOLVE_MCP_BIND", "127.0.0.1"),
                   port=int(os.getenv("PORT", "8002")), public_host=os.getenv("HOMERESOLVE_PUBLIC_HOST") or None)


class RequestBudget:
    """Single-worker global budget: 120 requests/minute, 8 active, 10-second deadline.

    This bounds application work, not distributed denial of service. Use a host TLS edge.
    Forwarded IP headers are deliberately not trusted. Health probes avoid the rate bucket.
    """

    def __init__(self, app, *, requests_per_minute=120, concurrency=8, timeout=10):
        self.app, self.limit, self.concurrency, self.timeout = app, requests_per_minute, concurrency, timeout
        self.timestamps: deque[float] = deque()
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope["path"] == "/health" and scope["method"] in ("GET", "HEAD"):
            return await self.app(scope, receive, send)
        now = time.monotonic()
        while self.timestamps and now - self.timestamps[0] >= 60:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.limit:
            return await JSONResponse({"error": "Read-only demo request budget exceeded"}, 429,
                                      headers={"Retry-After": "60"})(scope, receive, send)
        if self.active >= self.concurrency:
            return await JSONResponse({"error": "Read-only demo is busy; retry later"}, 503)(scope, receive, send)
        self.timestamps.append(now)
        self.active += 1
        started = False

        async def bounded_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            async with asyncio.timeout(self.timeout):
                await self.app(scope, receive, bounded_send)
        except TimeoutError:
            if not started:
                await JSONResponse({"error": "Read-only request timed out"}, 504)(scope, receive, send)
        except Exception:
            if not started:
                await JSONResponse({"error": "Read-only service could not complete the request"}, 500)(scope, receive, send)
        finally:
            self.active -= 1


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_environment()
    hosts = ["127.0.0.1:*", "localhost:*", *([settings.public_host] if settings.public_host else [])]
    origins = ["http://127.0.0.1:*", "http://localhost:*", *([f"https://{settings.public_host}"] if settings.public_host else [])]
    server = FastMCP("HomeResolve", host=settings.bind, port=settings.port, json_response=True,
                     stateless_http=True, max_request_body_size=65536,
                     transport_security=TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins))
    for function in (find_appliance, get_purchase_evidence, evaluate_warranty):
        server.add_tool(function, annotations=READ_ONLY)

    @server.custom_route("/health", methods=["GET", "HEAD"])
    async def health(request):
        return JSONResponse({"status": "ok", "scope": "synthetic-read-only-mcp", "minimum_protocol": "2025-11-25"},
                            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    app = RequestBudget(server.streamable_http_app())
    return TrustedHostMiddleware(app, allowed_hosts=["127.0.0.1", "localhost", *([settings.public_host] if settings.public_host else [])])


def main():
    import uvicorn
    settings = Settings.from_environment()
    uvicorn.run(create_app(settings), host=settings.bind, port=settings.port, proxy_headers=False,
                limit_concurrency=16, timeout_keep_alive=5, access_log=False)


if __name__ == "__main__":
    main()
