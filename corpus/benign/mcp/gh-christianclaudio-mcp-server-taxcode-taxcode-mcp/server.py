"""FastMCP server instance, modular sub-servers, hierarchical middleware, and entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import logging
import signal
import sys
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform, RegexSearchTransform
from fastmcp.tools import Tool
from mcp.server.caching import CacheHint

from taxcode_mcp import __version__
from taxcode_mcp.auth import (
    ALLOW_UNAUTHENTICATED_BIND_ENV,
    AUTH_TOKEN_ENV,
    SharedTokenVerifier,
    allow_unauthenticated_bind,
    is_localhost,
    read_auth_token,
)
from taxcode_mcp.client import TemplateClient
from taxcode_mcp.config import settings
from taxcode_mcp.errors import SafetyViolationError, redact_secrets
from taxcode_mcp.middleware import (
    ParentAuditMiddleware,
    ReadOnlyGateMiddleware,
)
from taxcode_mcp.profiles import (
    PROFILES,
    ReadOnlyAnnotations,
    ReadOnlyToolFilter,
    get_profile,
    validate_allowlist,
)
from taxcode_mcp.tools import (
    SUPPORTED_STATE_JURISDICTIONS,
    calculate_built_in_gain_sourcing,
    compliance_server,
    cross_border_tax_analysis,
    evaluate_georgia_residency,
    evaluate_pr_bona_fide_residency,
    evaluate_state_residency,
    get_capabilities,
    get_health_status,
    get_statute_resource,
    list_publications,
    lookup_statute,
    search_tax_code,
    statutes_server,
    system_server,
)

__all__ = [
    "CACHE_HINTS",
    "ParentAuditMiddleware",
    "ReadOnlyGateMiddleware",
    "SafetyViolationError",
    "SUPPORTED_STATE_JURISDICTIONS",
    "TemplateClient",
    "calculate_built_in_gain_sourcing",
    "client",
    "compliance_server",
    "create_server",
    "cross_border_tax_analysis",
    "evaluate_georgia_residency",
    "evaluate_pr_bona_fide_residency",
    "evaluate_state_residency",
    "get_capabilities",
    "get_health_status",
    "get_statute_resource",
    "list_publications",
    "lookup_statute",
    "main",
    "mcp",
    "redact_secrets",
    "search_tax_code",
    "server_lifespan",
    "settings",
    "statutes_server",
    "system_server",
]

CacheableMethod = Literal[
    "prompts/list",
    "resources/list",
    "resources/read",
    "resources/templates/list",
    "server/discover",
    "tools/list",
]

ToolSearchBackend = Literal["regex", "bm25"]

logger = logging.getLogger(__name__)

# Domain sub-servers by mount namespace (hybrid A+B: the namespace is the domain).
DOMAIN_SERVERS: dict[str, FastMCP] = {
    "system": system_server,
    "statutes": statutes_server,
    "compliance": compliance_server,
}

# FastMCP synthetic discovery tools that only read the catalog (annotated readOnlyHint=True).
TOOL_SEARCH_READ_ONLY_TOOLS = ("search_tools",)
CODE_MODE_READ_ONLY_TOOLS = ("search", "get_schema")

# MCP 2026-07-28 Deterministic Caching Hints (SEP-2549)
CACHE_HINTS: dict[CacheableMethod, CacheHint] = {
    "tools/list": CacheHint(ttl_ms=3600000, scope="public"),
    "prompts/list": CacheHint(ttl_ms=3600000, scope="public"),
    "resources/list": CacheHint(ttl_ms=3600000, scope="public"),
    "resources/templates/list": CacheHint(ttl_ms=3600000, scope="public"),
    "server/discover": CacheHint(ttl_ms=3600000, scope="public"),
}

client = TemplateClient()


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage server lifecycle and persistent client resources."""
    logger.info("Starting up Tax Code MCP server")
    try:
        yield {"client": client}
    finally:
        logger.info("Shutting down Tax Code MCP resources")
        await client.close()


def _streamable_http_app(
    self: FastMCP,
    path: str | None = None,
    stateless_http: bool | None = None,
    json_response: bool | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    **kwargs: Any,
) -> Any:
    """Compatibility bridge for streamable HTTP ASGI application."""
    allowed_hosts = kwargs.pop("allowed_hosts", None)
    if allowed_hosts is None:
        allowed_hosts = [host, "localhost", f"{host}:{port}", f"localhost:{port}"]
    return self.http_app(
        path=path,
        transport="streamable-http",
        stateless_http=stateless_http,
        json_response=json_response,
        host_origin_protection=True,
        allowed_hosts=allowed_hosts,
        **kwargs,
    )


