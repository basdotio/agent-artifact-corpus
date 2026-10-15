"""Nginx Proxy Manager MCP tool.

Lets Claude read and change an Nginx Proxy Manager (NPM) through its API.

Settings come from environment variables only. The password and the login
token are never written to disk, never printed, and never sent anywhere
except the NPM server.

  NPM_URL         Example: http://172.16.90.75:81   (required)
  NPM_EMAIL       Login email of an NPM user        (required)
  NPM_PASSWORD    Password of that user             (required)
  NPM_VERIFY_TLS  "false" to skip TLS checks for a self-signed https URL
"""

from __future__ import annotations

import json
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

__version__ = "2026.09.28.01"

mcp = FastMCP("nginx-proxy-manager")

# ---------------------------------------------------------------------------
# What each kind of NPM object looks like
# ---------------------------------------------------------------------------
# "fields" are the only keys NPM accepts when writing. NPM rejects anything
# else (id, created_on, owner, certificate, ...), so update strips them.

KINDS: dict[str, dict[str, Any]] = {
    "proxy-hosts": {
        "path": "/api/nginx/proxy-hosts",
        "expand": "owner,access_list,certificate",
        "fields": (
            "domain_names", "forward_scheme", "forward_host", "forward_port",
            "certificate_id", "ssl_forced", "hsts_enabled", "hsts_subdomains",
            "http2_support", "block_exploits", "caching_enabled",
            "allow_websocket_upgrade", "access_list_id", "advanced_config",
            "enabled", "meta", "locations",
        ),
        "required": ("domain_names", "forward_host", "forward_port"),
        "defaults": {
            "forward_scheme": "http", "certificate_id": 0, "ssl_forced": False,
            "hsts_enabled": False, "hsts_subdomains": False, "http2_support": False,
            "block_exploits": True, "caching_enabled": False,
            "allow_websocket_upgrade": False, "access_list_id": 0,
            "advanced_config": "", "enabled": True, "meta": {}, "locations": [],
        },
        "summary": (
            "id", "domain_names", "forward_scheme", "forward_host", "forward_port",
            "enabled", "certificate_id", "ssl_forced", "access_list_id",
            "allow_websocket_upgrade",
        ),
        "toggle": True,
    },
    "redirection-hosts": {
        "path": "/api/nginx/redirection-hosts",
        "expand": "owner,certificate",
        "fields": (
            "domain_names", "forward_scheme", "forward_domain_name",
            "forward_http_code", "preserve_path", "certificate_id", "ssl_forced",
            "hsts_enabled", "hsts_subdomains", "http2_support", "block_exploits",
            "advanced_config", "enabled", "meta",
        ),
        "required": ("domain_names", "forward_domain_name"),
        "defaults": {
            "forward_scheme": "auto", "forward_http_code": 301, "preserve_path": True,
            "certificate_id": 0, "ssl_forced": False, "hsts_enabled": False,
            "hsts_subdomains": False, "http2_support": False, "block_exploits": False,
            "advanced_config": "", "enabled": True, "meta": {},
        },
        "summary": (
            "id", "domain_names", "forward_scheme", "forward_domain_name",
            "forward_http_code", "enabled", "certificate_id",
        ),
        "toggle": True,
    },
    "dead-hosts": {
        "path": "/api/nginx/dead-hosts",
        "expand": "owner,certificate",
        "fields": (
            "domain_names", "certificate_id", "ssl_forced", "hsts_enabled",
            "hsts_subdomains", "http2_support", "advanced_config", "enabled", "meta",
        ),
        "required": ("domain_names",),
        "defaults": {
            "certificate_id": 0, "ssl_forced": False, "hsts_enabled": False,
            "hsts_subdomains": False, "http2_support": False,
            "advanced_config": "", "enabled": True, "meta": {},
        },
        "summary": ("id", "domain_names", "enabled", "certificate_id"),
        "toggle": True,
    },
    "streams": {
        "path": "/api/nginx/streams",
        "expand": "owner,certificate",
        "fields": (
            "incoming_port", "forwarding_host", "forwarding_port", "tcp_forwarding",
            "udp_forwarding", "certificate_id", "enabled", "meta",
        ),
        "required": ("incoming_port", "forwarding_host", "forwarding_port"),
        "defaults": {
            "tcp_forwarding": True, "udp_forwarding": False, "certificate_id": 0,
            "enabled": True, "meta": {},
        },
        "summary": (
            "id", "incoming_port", "forwarding_host", "forwarding_port",
            "tcp_forwarding", "udp_forwarding", "enabled",
        ),
        "toggle": True,
    },
    # Read and delete only. Make or change these with npm_call.
    "certificates": {
        "path": "/api/nginx/certificates",
        "expand": None,
        "fields": (),
        "required": (),
        "defaults": {},
        "summary": ("id", "provider", "nice_name", "domain_names", "expires_on"),
        "toggle": False,
    },
    "access-lists": {
        "path": "/api/nginx/access-lists",
        "expand": "owner,items,clients",
        "fields": (),
        "required": (),
        "defaults": {},
        "summary": ("id", "name", "satisfy_any", "pass_auth"),
        "toggle": False,
    },
}

