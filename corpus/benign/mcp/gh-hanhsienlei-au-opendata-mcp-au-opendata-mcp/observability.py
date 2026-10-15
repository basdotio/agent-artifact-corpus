import hashlib
import json
import logging
import time
from collections.abc import Mapping
from typing import Any

from fastmcp.server.middleware import Middleware

log = logging.getLogger("au_opendata_mcp")

# Attributes LogRecord always carries. Anything else came from `extra` and belongs in the JSON.
_STANDARD_FIELDS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, merging whatever was passed via `extra`.

    Formatting must never raise: a log line that throws while logging an error is
    the worst possible time to fail. `default=str` handles most odd `extra` values,
    but two cases get past it -- a circular reference (json's cycle check fires
    before `default` is ever consulted) and a value whose own `__str__`/`__repr__`
    raises (the exception from `default=str` propagates straight out of
    `json.dumps`). Both are caught here and traded for a minimal, guaranteed-
    serialisable fallback payload rather than letting the formatter blow up.
    """

    def format(self, record: logging.LogRecord) -> str:
        try:
            payload: dict[str, Any] = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            for key, value in vars(record).items():
                if key not in _STANDARD_FIELDS:
                    payload[key] = value
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload, default=str)
        except Exception:
            return json.dumps(
                {
                    "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": "<log formatting failed>",
                }
            )


# Third-party loggers known to emit request details -- including full URLs and
# their query strings -- at INFO, and to propagate straight through root by
# default. search_datasets sends `q` (a user's question) as a GET query string,
# and any other tool argument that ends up in a URL is exposed the same way. The
# whole point of arguments_digest is that this content never reaches the log file;
# a chatty client library must not undo that by logging the raw request itself.
# httpcore is quieted defensively even though it does not currently log at INFO on
# the request path (it favours its own trace-extension mechanism); urllib3 is not
# a dependency of this project. "httpx2" is a *separate* distribution from "httpx"
# with its own logger name, pulled in transitively by fastmcp/mcp (and preferred by
# starlette.testclient) -- silencing "httpx" does nothing for it, and it logs the
# same "HTTP Request: GET <full url>" line at INFO.
_NOISY_THIRD_PARTY_LOGGERS = ("httpx", "httpx2", "httpcore")


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in _NOISY_THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def arguments_digest(arguments: Mapping[str, Any] | None) -> str:
    """A short, stable fingerprint of a call's arguments.

    Arguments are never logged verbatim: query_resource carries caller SQL and
    search_datasets carries a user's question. The digest is enough to correlate
    repeated calls without recording their content.
    """
    canonical = json.dumps(arguments or {}, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


UNROUTED = "<unrouted>"


class RequestLoggingMiddleware:
    """Log one structured record per HTTP request: method, route template, status, duration.

    This replaces uvicorn's own access log, which is disabled in `main.cli()`. It has to
    be replaced rather than reconfigured: `uvicorn.access` is created with
    ``propagate: False`` and its own handler, so `configure_logging` cannot reach it, and
    what it writes is the raw request line -- ``GET /api/datasets?q=<the user's
    question>`` -- which is exactly the content `arguments_digest` exists to keep out of
    the logs.

    Two deliberate choices:

    * **The route template, never the concrete path.** ``/api/tools/abn/51824753556`` and
      ``/api/datasets/{dataset_id}`` both carry caller-supplied values *in the path*, so
      stripping the query string alone would not be enough. `scope["route"]` is set by
      Starlette's router while the request is handled; a request that matched no route
      (a 404, or a malformed path) leaves it unset, and is reported as `UNROUTED` rather
      than raising here. The query string is never read at all.

    * **Raw ASGI, not `BaseHTTPMiddleware`.** The app mounts FastMCP's streaming HTTP
      transport at ``/mcp``; `BaseHTTPMiddleware` buffers through an anyio stream and is
      a known source of trouble for long-lived streaming responses. A bare ASGI wrapper
      touches nothing but the response-start message.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        status = 500  # what the caller sees if the app dies before sending a response
        started = time.perf_counter()

        async def send_wrapper(message: Any) -> None:
            nonlocal status
            if message.get("type") == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = scope.get("route")
            log.info(
                "request",
                extra={
                    "event": "request",
                    "method": scope.get("method", "?"),
                    "route": getattr(route, "path", UNROUTED),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )


class ToolTimingMiddleware(Middleware):
    """Log every MCP tool call with its duration and outcome."""

    async def on_call_tool(self, context: Any, call_next: Any) -> Any:
        message = getattr(context, "message", None)
        tool = getattr(message, "name", "unknown")
        digest = arguments_digest(getattr(message, "arguments", None))
        started = time.perf_counter()
        try:
            result = await call_next(context)
        except Exception as exc:
            # FastMCP wraps every tool-body exception in ToolError before it reaches
            # middleware (masked or not -- see server.py's call_tool), so
            # type(exc).__name__ is always "ToolError" and never the domain error
            # (UpstreamUnavailable, SqlRejected, ...) that actually happened. The
            # original is preserved via `raise ToolError(...) from e`, so walk the
            # cause chain to report the type that is actually useful for correlating
            # failures in the logs. Every raise site in this codebase chains exactly
            # one level, so this never loops today -- but `exc.__cause__ = exc` (or
            # a longer cycle) is something Python permits, and this code runs while
            # a tool call has already failed, so it must not be the thing that hangs.
            root: BaseException = exc
            seen: set[int] = {id(root)}
            for _ in range(10):
                cause = root.__cause__
                if cause is None or id(cause) in seen:
                    break
                root = cause
                seen.add(id(root))
            log.warning(
                "tool call failed",
                extra={
                    "event": "tool_call",
                    "tool": tool,
                    "args_digest": digest,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "outcome": "error",
                    "error_type": type(root).__name__,
                },
            )
            raise
        log.info(
            "tool call completed",
            extra={
                "event": "tool_call",
                "tool": tool,
                "args_digest": digest,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "outcome": "ok",
            },
        )
        return result
