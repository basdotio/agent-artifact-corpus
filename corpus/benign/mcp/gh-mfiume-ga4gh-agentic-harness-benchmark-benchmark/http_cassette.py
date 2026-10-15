"""Recorded upstream HTTP, so every model and every MCP build sees the same service answers.

The cassette sits below the MCP server rather than in front of it: the server runs its own,
current code, and only the HTTP exchanges with GA4GH services are replayed. A change to a tool
(a clearer error, a new parameter, paging) is therefore exercised against the same frozen
services as its parent build, and only requests no earlier run made go to the network.

It is installed inside the MCP server's process by ``mcp_launch`` and patches
``httpx.AsyncClient.send``. Modes are those of the tool cassette: ``live``, ``record``,
``replay`` and ``replay-or-record``. An exchange is keyed by method, URL and request body.

Not stored, because a later run may get a real answer and a stored one would be replayed to
every later model: timeouts, HTTP 429 and gateway errors (502, 503, 504), and connection
failures while this machine is offline. A connection failure while online (a dead service's
DNS name) is stored and replayed as the same exception.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import importlib
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx

MODES = ("live", "record", "replay", "replay-or-record")
NETWORK_CHECK_URL = "https://implementation-registry.ga4gh.org/api/services"
_TRANSIENT_STATUS = {429, 502, 503, 504}
_DROPPED_HEADERS = {"content-encoding", "content-length", "transfer-encoding", "connection", "set-cookie"}


def key(method: str, url: str, body: bytes) -> str:
    digest = hashlib.sha256(body or b"").hexdigest()
    return hashlib.sha256(f"{method.upper()} {url} {digest}".encode()).hexdigest()


class HttpCassette:
    def __init__(self, path: Path, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.path, self.mode = path, mode
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        self.stats = {"replayed": 0, "live": 0, "stored": 0, "refused": 0}
        # A published recording ships gzipped beside the path (http.jsonl.gz); new entries are
        # appended to the plain file, which is read after it so they take precedence.
        for source in (path.with_name(path.name + ".gz"), path):
            if not source.is_file():
                continue
            text = gzip.decompress(source.read_bytes()).decode() if source.suffix == ".gz" else source.read_text()
            for line in text.splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self._entries[entry["key"]] = entry

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, k: str) -> dict[str, Any] | None:
        if self.mode in ("live", "record"):
            return None
        return self._entries.get(k)

    def put(self, entry: dict[str, Any]) -> None:
        if self.mode == "live":
            return
        with self._lock:
            self._entries[entry["key"]] = entry
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as handle:
                handle.write(json.dumps(entry) + "\n")
        self.stats["stored"] += 1


def _body_fields(content: bytes) -> dict[str, str]:
    try:
        return {"body": content.decode("utf-8")}
    except UnicodeDecodeError:
        return {"body_b64": base64.b64encode(content).decode()}


def _entry_body(entry: dict[str, Any]) -> bytes:
    if "body_b64" in entry:
        return base64.b64decode(entry["body_b64"])
    return (entry.get("body") or "").encode("utf-8")


def _exception(entry: dict[str, Any], request: httpx.Request) -> Exception:
    module, _, name = entry["error"].rpartition(".")
    try:
        cls = getattr(importlib.import_module(module), name)
        try:
            return cls(entry.get("message", ""), request=request)
        except TypeError:
            return cls(entry.get("message", ""))
    except Exception:  # noqa: BLE001
        return httpx.ConnectError(entry.get("message", ""), request=request)


def install(path: Path, mode: str, online: Any = None) -> HttpCassette:
    """Patch httpx in this process. Returns the cassette, whose stats count what happened.

    ``online`` is an async callable answering whether this machine is online (default: the
    registry answers), consulted before a connection failure is stored."""
    cassette = HttpCassette(path, mode)
    if mode == "live":
        return cassette
    original = httpx.AsyncClient.send
    state = {"checked": 0.0, "ok": True}

    async def network_ok() -> bool:
        if time.monotonic() - state["checked"] < 20:
            return state["ok"]
        try:
            async with httpx.AsyncClient(timeout=10) as probe:
                state["ok"] = (await original(probe, probe.build_request("GET", NETWORK_CHECK_URL))).status_code < 500
        except Exception:  # noqa: BLE001
            state["ok"] = False
        state["checked"] = time.monotonic()
        return state["ok"]

    async def send(self: httpx.AsyncClient, request: httpx.Request, *args: Any, **kwargs: Any) -> httpx.Response:
        body = await request.aread()
        k = key(request.method, str(request.url), body)
        entry = cassette.get(k)
        if entry is not None:
            cassette.stats["replayed"] += 1
            if "error" in entry:
                raise _exception(entry, request)
            return httpx.Response(entry["status"], headers=entry.get("headers") or {},
                                  content=_entry_body(entry), request=request)
        if cassette.mode == "replay":
            cassette.stats["refused"] += 1
            raise httpx.ConnectError(f"not recorded, so it cannot be replayed: {request.method} {request.url}",
                                     request=request)
        cassette.stats["live"] += 1
        base = {"key": k, "method": request.method, "url": str(request.url),
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        try:
            response = await original(self, request, *args, **kwargs)
        except httpx.TimeoutException:
            raise
        except Exception as exc:  # noqa: BLE001  stored only if the failure is the service's
            if await (online or network_ok)():
                cls = exc.__class__
                cassette.put({**base, "error": f"{cls.__module__}.{cls.__qualname__}", "message": str(exc)})
            raise
        content = await response.aread()
        print(f"[http-cassette] live {request.method} {request.url} -> {response.status_code}", file=sys.stderr, flush=True)
        if response.status_code not in _TRANSIENT_STATUS:
            headers = {h: v for h, v in response.headers.items() if h.lower() not in _DROPPED_HEADERS}
            cassette.put({**base, "status": response.status_code, "headers": headers, **_body_fields(content)})
        return response

    httpx.AsyncClient.send = send  # type: ignore[method-assign]
    return cassette
