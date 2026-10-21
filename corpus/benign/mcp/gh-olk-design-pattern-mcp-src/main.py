"""CLI entry point for the MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import click

from src.server import health_check, server_main


def _package_version() -> str:
    """Installed dist version, falling back to pyproject.toml (container runs uninstalled)."""
    try:
        return metadata.version("design-pattern-mcp")
    except metadata.PackageNotFoundError:
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        with pyproject.open("rb") as fh:
            return str(tomllib.load(fh)["project"]["version"])


@click.command()
@click.version_option(version=_package_version(), prog_name="design-pattern-mcp")
@click.option(
    "--config-path",
    default=None,
    help="Path to the config file (default: config/config.json; env DESIGN_PATTERN_CONFIG_PATH)",
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default=None,
    help="Transport mode: 'stdio' for subprocess clients, 'streamable-http' for HTTP (default from config)",
)
@click.option("--host", default=None, help="Host to bind for HTTP transport (default: 0.0.0.0)")
@click.option("--port", type=int, default=None, help="Port to bind for HTTP transport (default: 8050)")
@click.option(
    "--health",
    is_flag=True,
    default=False,
    help="Run the offline readiness check (config + catalog + index) and exit",
)
@click.option(
    "--offline",
    is_flag=True,
    default=False,
    help=(
        "Serve with the deterministic offline embedder/reranker instead of the configured TEI "
        "endpoints (no network; retrieval quality is lexical-only)"
    ),
)
def cli(
    config_path: str | None,
    transport: str | None,
    host: str | None,
    port: int | None,
    health: bool,
    offline: bool,
) -> None:
    """design-pattern-mcp server: select design patterns for a described system."""
    if health:
        report = asyncio.run(health_check(config_path))
        click.echo("OK")
        click.echo(json.dumps(report), err=True)
        sys.exit(0)

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr, force=True)
    asyncio.run(
        server_main(
            config_path=config_path, transport=transport, host=host, port=port, offline=offline
        )
    )


if __name__ == "__main__":
    cli()