# ---------------------------------------------------------------------------
# Safety tiers
# ---------------------------------------------------------------------------
# read         runs right away
# change       needs confirm=true (Claude must ask the user first)
# destructive  needs confirm=true AND confirm_phrase typed back exactly

# Never sent through this tool. The tool logs in by itself, and a token
# call would put a login in the chat.
BLOCKED_PREFIXES = ("/api/tokens",)
# Users and settings can lock you out, so changes there are destructive.
DESTRUCTIVE_PREFIXES = ("/api/users", "/api/settings")


def _bare(path: str) -> str:
    return path.split("?", 1)[0].rstrip("/") or "/"


def classify(method: str, path: str) -> str:
    method = method.upper()
    bare = _bare(path)
    if method == "GET":
        return "read"
    if method == "DELETE":
        return "destructive"
    if bare.startswith(DESTRUCTIVE_PREFIXES):
        return "destructive"
    return "change"


def _gate(tier: str, confirm: bool, phrase: str, expected: str,
          preview: Any, what: str) -> dict[str, Any] | None:
    """Return a 'stop and ask' answer, or None when it is fine to run."""
    if tier == "read":
        return None
    if not confirm:
        msg = (f"This is a {tier} step: {what}. Tell the user what will happen "
               "and ask first. Only after they say yes, call again with confirm=true")
        if tier == "destructive":
            msg += f" and confirm_phrase='{expected}'"
        return {"ok": False, "needs_confirm": True, "tier": tier,
                "message": msg + ".", "preview": preview}
    if tier == "destructive" and (phrase or "").strip() != expected:
        return {"ok": False, "needs_confirm": True, "tier": tier,
                "message": (f"This step is destructive. Set confirm_phrase to exactly "
                            f"'{expected}' after the user agrees."),
                "preview": preview}
    return None


# ---------------------------------------------------------------------------
# HTTP and login
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {"token": None, "exp": 0.0}
_lock = threading.Lock()


def _config() -> tuple[str, str, str]:
    url = os.environ.get("NPM_URL", "").strip().rstrip("/")
    email = os.environ.get("NPM_EMAIL", "").strip()
    password = os.environ.get("NPM_PASSWORD", "")
    if not (url and email and password):
        raise RuntimeError(
            "Set NPM_URL, NPM_EMAIL and NPM_PASSWORD in this tool's environment "
            "(see the README). They are not stored anywhere else."
        )
    return url, email, password


def _ssl_context() -> ssl.SSLContext | None:
    if os.environ.get("NPM_VERIFY_TLS", "true").lower() == "false":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _scrub(value: Any) -> Any:
    """Remove the password and the token from anything we hand back."""
    secrets = [s for s in (os.environ.get("NPM_PASSWORD", ""), _state.get("token")) if s]
    if not secrets:
        return value
    text = json.dumps(value, default=str)
    for s in secrets:
        text = text.replace(s, "***")
    try:
        return json.loads(text)
    except ValueError:
        return text


def _send(method: str, url: str, headers: dict[str, str], body: Any,
          ctx: ssl.SSLContext | None) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json", **headers}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw, status = resp.read(), resp.status
    except urllib.error.HTTPError as err:
        raw, status = err.read(), err.code
    except urllib.error.URLError as err:
        raise RuntimeError(f"Cannot reach NPM at {url.split('/api')[0]}: {err.reason}") from None
    except (TimeoutError, OSError) as err:
        raise RuntimeError(f"Cannot reach NPM at {url.split('/api')[0]}: {err}") from None
    try:
        parsed: Any = json.loads(raw) if raw else None
    except ValueError:
        parsed = raw.decode("utf-8", "replace")[:2000]
    return status, parsed


def _parse_expiry(value: Any) -> float:
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return time.time() + 1800


def _login(base: str, email: str, password: str, ctx: ssl.SSLContext | None) -> str:
    status, data = _send("POST", f"{base}/api/tokens", {},
                         {"identity": email, "secret": password}, ctx)
    if isinstance(data, dict) and data.get("requires_2fa"):
        raise RuntimeError(
            "This NPM user has two-step login turned on. "
            "Make a separate NPM user for Claude without it."
        )
    if status != 200 or not isinstance(data, dict) or not data.get("token"):
        raise RuntimeError(
            f"NPM login failed (HTTP {status}). Check NPM_EMAIL and NPM_PASSWORD."
        )
    _state["token"] = data["token"]
    _state["exp"] = _parse_expiry(data.get("expires"))
    return data["token"]


