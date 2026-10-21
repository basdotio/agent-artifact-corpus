"""MCP server over stdio exposing the MRTR tool — for wire-level reproduction.

The in-process `Client(mcp)` evidence from Milestone A cannot prove a guarantee
survives transport. This process exists so a test can speak RAW newline-delimited
JSON-RPC to it and capture every byte on the wire.

Wire framing (MCP 2026-07-28 stdio spec): one JSON-RPC message per line, no
header layer, stdout carries only MCP messages, stderr is free for logs.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.request_state import RequestStateSecurity
from mcp_types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult

from reference.backend import IssueStore

KEY = b"0123456789abcdef0123456789abcdef"  # fixed 32 bytes so tokens stay valid
ROOT = Path(__file__).resolve().parents[1]
_DB_VALUE = os.environ.get("WIRE_SERVER_DB")
DB_PATH = Path(_DB_VALUE) if _DB_VALUE else None
BACKEND_ID = os.environ.get("WIRE_BACKEND_ID")
# Case 09: crash AFTER the backend commits, BEFORE the reply is written.
# The effect lands in SQLite; the client sees a closed connection with no
# response. That is a real injected fault between commit and receipt.
FAULT_DROP_AFTER_COMMIT = os.environ.get("WIRE_FAULT", "") == "drop-after-commit"


def _ask(title: str) -> ElicitRequest:
    return ElicitRequest(
        params=ElicitRequestFormParams(
            message=f"Body for {title}?",
            requested_schema={
                "type": "object",
                "properties": {"body": {"type": "string"}},
                "required": ["body"],
            },
        )
    )


def _extract_body(responses: object) -> str:
    """Pull the `body` value out of the wire-shaped inputResponses map."""
    resp = responses["body"] if isinstance(responses, dict) else getattr(responses, "body", {})
    content = resp["content"] if isinstance(resp, dict) else getattr(resp, "content", {})
    return str(content.get("body", ""))


def build_server(store: IssueStore) -> MCPServer:
    mcp = MCPServer("wire-reference", request_state_security=RequestStateSecurity(keys=[KEY]))

    @mcp.tool()
    async def create_issue(title: str, ctx: Context) -> str | InputRequiredResult:
        if ctx.input_responses is None:
            return InputRequiredResult(
                input_requests={"body": _ask(title)},
                request_state="awaiting-body",
            )
        issue_id = store.create_issue(title, body=_extract_body(ctx.input_responses))
        if FAULT_DROP_AFTER_COMMIT:
            # The reply is never written. os._exit skips all cleanup, exactly
            # like a crashed process whose DB commit already happened.
            os._exit(70)
        return f"created {issue_id}"

    return mcp


def main() -> None:
    if DB_PATH is None or BACKEND_ID is None:
        raise SystemExit("WIRE_SERVER_DB and WIRE_BACKEND_ID are required")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    store = IssueStore(str(DB_PATH), backend_id=BACKEND_ID)
    mcp = build_server(store)
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
