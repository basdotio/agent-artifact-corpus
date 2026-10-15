"""Arr stack MCP tool.

Lets Claude read and manage Sonarr, Radarr, Prowlarr, Bazarr, Seerr,
qBittorrent, Jellyfin and Tdarr through their own APIs.

Settings come from environment variables only. Keys and passwords are never
written to disk, never printed, and only sent to the matching service.

For each service you use, set its address and key. Services with no address
are simply off.

  ARR_SONARR_URL      ARR_SONARR_KEY
  ARR_RADARR_URL      ARR_RADARR_KEY
  ARR_PROWLARR_URL    ARR_PROWLARR_KEY
  ARR_BAZARR_URL      ARR_BAZARR_KEY
  ARR_SEERR_URL   ARR_SEERR_KEY   (ARR_OVERSEERR_* still works)
  ARR_JELLYFIN_URL    ARR_JELLYFIN_KEY
  ARR_QBITTORRENT_URL ARR_QBITTORRENT_USER ARR_QBITTORRENT_PASS
  ARR_TDARR_URL       ARR_TDARR_KEY   (a Tdarr API key, made in Tools, API Keys)
  ARR_VERIFY_TLS      "false" to skip TLS checks for self-signed https
  ARR_TIMEOUT         seconds to wait for an answer (default 30)

An address may have a URL base, like http://nas:8989/sonarr.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any

from mcp.server.fastmcp import FastMCP

__version__ = "2026.10.12.01"

mcp = FastMCP("arr-stack")

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
# prefix: the API root added in front of every path.
# auth:   how the key is sent.
SERVICES: dict[str, dict[str, str]] = {
    "sonarr": {"label": "Sonarr", "prefix": "/api/v3", "auth": "x-api-key"},
    "radarr": {"label": "Radarr", "prefix": "/api/v3", "auth": "x-api-key"},
    "prowlarr": {"label": "Prowlarr", "prefix": "/api/v1", "auth": "x-api-key"},
    "bazarr": {"label": "Bazarr", "prefix": "/api", "auth": "x-api-key"},
    "seerr": {"label": "Seerr", "prefix": "/api/v1", "auth": "x-api-key"},
    "jellyfin": {"label": "Jellyfin", "prefix": "", "auth": "jellyfin"},
    "qbittorrent": {"label": "qBittorrent", "prefix": "/api/v2", "auth": "cookie"},
    "tdarr": {"label": "Tdarr", "prefix": "/api/v2", "auth": "x-api-key"},
}

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
# read         runs right away (GET)
# change       needs confirm=true (Claude must ask the user first)
# destructive  needs confirm=true AND confirm_phrase "<service> <METHOD> <path>"

# Anything with these in the path is never sent. They carry passwords or keys.
BLOCKED_PARTS = ("/auth/", "authenticate", "initialize.js", "/quickconnect")

# A non-GET call with one of these in the path is destructive.
DESTRUCTIVE_PARTS = (
    "/system/restart", "/system/shutdown", "/restart", "/shutdown",
    "/backup/restore", "/config/host", "/config/security", "/system/settings",
    "/regenerate", "/delete", "/password", "/policy", "/users/new",
)

# Commands that restart or update the app.
DESTRUCTIVE_COMMANDS = {"restartapplication", "applicationupdate"}

# qBittorrent preferences that can lock you out of the web page.
RISKY_QBIT_PREFS = {
    "web_ui_username", "web_ui_password", "web_ui_port", "web_ui_address",
    "web_ui_https_enabled", "bypass_auth_subnet_whitelist",
    "bypass_auth_subnet_whitelist_enabled", "bypass_local_auth",
    "web_ui_csrf_protection_enabled", "web_ui_host_header_validation_enabled",
}

# JSON keys whose values are hidden in anything shown to Claude.
SECRET_KEYS = {
    "apikey", "password", "passwordconfirmation", "token", "accesstoken",
    "secret", "api_key", "web_ui_password", "authtoken",
    "seededapikey", "authsecretkey",
}

# Tdarr uses POST for database reads. These modes only read.
TDARR_READ_MODES = {"getall", "getbyid", "getbyidmulti", "getone", "count"}
SECRET_FIELD_NAMES = {"apikey", "password", "token", "secret", "passkey", "username"}

METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


def classify(service: str, method: str, path: str,
             params: dict[str, Any] | None = None, body: Any = None) -> str:
    m = method.upper()
    low = path.lower().rstrip("/")
    if m == "GET":
        return "read"
    if m == "DELETE":
        return "destructive"
    if service == "tdarr" and low.endswith("/search-db"):
        return "read"
    if service == "tdarr" and low.endswith("/cruddb") and isinstance(body, dict):
        mode = str((body.get("data") or {}).get("mode", "")).lower()
        if mode in TDARR_READ_MODES:
            return "read"
        if mode.startswith("remove"):
            return "destructive"
    if any(part in low for part in DESTRUCTIVE_PARTS):
        return "destructive"
    if low.endswith("/command") and isinstance(body, dict):
        if str(body.get("name", "")).lower() in DESTRUCTIVE_COMMANDS:
            return "destructive"
    if service == "seerr" and low.startswith("/settings"):
        return "destructive"
    if service == "qbittorrent" and low.endswith("/app/setpreferences"):
        prefs: Any = (params or {}).get("json")
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except ValueError:
                return "destructive"
        if isinstance(prefs, dict) and RISKY_QBIT_PREFS.intersection(prefs):
            return "destructive"
    if service == "qbittorrent" and low.endswith("/app/shutdown"):
        return "destructive"
    return "change"


def _phrase(service: str, method: str, path: str) -> str:
    return f"{service} {method.upper()} {path}"


def _gate(service: str, method: str, path: str, params: dict[str, Any],
          body: Any, confirm: bool, phrase: str) -> str | None:
    """Return a message if the call must not run yet, else None."""
    tier = classify(service, method, path, params, body)
    if tier == "read":
        return None
    shown = {"params": _redact(params), "body": _redact(body)}
    need = _phrase(service, method, path)
    if not confirm:
        return (
            f"NOT RUN. This call makes a change ({tier}).\n"
            f"Call: {need}\nDetails: {json.dumps(shown)[:1500]}\n"
            "Tell the user exactly what will change and ask for a clear yes. "
            "Then call again with confirm=true"
            + (f" and confirm_phrase=\"{need}\"." if tier == "destructive" else ".")
        )
    if tier == "destructive" and phrase != need:
        return (
            "NOT RUN. This call can delete data, restart an app, or lock someone out.\n"
            f"Call: {need}\nDetails: {json.dumps(shown)[:1500]}\n"
            f"Ask the user again. To run it, set confirm=true and confirm_phrase=\"{need}\"."
        )
    return None


# ---------------------------------------------------------------------------
# Settings and secrets
# ---------------------------------------------------------------------------

def _env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val and name.startswith("ARR_SEERR_"):
        # Old name from when this service was called Overseerr.
        val = os.environ.get("ARR_OVERSEERR_" + name[len("ARR_SEERR_"):], "").strip()
    return val


def _alias(service: str) -> str:
    """Accept the old name 'overseerr' for Seerr."""
    s = (service or "").strip().lower()
    return "seerr" if s == "overseerr" else s


def configured() -> list[str]:
    return [s for s in SERVICES if _env(f"ARR_{s.upper()}_URL")]


def _config(service: str) -> tuple[str, str]:
    """Return (base url, key). For qBittorrent the key is the password."""
    if service not in SERVICES:
        raise RuntimeError(f"Unknown service '{service}'. Use one of: {', '.join(SERVICES)}.")
    up = service.upper()
    url = _env(f"ARR_{up}_URL").rstrip("/")
    if not url:
        raise RuntimeError(
            f"{SERVICES[service]['label']} is not set up. Set ARR_{up}_URL and "
            + ("(optional) ARR_QBITTORRENT_USER and ARR_QBITTORRENT_PASS" if service == "qbittorrent" else f"ARR_{up}_KEY")
            + " in this tool's environment (see the README)."
        )
    if service == "qbittorrent":
        return url, _env("ARR_QBITTORRENT_PASS")
    key = _env(f"ARR_{up}_KEY")
    if not key:
        raise RuntimeError(f"Set ARR_{up}_KEY in this tool's environment (see the README).")
    return url, key


def _secrets() -> list[str]:
    vals = []
    for k, v in os.environ.items():
        if k.startswith("ARR_") and (k.endswith("_KEY") or k.endswith("_PASS")) and len(v) >= 4:
            vals.append(v)
    return vals


def _scrub(text: str) -> str:
    for s in _secrets():
        text = text.replace(s, "***")
    return text


def _redact(obj: Any) -> Any:
    """Hide secret values in anything shown to Claude."""
    if isinstance(obj, dict):
        out = {}
        field_name = str(obj.get("name", "")).lower() if "value" in obj else ""
        for k, v in obj.items():
            if str(k).lower() in SECRET_KEYS and v not in (None, ""):
                out[k] = "***"
            elif k == "value" and field_name in SECRET_FIELD_NAMES and v not in (None, ""):
                out[k] = "***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

_qbit_cookie: dict[str, str] = {}


def _ssl_ctx() -> ssl.SSLContext | None:
    if _env("ARR_VERIFY_TLS").lower() == "false":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _timeout() -> float:
    try:
        return float(_env("ARR_TIMEOUT") or 30)
    except ValueError:
        return 30.0


def _to_param(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value)
    return str(value)


def _send(method: str, url: str, headers: dict[str, str], data: bytes | None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=_timeout(), context=_ssl_ctx()) as resp:
            return {"status": resp.status, "ctype": resp.headers.get("Content-Type", ""),
                    "raw": resp.read(), "headers": resp.headers}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "ctype": exc.headers.get("Content-Type", "") if exc.headers else "",
                "raw": exc.read(), "headers": exc.headers}
    except urllib.error.URLError as exc:
        return {"status": 0, "error": _scrub(f"Could not reach the service: {exc.reason}")}
    except TimeoutError:
        return {"status": 0, "error": "The service did not answer in time."}


def _qbit_login(base: str) -> str | None:
    """Log in to qBittorrent. Returns an error text, or None when it worked."""
    user = _env("ARR_QBITTORRENT_USER")
    pw = _env("ARR_QBITTORRENT_PASS")
    if not user and not pw:
        # No login set: qBittorrent may skip passwords for trusted networks.
        _qbit_cookie[base] = ""
        return None
    if not user or not pw:
        return "Set both ARR_QBITTORRENT_USER and ARR_QBITTORRENT_PASS, or neither."
    data = urllib.parse.urlencode({"username": user, "password": pw}).encode()
    res = _send("POST", f"{base}/api/v2/auth/login",
                {"Referer": base, "Content-Type": "application/x-www-form-urlencoded"}, data)
    if res.get("error"):
        return res["error"]
    body = res["raw"].decode("utf-8", "replace").strip()
    if res["status"] == 403:
        return "qBittorrent banned this address for too many failed logins. Wait, then try again."
    if res["status"] != 200 or body.lower().startswith("fails"):
        return "qBittorrent refused the user name or password."
    for c in res["headers"].get_all("Set-Cookie") or []:
        if c.startswith("SID="):
            _qbit_cookie[base] = c.split(";", 1)[0]
            return None
    return "qBittorrent logged in but sent no session cookie."


def _norm_path(service: str, path: str) -> str:
    prefix = SERVICES[service]["prefix"]
    if prefix and path.startswith(prefix + "/"):
        path = path[len(prefix):]
    return path


def _path_error(path: str) -> str | None:
    if not path.startswith("/") or ".." in path or "?" in path or "://" in path or "#" in path:
        return "path must look like /series (no query string; put options in params)."
    low = path.lower()
    if any(p in low for p in BLOCKED_PARTS):
        return ("that path is not allowed here. Login, key and token calls would put a "
                "secret in the chat. Set up keys in the app's own web page.")
    return None


def _request(service: str, method: str, path: str,
             params: dict[str, Any] | None = None, body: Any = None) -> dict[str, Any]:
    """Call the service. Returns a dict with ok, and either data or error."""
    base, key = _config(service)
    svc = SERVICES[service]
    method = method.upper()
    query = {k: v for k, v in ((k, _to_param(v)) for k, v in (params or {}).items()) if v is not None}
    headers = {"Accept": "application/json"}
    data: bytes | None = None

    if svc["auth"] == "x-api-key":
        headers["X-Api-Key"] = key
    elif svc["auth"] == "jellyfin":
        headers["Authorization"] = f'MediaBrowser Token="{key}"'
    else:  # qbittorrent
        if base not in _qbit_cookie:
            err = _qbit_login(base)
            if err:
                return {"ok": False, "error": err}
        headers["Referer"] = base
        if method != "GET":
            data = urllib.parse.urlencode(query).encode()
            query = {}
            headers["Content-Type"] = "application/x-www-form-urlencoded"

    if body is not None and svc["auth"] != "cookie":
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    url = base + svc["prefix"] + path
    if query:
        url += "?" + urllib.parse.urlencode(query)

    def go() -> dict[str, Any]:
        h = dict(headers)
        if svc["auth"] == "cookie":
            h["Cookie"] = _qbit_cookie.get(base, "")
        return _send(method, url, h, data)

    res = go()
    if svc["auth"] == "cookie" and res.get("status") == 403:
        if not _env("ARR_QBITTORRENT_USER") and not _env("ARR_QBITTORRENT_PASS"):
            return {"ok": False, "error": "qBittorrent wants a login from this address. "
                    "Add this address to its no-password subnet list, or set ARR_QBITTORRENT_USER and ARR_QBITTORRENT_PASS."}
        _qbit_cookie.pop(base, None)
        if _qbit_login(base) is None:
            res = go()
    return _parse(service, res)


def _parse(service: str, res: dict[str, Any]) -> dict[str, Any]:
    label = SERVICES[service]["label"]
    if res.get("error"):
        return {"ok": False, "error": res["error"]}
    status = res["status"]
    raw: bytes = res["raw"]
    if status >= 400:
        text = _scrub(raw.decode("utf-8", "replace").strip()[:500])
        hint = ""
        if status in (401, 403):
            hint = " The key or login may be wrong."
        elif status == 404:
            hint = " Check the path and the service address."
        return {"ok": False, "error": f"HTTP {status} from {label}.{hint} {text}".strip()}
    if not raw.strip():
        return {"ok": True, "data": None, "status": status}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"ok": True, "data": f"(binary answer, {len(raw)} bytes, not shown)", "status": status}
    try:
        return {"ok": True, "data": _redact(json.loads(text)), "status": status}
    except ValueError:
        return {"ok": True, "data": _scrub(text.strip()), "status": status}


def _render(result: dict[str, Any], max_chars: int = 20000) -> str:
    if not result.get("ok"):
        return "ERROR: " + result.get("error", "unknown error")
    data = result.get("data")
    if data is None:
        return f"OK (HTTP {result.get('status', 200)}, no content)"
    text = data if isinstance(data, str) else json.dumps(data, indent=1, ensure_ascii=False)
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... cut at {max_chars} characters. Narrow the request or raise max_chars."
    return text


def _safe(fn):
    """Turn setup errors into plain text for Claude."""
    def wrap(*a, **k):
        try:
            return fn(*a, **k)
        except RuntimeError as exc:
            return "ERROR: " + str(exc)
    wrap.__name__ = fn.__name__
    wrap.__doc__ = fn.__doc__
    wrap.__wrapped__ = fn
    return wrap


def _get(service: str, path: str, **params: Any) -> dict[str, Any]:
    return _request(service, "GET", path, params)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def arr_services() -> str:
    """List which services are set up (Sonarr, Radarr, Prowlarr, Bazarr,
    Seerr, Jellyfin, qBittorrent, Tdarr). Shows addresses only, never keys."""
    on = set(configured())
    rows = []
    for name, svc in SERVICES.items():
        rows.append({
            "service": name,
            "set_up": name in on,
            "address": _env(f"ARR_{name.upper()}_URL") or None,
        })
    return json.dumps(rows, indent=1)


@mcp.tool()
@_safe
def arr_call(
    service: str,
    path: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    body: Any = None,
    confirm: bool = False,
    confirm_phrase: str = "",
    max_chars: int = 20000,
) -> str:
    """Call any API path on a service.

    service: sonarr, radarr, prowlarr, bazarr, seerr, jellyfin, qbittorrent or tdarr.
    path: the path after the API root, for example /series, /movie/12,
      /system/status, /torrents/info, /Items, /get-nodes. Do not add a query string.
    method: GET, POST, PUT, DELETE or PATCH.
    params: query options (for qBittorrent POST calls these are the form fields).
    body: JSON body for POST and PUT (not used by qBittorrent).

    API roots added for you: Sonarr and Radarr /api/v3, Prowlarr and Seerr
    /api/v1, Bazarr /api, qBittorrent and Tdarr /api/v2, Jellyfin none.

    Tdarr reads its database with POST /cruddb and a body like
    {"data": {"collection": "LibrarySettingsJSONDB", "mode": "getAll"}}.
    Those read modes run at once. Other modes need confirm=true.

    GET runs at once. Any change is NOT run until you set confirm=true, and you
    must first tell the user what will change and get a clear yes. Deleting,
    restarting, restoring a backup, host or security settings and password
    changes also need confirm_phrase set to exactly "<service> <METHOD> <path>",
    for example "sonarr DELETE /series/5". Never guess a body: read an existing
    item with GET first and send it back with changes.
    """
    service = _alias(service)
    method = method.upper().strip()
    if service not in SERVICES:
        return f"ERROR: service must be one of: {', '.join(SERVICES)}."
    if method not in METHODS:
        return "ERROR: method must be GET, POST, PUT, DELETE or PATCH."
    params = dict(params or {})
    path = _norm_path(service, path)
    err = _path_error(path)
    if err:
        return "ERROR: " + err
    if any(k.lower() in ("apikey", "api_key", "token", "x-api-key") for k in params):
        return "ERROR: do not pass a key or token. The tool adds it from its own settings."
    blocked = _gate(service, method, path, params, body, confirm, confirm_phrase)
    if blocked:
        return blocked
    return _render(_request(service, method, path, params, body), max_chars)


@mcp.tool()
@_safe
def arr_status(service: str = "") -> str:
    """Check that services answer. Shows version and health warnings.

    service: one name, or leave empty to check every service that is set up.
    """
    names = [service.lower().strip()] if service else configured()
    if not names:
        return "ERROR: no service is set up. See the README."
    out: dict[str, Any] = {}
    for name in names:
        if name not in SERVICES:
            out[name] = {"error": "unknown service"}
            continue
        if name not in configured():
            out[name] = {"error": "not set up"}
            continue
        out[name] = _probe(name)
    return json.dumps(out, indent=1, ensure_ascii=False)


def _probe(name: str) -> dict[str, Any]:
    def need(res: dict[str, Any]) -> Any:
        if not res.get("ok"):
            raise RuntimeError(res.get("error", "failed"))
        return res.get("data")

    try:
        if name in ("sonarr", "radarr", "prowlarr"):
            st = need(_get(name, "/system/status")) or {}
            health = need(_get(name, "/health")) or []
            return {"version": st.get("version"), "app": st.get("appName") or st.get("instanceName"),
                    "health": [f"{h.get('type')}: {h.get('message')}" for h in health] or "ok"}
        if name == "bazarr":
            st = (need(_get(name, "/system/status")) or {}).get("data", {})
            health = (need(_get(name, "/system/health")) or {}).get("data", [])
            return {"version": st.get("bazarr_version"), "health": health or "ok"}
        if name == "seerr":
            st = need(_get(name, "/status")) or {}
            return {"version": st.get("version"), "update_available": st.get("updateAvailable")}
        if name == "jellyfin":
            st = need(_get(name, "/System/Info")) or {}
            return {"server": st.get("ServerName"), "version": st.get("Version"),
                    "restart_pending": st.get("HasPendingRestart")}
        if name == "tdarr":
            st = need(_get(name, "/status")) or {}
            nodes = need(_get(name, "/get-nodes")) or {}
            return {"version": st.get("version"), "status": st.get("status"),
                    "nodes": [n.get("nodeName") for n in nodes.values()] if isinstance(nodes, dict) else nodes}
        ver = need(_get(name, "/app/version"))
        info = need(_get(name, "/transfer/info")) or {}
        return {"version": ver, "connection": info.get("connection_status"),
                "download_mb_s": round(info.get("dl_info_speed", 0) / 1048576, 2),
                "upload_mb_s": round(info.get("up_info_speed", 0) / 1048576, 2)}
    except RuntimeError as exc:
        return {"error": str(exc)}


@mcp.tool()
@_safe
def arr_queue(service: str = "") -> str:
    """Show what Sonarr and Radarr are downloading right now.

    service: sonarr, radarr, or empty for both.
    """
    names = [service.lower().strip()] if service else [s for s in ("sonarr", "radarr") if s in configured()]
    if not names:
        return "ERROR: Sonarr and Radarr are not set up."
    out: dict[str, Any] = {}
    for name in names:
        if name not in ("sonarr", "radarr"):
            out[name] = {"error": "queue works for sonarr and radarr"}
            continue
        extra = {"includeSeries": True, "includeEpisode": True} if name == "sonarr" else {"includeMovie": True}
        res = _get(name, "/queue", page=1, pageSize=50, **extra)
        if not res.get("ok"):
            out[name] = {"error": res.get("error")}
            continue
        rows = []
        for r in (res["data"] or {}).get("records", []):
            size, left = r.get("size") or 0, r.get("sizeleft") or 0
            media = (r.get("series") or r.get("movie") or {}).get("title")
            ep = r.get("episode") or {}
            rows.append({
                "title": r.get("title"),
                "media": media,
                "episode": f"S{ep.get('seasonNumber')}E{ep.get('episodeNumber')}" if ep else None,
                "status": r.get("status"),
                "state": r.get("trackedDownloadState"),
                "percent": round(100 * (size - left) / size, 1) if size else None,
                "time_left": r.get("timeleft"),
                "client": r.get("downloadClient"),
                "problem": r.get("errorMessage"),
            })
        out[name] = rows or "empty"
    return json.dumps(out, indent=1, ensure_ascii=False)


@mcp.tool()
@_safe
def arr_search(term: str, service: str = "sonarr") -> str:
    """Look up a show or movie by name. Nothing is added.

    service: sonarr (shows), radarr (movies) or seerr (both).
    Shows the id to use with arr_add. "in_library" is set when it already exists.
    """
    service = _alias(service)
    if service == "sonarr":
        res = _get("sonarr", "/series/lookup", term=term)
    elif service == "radarr":
        res = _get("radarr", "/movie/lookup", term=term)
    elif service == "seerr":
        res = _get("seerr", "/search", query=term, page=1)
    else:
        return "ERROR: service must be sonarr, radarr or seerr."
    if not res.get("ok"):
        return _render(res)
    data = res["data"]
    items = data.get("results", []) if isinstance(data, dict) else data
    rows = []
    for it in (items or [])[:10]:
        if service == "seerr":
            media = it.get("mediaInfo") or {}
            rows.append({"type": it.get("mediaType"), "tmdbId": it.get("id"),
                         "title": it.get("title") or it.get("name"),
                         "date": it.get("releaseDate") or it.get("firstAirDate"),
                         "library_status": media.get("status")})
        else:
            rows.append({"title": it.get("title"), "year": it.get("year"),
                         "tvdbId": it.get("tvdbId"), "tmdbId": it.get("tmdbId"),
                         "status": it.get("status"),
                         "in_library": bool(it.get("id")), "library_id": it.get("id")})
    return json.dumps(rows, indent=1, ensure_ascii=False) if rows else "No match."


@mcp.tool()
@_safe
def arr_add(
    service: str, external_id: int, quality_profile: str = "", root_folder: str = "",
    search_now: bool = True, confirm: bool = False,
) -> str:
    """Add a show to Sonarr or a movie to Radarr.

    service: sonarr or radarr.
    external_id: the TVDB id for a show, or the TMDB id for a movie (from arr_search).
    quality_profile: profile name. If empty and there is only one, it is used.
    root_folder: folder path. If empty and there is only one, it is used.
    search_now: start looking for downloads right away.
    First call without confirm to see what will be added. Ask the user,
    then call again with confirm=true.
    """
    service = service.lower().strip()
    if service == "sonarr":
        lookup, endpoint, term = "/series/lookup", "/series", f"tvdb:{external_id}"
    elif service == "radarr":
        lookup, endpoint, term = "/movie/lookup", "/movie", f"tmdb:{external_id}"
    else:
        return "ERROR: service must be sonarr or radarr."
    found = _get(service, lookup, term=term)
    if not found.get("ok"):
        return _render(found)
    items = found["data"] or []
    if not items:
        return "ERROR: nothing found with that id."
    item = items[0]
    if item.get("id"):
        return f"Already in the library: {item.get('title')} ({item.get('year')}), id {item['id']}."
    roots = (_get(service, "/rootfolder").get("data") or [])
    profiles = (_get(service, "/qualityprofile").get("data") or [])
    if root_folder:
        root = next((r for r in roots if r.get("path", "").rstrip("/\\") == root_folder.rstrip("/\\")), None)
    else:
        root = roots[0] if len(roots) == 1 else None
    if quality_profile:
        prof = next((p for p in profiles if p.get("name", "").lower() == quality_profile.lower()), None)
    else:
        prof = profiles[0] if len(profiles) == 1 else None
    if not root or not prof:
        return json.dumps({
            "need": "choose root_folder and quality_profile",
            "root_folders": [r.get("path") for r in roots],
            "quality_profiles": [p.get("name") for p in profiles],
        }, indent=1)
    body = dict(item)
    body.update({"rootFolderPath": root["path"], "qualityProfileId": prof["id"], "monitored": True})
    if service == "sonarr":
        body["seasonFolder"] = True
        body["addOptions"] = {"monitor": "all", "searchForMissingEpisodes": search_now}
    else:
        body["addOptions"] = {"monitor": "movieOnly", "searchForMovie": search_now}
    summary = {"add": f"{item.get('title')} ({item.get('year')})", "to": service,
               "folder": root["path"], "quality": prof["name"], "search_now": search_now}
    blocked = _gate(service, "POST", endpoint, {}, summary, confirm, "")
    if blocked:
        return blocked
    res = _request(service, "POST", endpoint, {}, body)
    if not res.get("ok"):
        return _render(res)
    return json.dumps({"added": summary["add"], "id": (res["data"] or {}).get("id")}, indent=1)


@mcp.tool()
@_safe
def arr_calendar(service: str = "sonarr", days: int = 7) -> str:
    """Upcoming episodes (sonarr) or movie releases (radarr) for the next days."""
    service = service.lower().strip()
    if service not in ("sonarr", "radarr"):
        return "ERROR: service must be sonarr or radarr."
    start = date.today()
    end = start + timedelta(days=max(1, min(days, 60)))
    extra = {"includeSeries": True} if service == "sonarr" else {}
    res = _get(service, "/calendar", start=start.isoformat(), end=end.isoformat(),
               unmonitored=False, **extra)
    if not res.get("ok"):
        return _render(res)
    rows = []
    for e in res["data"] or []:
        if service == "sonarr":
            rows.append({"when": e.get("airDateUtc"), "show": (e.get("series") or {}).get("title"),
                         "episode": f"S{e.get('seasonNumber')}E{e.get('episodeNumber')}",
                         "title": e.get("title"), "downloaded": e.get("hasFile")})
        else:
            rows.append({"movie": e.get("title"), "year": e.get("year"),
                         "cinemas": e.get("inCinemas"), "digital": e.get("digitalRelease"),
                         "physical": e.get("physicalRelease"), "downloaded": e.get("hasFile")})
    return json.dumps(rows, indent=1, ensure_ascii=False) if rows else "Nothing coming up."


@mcp.tool()
@_safe
def arr_downloads(filter: str = "all", limit: int = 30) -> str:
    """Show qBittorrent torrents.

    filter: all, downloading, seeding, completed, paused, active, stalled, errored.
    """
    res = _get("qbittorrent", "/torrents/info", filter=filter, sort="added_on",
               reverse=True, limit=max(1, min(limit, 200)))
    if not res.get("ok"):
        return _render(res)
    rows = []
    for t in res["data"] or []:
        rows.append({
            "name": t.get("name"), "state": t.get("state"),
            "percent": round(100 * (t.get("progress") or 0), 1),
            "down_mb_s": round((t.get("dlspeed") or 0) / 1048576, 2),
            "up_mb_s": round((t.get("upspeed") or 0) / 1048576, 2),
            "eta_seconds": t.get("eta"), "category": t.get("category"),
            "size_gb": round((t.get("size") or 0) / 1073741824, 2),
            "hash": t.get("hash"),
        })
    return json.dumps(rows, indent=1, ensure_ascii=False) if rows else "No torrents."


REQUEST_STATUS = {1: "pending", 2: "approved", 3: "declined", 4: "failed", 5: "completed"}


@mcp.tool()
@_safe
def arr_requests(filter: str = "pending", take: int = 20) -> str:
    """Show Seerr requests.

    filter: pending, approved, available, processing, unavailable, failed, all.
    To approve or decline, use arr_call with POST /request/<id>/approve
    (or /decline) after the user says yes.
    """
    res = _get("seerr", "/request", take=max(1, min(take, 100)), skip=0,
               filter=filter, sort="added")
    if not res.get("ok"):
        return _render(res)
    rows = []
    for r in (res["data"] or {}).get("results", []):
        media = r.get("media") or {}
        rows.append({
            "id": r.get("id"), "status": REQUEST_STATUS.get(r.get("status"), r.get("status")),
            "type": r.get("type"), "tmdbId": media.get("tmdbId"),
            "by": (r.get("requestedBy") or {}).get("displayName"),
            "created": r.get("createdAt"),
        })
    return json.dumps(rows, indent=1, ensure_ascii=False) if rows else "No requests."


@mcp.tool()
@_safe
def tdarr_summary(show_failed: int = 10) -> str:
    """Show what Tdarr is doing: nodes, workers, and how many files are in each state.

    show_failed: how many failed file names to list (0 to 50).
    """
    nodes = _get("tdarr", "/get-nodes")
    if not nodes.get("ok"):
        return _render(nodes)
    files = _request("tdarr", "POST", "/cruddb",
                     body={"data": {"collection": "FileJSONDB", "mode": "getAll"}})
    if not files.get("ok"):
        return _render(files)
    node_rows = []
    for nid, n in (nodes["data"] or {}).items():
        node_rows.append({
            "name": n.get("nodeName"), "paused": n.get("nodePaused"),
            "worker_limits": n.get("workerLimits"),
            "workers_busy": len(n.get("workers") or {}),
        })
    counts: dict[str, int] = {}
    failed: list[str] = []
    for f in files["data"] or []:
        state = str(f.get("TranscodeDecisionMaker") or "unknown")
        counts[state] = counts.get(state, 0) + 1
        if "error" in state.lower() or "fail" in state.lower():
            failed.append(str(f.get("file")))
    limit = max(0, min(show_failed, 50))
    out = {"nodes": node_rows, "files_by_state": counts, "total_files": sum(counts.values()),
           "failed_files": failed[:limit], "failed_count": len(failed)}
    return json.dumps(out, indent=1, ensure_ascii=False)


@mcp.tool()
@_safe
def jellyfin_now_playing() -> str:
    """Show who is watching on Jellyfin right now, and on which device."""
    res = _get("jellyfin", "/Sessions", activeWithinSeconds=960)
    if not res.get("ok"):
        return _render(res)
    rows = []
    for s in res["data"] or []:
        item = s.get("NowPlayingItem")
        rows.append({
            "user": s.get("UserName"), "device": s.get("DeviceName"), "app": s.get("Client"),
            "playing": item.get("Name") if item else None,
            "type": item.get("Type") if item else None,
            "paused": (s.get("PlayState") or {}).get("IsPaused") if item else None,
        })
    return json.dumps(rows, indent=1, ensure_ascii=False) if rows else "No active sessions."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