def _token(base: str, email: str, password: str, ctx: ssl.SSLContext | None,
           force: bool = False) -> str:
    with _lock:
        if force or not _state["token"] or time.time() > _state["exp"] - 60:
            return _login(base, email, password, ctx)
        return _state["token"]


def _check_path(path: str) -> None:
    bare = _bare(path)
    if not path.startswith("/api/") or ".." in path or "://" in path:
        raise ValueError("Path must start with /api/ and stay on the NPM server.")
    if any(ord(c) < 33 for c in path) or "\\" in path or "#" in path:
        raise ValueError("Path has characters that are not allowed.")
    if bare.startswith(BLOCKED_PREFIXES):
        raise ValueError(
            "Login and token calls are blocked. This tool logs in by itself."
        )


def _request(method: str, path: str, body: Any = None) -> dict[str, Any]:
    """Call the API. Returns a dict with ok, status, and data or error."""
    _check_path(path)
    base, email, password = _config()
    ctx = _ssl_context()
    url = f"{base}{path}"
    token = _token(base, email, password, ctx)
    status, data = _send(method.upper(), url, {"Authorization": f"Bearer {token}"}, body, ctx)
    if status == 401:  # token expired or was revoked. Log in once more.
        token = _token(base, email, password, ctx, force=True)
        status, data = _send(method.upper(), url, {"Authorization": f"Bearer {token}"}, body, ctx)
    if 200 <= status < 300:
        return {"ok": True, "status": status, "data": _scrub(data)}
    err = data.get("error", data) if isinstance(data, dict) else data
    return {"ok": False, "status": status, "error": _scrub(err)}


def _fail(err: Exception) -> dict[str, Any]:
    return {"ok": False, "error": _scrub(str(err))}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def _summarize(kind: str, items: Any) -> Any:
    keys = KINDS[kind]["summary"]
    if not isinstance(items, list):
        return items
    return [{k: it.get(k) for k in keys if k in it} for it in items if isinstance(it, dict)]


@mcp.tool()
def npm_status() -> dict[str, Any]:
    """Check that Nginx Proxy Manager is reachable and logged in.

    Returns the NPM version and how many proxy hosts, redirection hosts,
    404 hosts and streams exist. Read only. Good first call.
    """
    try:
        out: dict[str, Any] = {}
        root = _request("GET", "/api/")
        out["server"] = root.get("data") if root["ok"] else root
        counts = _request("GET", "/api/reports/hosts")
        out["counts"] = counts.get("data") if counts["ok"] else counts
        out["ok"] = root["ok"] and counts["ok"]
        out["tool_version"] = __version__
        return out
    except (RuntimeError, ValueError) as err:
        return _fail(err)