if not hasattr(Tool, "input_schema"):
    Tool.input_schema = property(lambda self: getattr(self, "parameters", {}))  # type: ignore[attr-defined]


def _catalog_tool_names(root: FastMCP) -> set[str]:
    """Return the client-visible tool names of ``root`` via the public ``list_tools()``.

    Runs on a worker thread with its own event loop so ``create_server`` stays synchronous
    and safe to call from inside a running loop (tests, hosts).
    """

    async def _collect() -> set[str]:
        return {tool.name for tool in await root.list_tools()}

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _collect()).result()


def _apply_tool_allowlist(root: FastMCP, allowlist: frozenset[str]) -> None:
    """Expose only ``allowlist`` tools; prompts, resources, and templates are untouched.

    Public visibility API: disable every tool, then re-enable the named tools. The later
    ``enable`` wins. ``enable(only=True)`` is not used because it disables every component
    type first, which would also hide prompts and resources.
    """
    root.disable(components={"tool"})
    root.enable(names=set(allowlist), components={"tool"})


def _attach_tool_search(root: FastMCP, backend: ToolSearchBackend) -> None:
    """Attach Regex (default) or BM25 Tool Search transform to the root gateway."""
    if backend == "bm25":
        root.add_transform(BM25SearchTransform())
    else:
        root.add_transform(RegexSearchTransform())
    root.add_transform(ReadOnlyAnnotations(TOOL_SEARCH_READ_ONLY_TOOLS))


def _code_mode_sandbox_available() -> bool:
    """True when ``pydantic_monty`` (shipped by ``fastmcp[code-mode]``) is importable.

    Code Mode imports without it, but every ``execute`` call then fails, so attach is skipped.
    """
    return importlib.util.find_spec("pydantic_monty") is not None


def _attach_code_mode(root: FastMCP) -> bool:
    """Attach experimental Code Mode when its ``pydantic_monty`` sandbox is installed.

    Returns True when the transform was attached; False when a missing ``pydantic_monty``
    skipped it (install the ``code-mode`` extra, which pulls ``fastmcp[code-mode]``).
    """
    if not _code_mode_sandbox_available():
        logger.warning(
            "Code Mode requested but pydantic-monty (the Code Mode sandbox) is not installed; "
            "skipping attach. Install the code-mode extra (mcp-server-taxcode[code-mode]) "
            "or omit --enable-code-mode."
        )
        return False
    from fastmcp.experimental.transforms.code_mode import CodeMode

    root.add_transform(CodeMode())
    root.add_transform(ReadOnlyAnnotations(CODE_MODE_READ_ONLY_TOOLS))
    return True


