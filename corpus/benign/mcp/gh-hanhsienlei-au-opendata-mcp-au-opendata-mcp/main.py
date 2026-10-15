import argparse
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from au_opendata_mcp.api import STATUS_FOR, router, tools_router
from au_opendata_mcp.deps import close_services
from au_opendata_mcp.errors import AuOpenDataError
from au_opendata_mcp.mcp_server import mcp
from au_opendata_mcp.observability import RequestLoggingMiddleware, configure_logging

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    # FastMCP's HTTP app owns a session-manager lifespan. If it is not propagated to the
    # parent app, REST keeps working and every /mcp request fails with
    # "Task group is not initialized". See tests/test_app_assembly.py.
    mcp_app = mcp.http_app(path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with mcp_app.lifespan(app):
            yield
        await close_services()
        # Not the `finally` in cli(): uvicorn's Server.capture_signals restores the
        # default SIGTERM/SIGINT disposition and re-raises the signal once serve()
        # returns, so the process is killed at the OS level before cli() ever regains
        # control -- code after uvicorn.run() never runs on a signal-driven shutdown.
        # The ASGI shutdown phase (here) runs before that re-raise, so it is the only
        # place a shutdown record for the HTTP transport is reliably emitted.
        log.info("au-opendata-mcp stopped", extra={"event": "shutdown"})

    app = FastAPI(
        title="au-opendata-mcp",
        description="Australian government open data over MCP and REST.",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(AuOpenDataError)
    async def domain_error(_: Request, exc: AuOpenDataError) -> JSONResponse:
        status = STATUS_FOR.get(type(exc), 500)
        return JSONResponse(
            status_code=status,
            content={"detail": exc.message, "remedy_url": exc.remedy_url},
        )

    @app.exception_handler(ValueError)
    async def bad_argument(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    # Added inside create_app() so TestClient exercises it too -- this is the only
    # request log the server emits (uvicorn's own access log is disabled in cli()).
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(router)
    app.include_router(tools_router)
    app.mount("/mcp", mcp_app)
    return app


def cli() -> None:
    parser = argparse.ArgumentParser(prog="au-opendata-mcp")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    configure_logging("INFO")
    log.info(
        "starting au-opendata-mcp",
        extra={
            "event": "startup",
            "transport": args.transport,
            "host": args.host,
            "port": args.port,
        },
    )
    if args.transport == "stdio":
        # mcp.run() installs no signal handling of its own, so a normal return (stdin
        # closed) or a propagating exception both reach this finally -- unlike the
        # http branch below, see create_app()'s lifespan for why that one is different.
        try:
            mcp.run(transport="stdio")
        finally:
            log.info("au-opendata-mcp stopped", extra={"event": "shutdown"})
    else:
        import uvicorn

        # access_log=False, not a log_config tweak: uvicorn.access is created with
        # propagate=False and its own handler, so configure_logging cannot reach it, and
        # what it writes is the raw request line -- query string and path parameters
        # included. RequestLoggingMiddleware (installed in create_app) replaces it with a
        # record that names the route template instead.
        uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    cli()
