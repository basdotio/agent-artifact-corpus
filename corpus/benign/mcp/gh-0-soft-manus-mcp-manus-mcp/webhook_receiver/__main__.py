"""CLI entrypoint: `python -m manus_mcp.webhook_receiver`."""

from __future__ import annotations

import argparse
import sys

import uvicorn
from pydantic import ValidationError

from manus_mcp.config import load_settings
from manus_mcp.logger import get_logger, set_level
from manus_mcp.webhook_receiver.server import create_app


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="manus-mcp-webhook")
    p.add_argument("--host", default=None)
    p.add_argument("--port", type=int, default=None)
    p.add_argument(
        "--public-url",
        default=None,
        help="Override MANUS_WEBHOOK_PUBLIC_URL for this run",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        settings = load_settings()
    except ValidationError as e:
        sys.stderr.write(f"Manus MCP webhook: configuration error.\n{e}\n")
        raise SystemExit(2) from e

    if args.public_url:
        settings = settings.model_copy(update={"manus_webhook_public_url": args.public_url})

    set_level(settings.manus_log_level)
    log = get_logger("webhook")

    if not settings.manus_webhook_public_url:
        sys.stderr.write(
            "Manus MCP webhook: set MANUS_WEBHOOK_PUBLIC_URL to the URL Manus will POST to.\n"
        )
        raise SystemExit(2)

    app = create_app(settings)
    host = args.host or settings.manus_webhook_host
    port = args.port or settings.manus_webhook_port
    log.info(
        "starting webhook receiver on %s:%d for public_url=%s",
        host,
        port,
        settings.manus_webhook_public_url,
    )
    uvicorn.run(app, host=host, port=port, log_level=settings.manus_log_level.lower())


if __name__ == "__main__":
    main()