def create_server(
    profile: str | None = None,
    enable_tool_search: bool | None = None,
    enable_code_mode: bool | None = None,
    tool_search_backend: ToolSearchBackend | None = None,
) -> FastMCP:
    """Build root gateway FastMCP instance using Server Composition and Hierarchical Middleware.

    Architecture:
    Gateway (FastMCP)
    ├── Parent Middleware (ParentAuditMiddleware, ReadOnlyGateMiddleware)
    ├── mount(system_server, namespace="system")   # domain mount, not a product stamp
    ├── mount(items_server, namespace="items")
    ├── (allowlist profiles) tools-only visibility allowlist over the full catalog
    ├── (readonly) ReadOnlyToolFilter: keep tools annotated readOnlyHint=True
    └── (Optional, profile==full only) Tool Search XOR experimental Code Mode

    Profile rules:
    * Domain-mount profiles mount the listed domains; allowlist profiles mount every
      domain and expose only the allowlisted tool names (prompts/resources stay).
    * An unknown profile, or an allowlisted name missing from the full catalog, raises
      ``ValueError`` at build time.

    Discovery rules:
    * Default: flat ``tools/list`` of mounted domain tools (curated or full).
    * Tool Search / Code Mode attach only when explicitly enabled **and** ``profile == "full"``.
    * Requesting either discovery mode on a curated profile logs a warning and skips attach.
    * Enabling both Tool Search and Code Mode raises ``ValueError`` (mutual exclusion).
    """
    active = get_profile(profile or settings.MCP_PROFILE)
    active_profile = active.name
    use_tool_search = (
        enable_tool_search if enable_tool_search is not None else settings.MCP_ENABLE_TOOL_SEARCH
    )
    use_code_mode = (
        enable_code_mode if enable_code_mode is not None else settings.MCP_ENABLE_CODE_MODE
    )
    search_backend: ToolSearchBackend = (
        tool_search_backend if tool_search_backend is not None else settings.MCP_TOOL_SEARCH_BACKEND
    )

    if use_tool_search and use_code_mode:
        raise ValueError(
            "Tool Search and Code Mode are mutually exclusive; enable only one discovery mode."
        )

    # Bearer auth on every HTTP entry point (``main()``, ``fastmcp run``, ``http_app()``):
    # FastMCP servers default to ``auth=None``, so the verifier is attached at build time
    # whenever the stripped token env is non-blank. The localhost bind refusal stays in
    # ``main()``, the only entry point that knows the bind host.
    auth_token = read_auth_token()
    root = FastMCP(
        "taxcode-mcp",
        version=__version__,
        auth=SharedTokenVerifier(auth_token) if auth_token else None,
        lifespan=server_lifespan,
        cache_ttl=3600,
        cache_scope="public",
    )

    # Attach ASGI streamable HTTP compatibility bridge
    root.streamable_http_app = _streamable_http_app.__get__(root, FastMCP)  # type: ignore[attr-defined]

    # 1. Global Parent Middleware (Audit logging, request timing, and read-only gate)
    readonly_gate = ReadOnlyGateMiddleware(enforce=active.readonly)
    root.add_middleware(ParentAuditMiddleware())
    root.add_middleware(readonly_gate)

    # 2. Server Composition via mount(subserver, namespace=...) — Hybrid A+B domain mounts
    for domain in active.domains:
        root.mount(DOMAIN_SERVERS[domain], namespace=domain)

    # 3. Allowlist profiles: validate against the full mounted catalog, then filter tools
    if active.is_allowlist:
        allowlist = validate_allowlist(active, _catalog_tool_names(root))
        _apply_tool_allowlist(root, allowlist)

    # 4. Read-only: keep only tools annotated readOnlyHint=True (annotation is the truth)
    if active.readonly or settings.MCP_READONLY:
        # Capture the profile catalog before the filter hides writes, so the gate refuses a
        # hidden real tool but lets an unknown name reach FastMCP's "Unknown tool" error.
        readonly_gate.catalog = frozenset(_catalog_tool_names(root))
        root.add_transform(ReadOnlyToolFilter())

    # 5. Opt-in discovery transforms — full profile only (never dump full catalog by default)
    if use_tool_search:
        if active_profile != "full":
            logger.warning(
                "Tool Search requested with profile=%r; attach is allowed only on profile='full'. "
                "Keeping flat curated tools/list.",
                active_profile,
            )
        else:
            _attach_tool_search(root, search_backend)

    if use_code_mode:
        if active_profile != "full":
            logger.warning(
                "Code Mode requested with profile=%r; attach is allowed only on profile='full'. "
                "Keeping flat curated tools/list.",
                active_profile,
            )
        else:
            _attach_code_mode(root)

    return root


# Default canonical server gateway instance
mcp = create_server()


def _handle_shutdown(signum: int, frame: Any) -> None:
    """Handle SIGTERM/SIGINT from host supervisor and unwind gracefully."""
    logger.info("Received signal %s; shutting down.", signum)
    sys.exit(0)


def _apply_http_auth(parser: argparse.ArgumentParser, transport: str, host: str) -> None:
    """Make sure bearer auth from the token env is on, or enforce the localhost-only bind policy.

    ``create_server`` already attaches the verifier when the token env is set at build time;
    this attaches it at serve time if the env was set after import and no verifier exists
    yet. A token changed after the server is built is not picked up; rebuild the server.
    A token that is empty after ``.strip()`` counts as unset. With no token, a bind to any
    host other than 127.0.0.1, ::1 or localhost exits through ``parser.error`` unless
    ``TAXCODE_MCP_ALLOW_UNAUTHENTICATED_BIND`` opts in. Messages never include the token.
    """
    auth_token = read_auth_token()
    if auth_token:
        if not isinstance(mcp.auth, SharedTokenVerifier):
            mcp.auth = SharedTokenVerifier(auth_token)
        logger.info("Bearer token authentication is on for the %s transport", transport)
        return
    if not is_localhost(host):
        if not allow_unauthenticated_bind():
            parser.error(
                f"refusing to serve {transport} on non-localhost host {host!r} without "
                f"authentication: set {AUTH_TOKEN_ENV}, bind to 127.0.0.1, ::1 or localhost, "
                f"or set {ALLOW_UNAUTHENTICATED_BIND_ENV}=1 to accept an unauthenticated bind"
            )
        logger.warning(
            "%s is set: serving %s on non-localhost host %r without authentication.",
            ALLOW_UNAUTHENTICATED_BIND_ENV,
            transport,
            host,
        )
    logger.warning(
        "%s is not set, so MCP requests on the %s transport are not authenticated.",
        AUTH_TOKEN_ENV,
        transport,
    )


