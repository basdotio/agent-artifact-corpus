"""Stdio entrypoint: `python -m manus_mcp`."""

from __future__ import annotations

import asyncio
import contextlib
import sys

from mcp.server.stdio import stdio_server
from pydantic import ValidationError

from manus_mcp.config import load_settings
from manus_mcp.logger import get_logger, set_level
from manus_mcp.server import build_server


async def _run() -> None:
    try:
        settings = load_settings()
    except ValidationError as e:
        sys.stderr.write(
            "Manus MCP: configuration error.\n"
            "Set MANUS_API_KEY in your environment or in a .env file next to the server.\n"
            f"Details: {e}\n"
        )
        raise SystemExit(2) from e

    set_level(settings.manus_log_level)
    log = get_logger()
    log.info("manus-mcp starting base_url=%s", settings.manus_base_url)

    server, client = build_server(settings)
    try:
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)
    finally:
        await client.aclose()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run())


if __name__ == "__main__":
    main()