@mcp.tool()
def npm_hosts(
    kind: str,
    action: str = "list",
    id: int | None = None,
    data: dict[str, Any] | None = None,
    full: bool = False,
    confirm: bool = False,
    confirm_phrase: str = "",
) -> dict[str, Any]:
    """List, look at, add, change, delete, enable or disable NPM items.

    kind: proxy-hosts, redirection-hosts, dead-hosts, streams,
          certificates, or access-lists.
    action: list, get, create, update, delete, enable, disable.
      - list and get are read only. list gives a short summary unless full=true.
      - create needs `data`. Only the main fields are needed. Sensible
        defaults fill the rest (for proxy-hosts: http, no certificate,
        block_exploits on). Proxy host example:
        {"domain_names": ["app.example.com"], "forward_host": "172.16.1.5",
         "forward_port": 8080, "allow_websocket_upgrade": true}
      - update needs `id` and `data` with ONLY the fields to change. The tool
        reads the current item and merges, so nothing else is lost.
      - create, update, enable and disable need confirm=true, after asking the user.
      - delete needs confirm=true and confirm_phrase='delete <kind> <id>'.
    certificates and access-lists can only be listed, read, or deleted here.
    To make or change those, use npm_call.
    Tip: for a new outside address, use its own subdomain as a proxy host.
    Custom Locations under an existing domain have been unreliable on this NPM.
    """
    try:
        spec = KINDS.get(kind)
        if spec is None:
            return {"ok": False, "error": f"kind must be one of: {', '.join(KINDS)}"}
        action = action.lower()
        base = spec["path"]

        if action == "list":
            path = base + (f"?expand={spec['expand']}" if spec["expand"] else "")
            res = _request("GET", path)
            if res["ok"] and not full:
                res["data"] = _summarize(kind, res["data"])
            return res

        if action == "get":
            if id is None:
                return {"ok": False, "error": "id is required for get."}
            path = f"{base}/{int(id)}" + (f"?expand={spec['expand']}" if spec["expand"] else "")
            return _request("GET", path)

        if action in ("enable", "disable"):
            if not spec["toggle"]:
                return {"ok": False, "error": f"{kind} cannot be enabled or disabled."}
            if id is None:
                return {"ok": False, "error": "id is required."}
            what = f"{action} {kind} #{int(id)}"
            stop = _gate("change", confirm, confirm_phrase, "", {"id": id}, what)
            if stop:
                return stop
            return _request("POST", f"{base}/{int(id)}/{action}")

        if action == "delete":
            if id is None:
                return {"ok": False, "error": "id is required."}
            expected = f"delete {kind} {int(id)}"
            preview = _request("GET", f"{base}/{int(id)}")
            shown = _summarize(kind, [preview["data"]])[0] if preview["ok"] else preview
            stop = _gate("destructive", confirm, confirm_phrase, expected,
                         shown, f"delete {kind} #{int(id)} for good")
            if stop:
                return stop
            return _request("DELETE", f"{base}/{int(id)}")

        if action in ("create", "update"):
            if not spec["fields"]:
                return {"ok": False,
                        "error": f"{kind} cannot be {action}d here. Use npm_call."}
            if not isinstance(data, dict) or not data:
                return {"ok": False, "error": f"data is required for {action}."}
            unknown = [k for k in data if k not in spec["fields"]]
            if unknown:
                return {"ok": False,
                        "error": f"Unknown field(s): {', '.join(unknown)}.",
                        "allowed_fields": list(spec["fields"])}

            if action == "create":
                missing = [k for k in spec["required"] if k not in data]
                if missing:
                    return {"ok": False, "error": f"Missing: {', '.join(missing)}."}
                body = {**spec["defaults"], **data}
                stop = _gate("change", confirm, confirm_phrase, "", body,
                             f"add a new {kind.rstrip('s')}")
                if stop:
                    return stop
                return _request("POST", base, body)

            if id is None:
                return {"ok": False, "error": "id is required for update."}
            current = _request("GET", f"{base}/{int(id)}")
            if not current["ok"]:
                return current
            cur = current["data"]
            body = {k: cur[k] for k in spec["fields"] if k in cur}
            body.update(data)
            changes = {k: {"from": cur.get(k), "to": v} for k, v in data.items()
                       if cur.get(k) != v}
            stop = _gate("change", confirm, confirm_phrase, "", {"changes": changes},
                         f"change {kind} #{int(id)}")
            if stop:
                return stop
            return _request("PUT", f"{base}/{int(id)}", body)

        return {"ok": False,
                "error": "action must be: list, get, create, update, delete, enable, disable."}
    except (RuntimeError, ValueError) as err:
        return _fail(err)


@mcp.tool()
def npm_call(
    method: str,
    path: str,
    data: Any = None,
    confirm: bool = False,
    confirm_phrase: str = "",
) -> dict[str, Any]:
    """Call any NPM API path directly (the catch-all).

    method: GET, POST, PUT, PATCH or DELETE.
    path: starts with /api/, for example /api/nginx/certificates.
    data: JSON body for POST and PUT.
    GET runs right away. POST and PUT need confirm=true after asking the user.
    DELETE, and anything under /api/users or /api/settings, also needs
    confirm_phrase set to '<METHOD> <path>' exactly, for example
    'DELETE /api/nginx/certificates/3'.
    Login and token paths are blocked.
    Use npm_hosts for normal hosts and streams. Use this for certificates
    (create, renew), access lists, users, settings, and the audit log.
    """
    try:
        method = method.upper()
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            return {"ok": False, "error": "method must be GET, POST, PUT, PATCH or DELETE."}
        _check_path(path)
        tier = classify(method, path)
        expected = f"{method} {_bare(path)}"
        stop = _gate(tier, confirm, confirm_phrase, expected,
                     {"method": method, "path": path, "data": data},
                     f"{method} {path}")
        if stop:
            return stop
        res = _request(method, path, data)
        res["tier"] = tier
        return res
    except (RuntimeError, ValueError) as err:
        return _fail(err)


@mcp.tool()
def npm_audit_log(limit: int = 20) -> dict[str, Any]:
    """Show the newest changes made in NPM (who did what, and when). Read only."""
    try:
        res = _request("GET", "/api/audit-log?expand=user")
        if not res["ok"]:
            return res
        rows = res["data"] if isinstance(res["data"], list) else []
        rows = sorted(rows, key=lambda r: str(r.get("created_on", "")), reverse=True)
        out = []
        for r in rows[: max(1, min(int(limit), 200))]:
            user = r.get("user") or {}
            out.append({
                "when": r.get("created_on"),
                "who": user.get("name") or user.get("email"),
                "action": r.get("action"),
                "type": r.get("object_type"),
                "id": r.get("object_id"),
                "meta": r.get("meta"),
            })
        return {"ok": True, "data": out}
    except (RuntimeError, ValueError) as err:
        return _fail(err)


def main() -> None:
    mcp.run()
