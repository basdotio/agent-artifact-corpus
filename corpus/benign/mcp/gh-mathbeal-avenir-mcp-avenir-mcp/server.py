# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Entry point of the avenir-mcp MCP server.

Importing the tool modules registers their tools on the shared server instance.
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
from datetime import UTC, datetime
from typing import Any

from pydantic import SecretStr

from avenir_mcp import (  # noqa: F401  pylint: disable=unused-import
    YNAB_API_VERSION,
    __version__,
    context,
    http_auth,
    logs,
    tools_accounts,
    tools_age,
    tools_budget,
    tools_categories,
    tools_charges,
    tools_classify,
    tools_flags,
    tools_networth,
    tools_payees,
    tools_payoff,
    tools_runway,
    tools_savings,
    tools_targets,
    tools_underfunded,
    tools_undo,
    updates,
)
from avenir_mcp.app import WRITE_TAG, configure, mcp, today

# The ways into the server, and nothing else: a tool is reached by registering on mcp,
# not through this module. Naming some tools here said twice what the registry says
# once, and the two drifted apart.
__all__ = [
    "WRITE_TAG",
    "configure",
    "http_options",
    "main",
    "mcp",
    "today",
]

logger = logging.getLogger(__name__)


def http_options(token: SecretStr) -> dict[str, Any]:
    """Say what guards the HTTP transport, besides listening on 127.0.0.1.

    The Host and Origin headers must name this machine, so a web page cannot reach
    the server through DNS rebinding; every request must carry the token, so no other
    program or user of the machine can.

    Args:
        token: AVENIR_MCP_HTTP_TOKEN, or the one made at start-up.

    Returns:
        Keyword arguments for FastMCP's run().
    """
    return {"host_origin_protection": True, "middleware": http_auth.middleware(token)}


def _new_http_token() -> str:
    """Make a token for an HTTP server started without AVENIR_MCP_HTTP_TOKEN, and say it.

    Printed once on stderr, not logged: the user needs it to connect a client, and
    log files may be shipped elsewhere.

    Returns:
        A random token, valid until the server stops.
    """
    token = secrets.token_urlsafe(32)
    print(
        "avenir-mcp: AVENIR_MCP_HTTP_TOKEN is not set, so this run requires a token made "
        f"for it:\n\n    Authorization: Bearer {token}\n\nIt changes at each start; set "
        "AVENIR_MCP_HTTP_TOKEN to a long random value to keep one.",
        file=sys.stderr,
        flush=True,
    )
    return token


def main(argv: list[str] | None = None) -> None:
    """Run the server: stdio by default, streamable HTTP when AVENIR_MCP_TRANSPORT=http.

    `avenir-mcp --version` prints the version and exits, for bug reports. The server
    takes no other argument: its configuration is in the environment.

    Read-only unless AVENIR_MCP_WRITE=1: write tools are then registered too.
    Diagnostics go to stderr (stdout belongs to the protocol in stdio mode), at
    AVENIR_MCP_LOG_LEVEL, WARNING by default, as text or, with
    AVENIR_MCP_LOG_FORMAT=json, one JSON object per line.

    Unless switched off (AVENIR_MCP_NO_UPDATE_CHECK=1, DO_NOT_TRACK=1 or a CI run),
    the server asks PyPI at most once a day whether a newer release exists, and says
    so in its instructions and as a warning in its logs (see updates).

    The HTTP address comes from AVENIR_MCP_HOST and AVENIR_MCP_PORT and defaults to
    127.0.0.1:8103, so the server is never reachable from the network by accident.
    Over HTTP, requests must name this machine and carry a token (see http_options):
    AVENIR_MCP_HTTP_TOKEN, or, when it is unset, a random token made at start-up and
    printed once on stderr.

    Args:
        argv: The command-line arguments; None for sys.argv.
    """
    if (sys.argv[1:] if argv is None else argv) == ["--version"]:
        print(f"avenir-mcp {__version__} (YNAB API v{YNAB_API_VERSION})")
        return
    logs.configure(
        os.getenv("AVENIR_MCP_LOG_LEVEL", "WARNING").upper(),
        os.getenv("AVENIR_MCP_LOG_FORMAT", "text"),
    )
    writes = os.getenv("AVENIR_MCP_WRITE") == "1"
    configure(enable_writes=writes)
    update = updates.check(os.environ, __version__, datetime.now(UTC))
    if update:
        logger.warning("%s", update)
        mcp.instructions = f"{mcp.instructions}\n\n{update}"
    if os.getenv("AVENIR_MCP_TRANSPORT", "stdio") == "http":
        host = os.getenv("AVENIR_MCP_HOST", "127.0.0.1")
        port = int(os.getenv("AVENIR_MCP_PORT", "8103"))
        # Masked from here on: a repr of the options, logged or printed, shows no token.
        token = SecretStr(os.getenv("AVENIR_MCP_HTTP_TOKEN") or _new_http_token())
        logger.info("Starting avenir-mcp on %s:%d", host, port)
        mcp.run(transport="streamable-http", host=host, port=port, **http_options(token))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