def main() -> None:
    """Run MCPServer with transport selection, profile configuration, and graceful shutdown."""
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    parser = argparse.ArgumentParser(description="Tax Code MCP Server (2026-07-28 Spec)")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport protocol: 'stdio' (default), 'streamable-http' (modern), or 'sse'.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address for HTTP transports (default: 127.0.0.1).",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transports.")
    parser.add_argument(
        "--stateless",
        action="store_true",
        default=settings.MCP_STATELESS_HTTP,
        help=(
            "Run Streamable HTTP in stateless mode "
            "(fresh connection per request, no Mcp-Session-Id)."
        ),
    )
    parser.add_argument(
        "--json-response",
        action="store_true",
        default=settings.MCP_JSON_RESPONSE,
        help="Return direct JSON responses instead of SSE text/event-stream over Streamable HTTP.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=settings.MCP_PROFILE,
        help=(
            "Server profile (default 'full'): domain-mount profiles full/system/items/readonly "
            "or job-shaped allowlist profiles such as 'intake'."
        ),
    )
    parser.add_argument(
        "--enable-tool-search",
        action="store_true",
        default=settings.MCP_ENABLE_TOOL_SEARCH,
        help=(
            "Enable Tool Search on profile=full only "
            "(replaces tools/list with search_tools + call_tool)."
        ),
    )
    parser.add_argument(
        "--tool-search-backend",
        choices=["regex", "bm25"],
        default=settings.MCP_TOOL_SEARCH_BACKEND,
        help="Tool Search backend: 'regex' (default) or 'bm25'.",
    )
    parser.add_argument(
        "--enable-code-mode",
        action="store_true",
        default=settings.MCP_ENABLE_CODE_MODE,
        help=(
            "Enable experimental Code Mode on profile=full only "
            "(search + execute). Mutually exclusive with --enable-tool-search."
        ),
    )
    parser.add_argument(
        "--allowed-host",
        action="append",
        dest="allowed_hosts",
        default=None,
        help="Allowed host for HTTP transports (can be specified multiple times).",
    )
    parser.add_argument(
        "--allowed-origin",
        action="append",
        dest="allowed_origins",
        default=None,
        help="Allowed origin for HTTP transports (can be specified multiple times).",
    )
    args = parser.parse_args()

    # Re-initialize server if non-default profile or discovery flags passed
    global mcp
    if (
        args.profile != settings.MCP_PROFILE
        or args.enable_tool_search != settings.MCP_ENABLE_TOOL_SEARCH
        or args.enable_code_mode != settings.MCP_ENABLE_CODE_MODE
        or args.tool_search_backend != settings.MCP_TOOL_SEARCH_BACKEND
    ):
        mcp = create_server(
            profile=args.profile,
            enable_tool_search=args.enable_tool_search,
            enable_code_mode=args.enable_code_mode,
            tool_search_backend=args.tool_search_backend,
        )

    if args.transport != "streamable-http":
        if args.stateless:
            logger.warning("--stateless flag is only applicable to 'streamable-http' transport.")
        if args.json_response:
            logger.warning(
                "--json-response flag is only applicable to 'streamable-http' transport."
            )

    if args.transport in ("sse", "streamable-http"):
        _apply_http_auth(parser, args.transport, args.host)

    hosts = getattr(args, "allowed_hosts", None)
    if hosts is None:
        if args.transport == "streamable-http" and args.host in ("0.0.0.0", "::"):
            parser.error("--allowed-host is required when binding to a wildcard host")
        hosts = [args.host, "localhost", f"{args.host}:{args.port}", f"localhost:{args.port}"]
    elif any(h.strip() == "*" for h in hosts):
        parser.error("Wildcard '*' is not permitted in --allowed-host; specify explicit hostnames.")
    run_kwargs: dict[str, Any] = {
        "host": args.host,
        "port": args.port,
        "host_origin_protection": True,
        "allowed_hosts": hosts,
    }
    if args.allowed_origins is not None:
        run_kwargs["allowed_origins"] = args.allowed_origins

    if args.transport == "sse":
        logger.warning(
            "Deprecation Warning: HTTP+SSE transport is deprecated per MCP 2026-07-28 spec "
            "(SEP-2577). Please migrate to Streamable HTTP (--transport streamable-http)."
        )
        mcp.run(
            transport="sse",
            **run_kwargs,
        )
    elif args.transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            stateless_http=args.stateless,
            json_response=args.json_response,
            **run_kwargs,
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
