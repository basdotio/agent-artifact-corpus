"""Command line interface using Typer.

Provides a clean entry point: `mcp-call-orchestrator-proxy run`
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

import typer

from mcp_call_orchestrator_proxy.app import create_proxy_app
from mcp_call_orchestrator_proxy.client import resolve_backend_url
from mcp_call_orchestrator_proxy.config import LogLevel, get_settings

app = typer.Typer(
    name="mcp-call-orchestrator-proxy",
    help="Resilient, serializing MCP proxy in front of a single backend MCP server.",
    no_args_is_help=True,
)


@app.callback()
def _main() -> None:
    """Resilient, serializing MCP proxy in front of a single backend MCP server.

    The callback keeps ``run`` an explicit subcommand: without it, Typer promotes
    a lone command to the top level and ``... run`` would be rejected.
    """


Transport = Literal["stdio", "streamable-http"]


def _configure_logging(level: LogLevel) -> None:
    """Install a handler so the proxy's own records actually reach the journal.

    A library never configures logging; the process entry point must, or every
    record below WARNING is discarded by the root logger's default and the queue
    runs invisibly. `level` is already validated by `ProxySettings`.
    """
    logging.basicConfig(
        level=logging.getLevelNamesMapping()[level],
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("mcp_call_orchestrator_proxy").setLevel(level)


@app.command()
def run(
    host: Annotated[str | None, typer.Option("--host", "-h")] = None,
    port: Annotated[int | None, typer.Option("--port", "-p")] = None,
    transport: Annotated[
        Transport,
        typer.Option("--transport", "-t", help="Transport to serve the proxy on."),
    ] = "streamable-http",
    backend_config: Annotated[
        str | None,
        typer.Option(
            "--backend-config",
            help="Path to a standard mcpServers JSON config file for the backend "
            "(takes precedence over the individual backend env vars).",
        ),
    ] = None,
    connect_timeout: Annotated[
        float | None,
        typer.Option(
            "--connect-timeout", help="Backend connect/initialize timeout (seconds)."
        ),
    ] = None,
    reconnect_initial_backoff: Annotated[
        float | None,
        typer.Option(
            "--reconnect-initial-backoff",
            help="First delay before retrying a failed backend connection (seconds).",
        ),
    ] = None,
    reconnect_max_backoff: Annotated[
        float | None,
        typer.Option(
            "--reconnect-max-backoff",
            help="Cap on the exponential reconnect backoff delay (seconds).",
        ),
    ] = None,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="DEBUG, INFO (default), WARNING, ERROR or CRITICAL. Overrides "
            "MCP_PROXY_LOG_LEVEL.",
        ),
    ] = None,
) -> None:
    """Start the MCP proxy server, connected to the real backend."""
    overrides: dict[str, Any] = {}
    if backend_config is not None:
        overrides["backend_config"] = backend_config
    if connect_timeout is not None:
        overrides["connect_timeout_seconds"] = connect_timeout
    if reconnect_initial_backoff is not None:
        overrides["reconnect_initial_backoff_seconds"] = reconnect_initial_backoff
    if reconnect_max_backoff is not None:
        overrides["reconnect_max_backoff_seconds"] = reconnect_max_backoff
    if log_level is not None:
        overrides["log_level"] = log_level

    settings = get_settings(**overrides)
    _configure_logging(settings.log_level)

    proxy_app = create_proxy_app(settings=settings)

    typer.echo(f"Upstream: {resolve_backend_url(settings)}")

    if transport == "stdio":
        proxy_app.mcp.run(transport="stdio")
        return

    effective_host = host or settings.listen_host
    effective_port = port or settings.listen_port
    typer.echo(
        f"Starting MCP call-orchestrator proxy on {effective_host}:{effective_port}"
    )
    proxy_app.mcp.run(transport=transport, host=effective_host, port=effective_port)


def main() -> None:
    """Entry point for the console script."""
    app()


if __name__ == "__main__":
    main()
