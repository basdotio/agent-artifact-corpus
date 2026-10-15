"""uvicorn entrypoint.

    python -m localoctop.main

All configuration comes from environment variables — see config.py and the
README for the full list.

Listeners (single process, one shared app → one SessionRegistry and one MCP
session manager):

  * plain HTTP on LOCALOCTOP_HOST:LOCALOCTOP_PORT — always on; the Octop
    container reaches it over the Docker network.
  * HTTPS/WSS on LOCALOCTOP_HOST:LOCALOCTOP_SSL_PORT — enabled when
    LOCALOCTOP_SSL_PORT is set together with LOCALOCTOP_SSL_CERTFILE and
    LOCALOCTOP_SSL_KEYFILE; employee bridges dial in over wss:// through the
    public port without a reverse proxy. TLS is terminated here with the
    same Let's Encrypt certificate Octop uses.

Exactly one uvicorn server drives the ASGI lifespan (the plain listener);
the TLS server runs with lifespan="off" against the same app instance, so
the MCP SDK session manager starts and shuts down precisely once.

Shutdown ordering (why SignalNotifyingServer exists): on SIGTERM/SIGINT
uvicorn first closes its listeners, then waits for in-flight requests to
finish, and only THEN runs the ASGI lifespan shutdown. A tool call waiting
on a transfer would otherwise sit in its wait through that whole window and
get cut off without an answer. SignalNotifyingServer sets the transfer
manager's shutdown_event the moment the signal arrives, so every waiting
call wakes up immediately and replies ("the service is restarting, poll
transfer_status") while uvicorn is still draining the connection.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import uvicorn

from .app import create_app
from .config import load_settings

logger = logging.getLogger("localoctop")


class SignalNotifyingServer(uvicorn.Server):
    """A uvicorn.Server that flags shutdown to the transfer manager the
    moment a termination signal arrives — before uvicorn starts draining
    in-flight requests and long before the ASGI lifespan shutdown runs.
    handle_exit is invoked exactly once per process lifetime (the signal
    handler guards with should_exit), so the flag is set exactly once."""

    def handle_exit(self, sig, frame):  # type: ignore[no-untyped-def]
        try:
            transfers = getattr(self.config.app.state, "transfers", None)
            if transfers is not None and not transfers.shutdown_event.is_set():
                transfers.shutdown_event.set()
                logger.info("shutdown signal %s received: waking the tool calls "
                            "waiting on transfers so they answer before the "
                            "connections close", sig)
        except Exception:  # noqa: BLE001 - never break signal handling
            pass
        super().handle_exit(sig, frame)


def _build_server(app, settings, *, host: str, port: int, tls: bool, drive_lifespan: bool) -> uvicorn.Server:
    kwargs: dict = {
        "host": host,
        "port": port,
        "log_level": settings.log_level.lower(),
        # WebSocket ping/pong keepalive at the uvicorn layer complements the
        # client's own pings and the idle-timeout sweep.
        "ws_ping_interval": 20,
        "ws_ping_timeout": 20,
        # v0.5.0: bridge media/zip responses arrive as one WS frame (30 MB
        # raw -> ~40 MB base64 + JSON). The 16 MB websockets default would
        # close 1009; 50 MiB matches the client's 48 MiB frame ceiling.
        "ws_max_size": 50 * 1024 * 1024,
        "lifespan": "auto" if drive_lifespan else "off",
    }
    if tls:
        kwargs["ssl_certfile"] = settings.ssl_certfile
        kwargs["ssl_keyfile"] = settings.ssl_keyfile
    return SignalNotifyingServer(uvicorn.Config(app, **kwargs))


async def run() -> None:
    settings = load_settings()
    app = create_app(settings)

    tls_enabled = bool(settings.ssl_port and settings.ssl_certfile and settings.ssl_keyfile)
    if settings.ssl_port and not tls_enabled:
        # Misconfiguration guard: an SSL port without a cert would silently
        # serve plaintext on the public listener — refuse instead.
        logger.error(
            "LOCALOCTOP_SSL_PORT is set but LOCALOCTOP_SSL_CERTFILE/LOCALOCTOP_SSL_KEYFILE are missing; "
            "refusing to start (public listener must not run plaintext)")
        sys.exit(1)

    servers = [_build_server(app, settings, host=settings.host, port=settings.port,
                             tls=False, drive_lifespan=True)]
    if tls_enabled:
        servers.append(_build_server(app, settings, host=settings.host, port=settings.ssl_port,
                                     tls=True, drive_lifespan=False))

    logger.info("listeners: plain=%s:%d tls=%s", settings.host, settings.port,
                f"{settings.host}:{settings.ssl_port}" if tls_enabled else "off")
    await asyncio.gather(*(s.serve() for s in servers))


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
