"""The MCP proxy.

Sits between a client and one or more downstream MCP servers. Forwards everything;
records every tool call into the ledger on the way through.

Statelessness helps here. The 2026-07-28 revision removed protocol sessions and
the Mcp-Session-Id header, so there is no session to forward or pin — the proxy
holds the audit chain and nothing else, and the HTTP deployment scales
horizontally with no sticky routing (given one ledger writer per replica; see
the README on deployment).

Tool naming: downstream tools are exposed as `<server_id>__<tool>`. The proxy's
own tools live under `provmcp__` and are not recorded — they are not scientific
tool use, they are questions about the record.

WHAT THIS CANNOT DO — state it in the README, do not paper over it:
A practitioner systematization of regulated agent deployments argues that
auditability is an interface design constraint established before tools are built,
not a logging concern fixable at the infrastructure layer; tools built without
audit requirements carry no case identifiers or session context in their
signatures, and retrofitting that meant changing every tool's interface contract.
That critique is correct. This proxy captures what is observable at its boundary
and nothing the downstream tools never carried. It is provenance capture that
supports an audit trail. It is not a validated system and not GxP compliance.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio
from mcp.server import Server
from mcp.server.context import ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp_types import (
    CLIENT_INFO_META_KEY,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from . import __version__
from .config import Config, DownstreamServer, Retention
from .downstream import Downstreams, error_payload
from .ledger import Ledger
from .sources import resolve_release

log = logging.getLogger(__name__)

SEP = "__"
OWN_PREFIX = "provmcp" + SEP
REDACTED = "[redacted]"


@dataclass
class ProxyState:
    downstreams: Downstreams
    ledger: Ledger
    lock: anyio.Lock


def redact_arguments(arguments: dict, fields: list[str]) -> dict:
    """Drop named top-level argument values before they reach the ledger. The
    hash covers the redacted form, so a redacted call is not replayable — replay
    reports it as such rather than guessing."""
    if not fields:
        return arguments
    return {k: (REDACTED if k in fields else v) for k, v in arguments.items()}


def _client_label(ctx: ServerRequestContext[Any]) -> str | None:
    """Who called. Modern envelope carries clientInfo in _meta; the legacy
    handshake put it in initialize params. Either may be absent."""
    try:
        info: Any = None
        if ctx.meta and CLIENT_INFO_META_KEY in ctx.meta:
            info = ctx.meta[CLIENT_INFO_META_KEY]
        else:
            params = getattr(ctx.session, "client_params", None)
            if params is not None:
                info = params.client_info
        if info is None:
            return None
        if isinstance(info, dict):
            name, version = info.get("name"), info.get("version")
        else:
            name, version = getattr(info, "name", None), getattr(info, "version", None)
        if not name:
            return None
        return f"{name}/{version}" if version else str(name)
    except Exception:
        log.debug("could not identify client", exc_info=True)
        return None


def _text(s: str, is_error: bool = False) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=s)], is_error=is_error)


OWN_TOOLS: list[Tool] = [
    Tool(
        name=OWN_PREFIX + "verify",
        description=(
            "Verify the provenance ledger: hash chain continuity and, if the proxy is "
            "signing, Ed25519 signatures. Returns the entry count and chain head, or "
            "every detected problem."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name=OWN_PREFIX + "status",
        description=(
            "Describe this provenance proxy: downstream servers, the current data-source "
            "release of each where resolvable, ledger path, entry count, and whether "
            "entries are signed."
        ),
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name=OWN_PREFIX + "export",
        description=(
            "Write a portable W3C PROV bundle of the ledger so far into out_dir. The "
            "bundle contains the ledger, a PROV-JSON graph, a manifest with the chain "
            "head, and the verifying public key. Attach it to an ELN entry or a methods "
            "section; `provmcp verify-bundle <dir>` checks it without this proxy."
        ),
        input_schema={
            "type": "object",
            "properties": {"out_dir": {"type": "string", "description": "directory to create"}},
            "required": ["out_dir"],
            "additionalProperties": False,
        },
    ),
]


def build_proxy(config: Config, ledger: Ledger) -> Server[ProxyState]:
    """Construct the proxy as a low-level Server. Downstream connections open in
    the lifespan and close with it; tests inject in-process servers via
    DownstreamServer.inproc."""

    @asynccontextmanager
    async def lifespan(_: Server[ProxyState]) -> AsyncIterator[ProxyState]:
        async with Downstreams(config.servers, config.server_log_dir) as ds:
            yield ProxyState(downstreams=ds, ledger=ledger, lock=anyio.Lock())

    async def on_list_tools(
        ctx: ServerRequestContext[ProxyState], _params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        state = ctx.lifespan_context
        tools: list[Tool] = []
        for sid in state.downstreams.servers:
            for t in await state.downstreams.list_tools(sid):
                data = t.model_dump(by_alias=True, exclude_none=True)
                data["name"] = f"{sid}{SEP}{t.name}"
                data["description"] = f"[{sid}] {t.description or ''}".strip()
                tools.append(Tool.model_validate(data))
        tools.extend(OWN_TOOLS)
        return ListToolsResult(tools=tools)

    async def on_call_tool(
        ctx: ServerRequestContext[ProxyState], params: CallToolRequestParams
    ) -> CallToolResult:
        state = ctx.lifespan_context
        name, arguments = params.name, dict(params.arguments or {})

        if name.startswith(OWN_PREFIX):
            return await _own_tool(state, config, name[len(OWN_PREFIX):], arguments)

        sid, sep, tool = name.partition(SEP)
        server = config.by_id(sid) if sep else None
        if server is None:
            raise MCPError(INVALID_PARAMS, f"unknown tool {name!r}")

        return await _forward_and_record(ctx, state, server, tool, arguments)

    return Server(
        "provmcp",
        version=__version__,
        instructions=(
            "Every tool call through this proxy is recorded in a hash-chained provenance "
            "ledger. Tools are named <server>__<tool>. Call provmcp__status to see which "
            "data-source releases are live, and provmcp__export to save a PROV bundle."
        ),
        lifespan=lifespan,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


async def _forward_and_record(
    ctx: ServerRequestContext[ProxyState],
    state: ProxyState,
    server: DownstreamServer,
    tool: str,
    arguments: dict,
) -> CallToolResult:
    error: str | None = None
    result_obj: CallToolResult | None = None
    try:
        result_obj, result_json, duration_ms = await state.downstreams.call(
            server.id, tool, arguments
        )
    except Exception as exc:
        result_json, duration_ms = error_payload(exc), 0
        error = result_json["error"]

    release = await resolve_release(server.source, server.source_options, result_json)
    client = _client_label(ctx)

    # Record before returning. If recording fails, the call fails: an
    # unrecorded call in a provenance system is worse than a failed one.
    try:
        async with state.lock:
            entry = state.ledger.append(
                server_id=server.id,
                tool=tool,
                arguments=redact_arguments(arguments, server.redact_arguments),
                result=result_json,
                source_release=release,
                duration_ms=duration_ms,
                error=error,
                client=client,
                retain_result=server.retention is Retention.FULL,
            )
    except Exception as exc:
        log.error("LEDGER WRITE FAILED for %s.%s: %s", server.id, tool, exc)
        raise MCPError(
            INTERNAL_ERROR, f"provmcp: ledger write failed, call not recorded: {exc}"
        ) from exc

    log.info("seq %d  %s__%s  %s  %s", entry.seq, server.id, tool,
             entry.result_hash[:12], release or "-")

    if result_obj is None:
        return _text(f"provmcp: downstream call failed and was recorded (seq {entry.seq}): {error}",
                     is_error=True)
    return result_obj


async def _own_tool(state: ProxyState, config: Config, name: str, arguments: dict) -> CallToolResult:
    ledger = state.ledger
    if name == "verify":
        pub = ledger._key.public_key() if ledger._key is not None else None
        problems = ledger.verify(pub)
        n, head = ledger.head()
        if problems:
            return _text("LEDGER INVALID:\n" + "\n".join(problems), is_error=True)
        signed = "signatures verified" if pub else "unsigned (chain only)"
        return _text(f"ledger intact: {n} entries, head {head}, {signed}")

    if name == "status":
        lines = [f"provmcp {__version__}", f"ledger: {ledger.path} ({ledger.head()[0]} entries, "
                 f"{'signed' if ledger.signed else 'UNSIGNED'})"]
        for s in config.servers:
            rel = await resolve_release(s.source, s.source_options, {})
            where = " ".join(s.command) if s.command else (s.url or "in-process")
            lines.append(f"  {s.id}: {where}  release={rel or '?'}  retention={s.retention.value}")
        return _text("\n".join(lines))

    if name == "export":
        from .bundle import write_bundle

        raw = str(arguments.get("out_dir", "")).strip()
        if not raw:
            return _text("out_dir is required", is_error=True)
        out = Path(raw).expanduser()  # noqa: ASYNC240 — no I/O, just path expansion
        try:
            path = write_bundle(ledger, out)
        except Exception as exc:
            return _text(f"export failed: {exc}", is_error=True)
        return _text(f"bundle written to {path}")

    raise MCPError(INVALID_PARAMS, f"unknown provmcp tool {name!r}")
