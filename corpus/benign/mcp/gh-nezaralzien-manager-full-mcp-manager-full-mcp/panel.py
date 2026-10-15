"""Local control panel: tick boxes for every resource, and the business list.

Binds to 127.0.0.1 only and requires a per-run token on every API call, so a
random page in the browser cannot drive it. Access tokens are typed here, never
in chat, and are stored 0600 in the config home.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from manager_full_mcp.catalog import GROUP_LABELS, GROUP_ORDER, OPS, build_catalog
from manager_full_mcp.config import (
    Business,
    load_cached_catalog,
    load_registry,
    save_catalog,
    save_registry,
    slugify,
)
from manager_full_mcp.permissions import Policy, coerce_mode, load_policy, save_policy

_HTML = (Path(__file__).resolve().parent / "data" / "panel.html").read_text(
    encoding="utf-8"
)


def _catalog_for(business: Business, *, refresh: bool = False):
    catalog = None if refresh else load_cached_catalog(business.id, max_age=-1)
    if catalog is not None:
        return catalog
    base = business.api_url.rstrip("/")
    with httpx.Client(
        headers={"X-API-KEY": business.api_key, "Accept": "application/json"},
        timeout=90.0,
        follow_redirects=True,
    ) as client:
        # The OpenAPI document lives at the base URL itself, without a trailing slash.
        response = client.get(base)
        response.raise_for_status()
        doc = response.json()
    catalog = build_catalog(doc, built_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
    save_catalog(business.id, catalog)
    return catalog


def _state(active_ref: str | None = None) -> dict[str, Any]:
    registry = load_registry()
    businesses = [b.public() for b in registry.businesses]
    active = registry.resolve(active_ref) or (
        registry.businesses[0] if registry.businesses else None
    )
    payload: dict[str, Any] = {
        "businesses": businesses,
        "active": active.id if active else None,
        "groups": [],
        "matrix": {},
        "summary": None,
        "catalog_ready": False,
    }
    if active is None:
        return payload
    try:
        catalog = _catalog_for(active)
    except Exception as exc:  # unreachable business: still show the business list
        payload["error"] = (
            f"Could not load the resource list for '{active.name}': {exc}"
        )
        return payload
    policy = load_policy(active.id, catalog)
    grouped = catalog.by_group()
    payload["groups"] = [
        {
            "id": group,
            "label": GROUP_LABELS.get(group, group),
            "resources": [
                {
                    "name": r.name,
                    "label": r.label,
                    "ops": r.ops,
                    "locked": r.locked,
                    "risk": r.risk,
                    "risk_note": r.risk_note,
                    "description": r.description,
                    "doc_url": r.doc_url,
                    "list_path": r.list_path,
                    "form_path": r.form_path,
                }
                for r in grouped[group]
            ],
        }
        for group in GROUP_ORDER
        if group in grouped
    ]
    payload["matrix"] = policy.matrix(catalog)
    payload["summary"] = policy.summary(catalog)
    payload["policy"] = {
        "source": policy.source,
        "raw_read": policy.raw_read,
        "raw_write": policy.raw_write,
        "read_only_mode": policy.read_only,
        "updated_at": policy.updated_at,
    }
    payload["catalog_ready"] = True
    payload["api_version"] = catalog.api_version
    return payload


def _save_permissions(body: dict[str, Any]) -> dict[str, Any]:
    business_id = body.get("business")
    registry = load_registry()
    business = registry.get(business_id or "")
    if business is None:
        return {"ok": False, "error": f"Unknown business '{business_id}'."}
    catalog = _catalog_for(business)
    matrix = body.get("matrix") or {}
    cleaned = {
        name: {op: coerce_mode(grants.get(op)) for op in OPS}
        for name, grants in matrix.items()
        if name in catalog.resources and isinstance(grants, dict)
    }
    policy = Policy(
        business_id=business.id,
        resources=cleaned,
        raw_read=bool(body.get("raw_read", True)),
        raw_write=bool(body.get("raw_write", False)),
    )
    save_policy(policy)
    reloaded = load_policy(business.id, catalog)
    return {"ok": True, "summary": reloaded.summary(catalog)}


def _save_business(body: dict[str, Any]) -> dict[str, Any]:
    name = (body.get("name") or "").strip()
    api_url = (body.get("api_url") or "").strip().rstrip("/")
    api_key = (body.get("api_key") or "").strip()
    business_id = (body.get("id") or "").strip() or slugify(name)
    if not name or not api_url:
        return {"ok": False, "error": "Name and API URL are required."}
    registry = load_registry()
    existing = registry.get(business_id)
    if existing is not None and not api_key:
        api_key = existing.api_key  # editing without retyping the token
    if not api_key:
        return {"ok": False, "error": "An access token is required."}
    business = Business(
        id=business_id,
        name=name,
        api_url=api_url,
        api_key=api_key,
        enabled=bool(body.get("enabled", True)),
        note=(body.get("note") or "").strip(),
    )
    try:
        catalog = _catalog_for(business, refresh=True)
    except Exception as exc:
        return {
            "ok": False,
            "error": (
                f"Could not reach Manager at {api_url}: {exc}. "
                "Check the URL (it usually ends with /api2) and the access token."
            ),
        }
    registry.upsert(business)
    save_registry(registry)
    return {
        "ok": True,
        "business": business.public(),
        "resources": len(catalog.resources),
        "api_version": catalog.api_version,
    }


def _delete_business(body: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry()
    removed = registry.remove((body.get("id") or "").strip())
    if removed:
        save_registry(registry)
    return {"ok": removed}


def _refresh_catalog(body: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry()
    business = registry.get((body.get("id") or "").strip())
    if business is None:
        return {"ok": False, "error": "Unknown business."}
    try:
        catalog = _catalog_for(business, refresh=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "resources": len(catalog.resources), "api_version": catalog.api_version}


class _Handler(BaseHTTPRequestHandler):
    server_version = "ManagerFullPanel/1.0"
    token = ""

    def log_message(self, *args: Any) -> None:  # keep stdio clean for MCP
        return

    def _authorized(self, query: dict[str, list[str]]) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in {"127.0.0.1", "localhost"}:
            return False
        supplied = (query.get("token") or [""])[0] or self.headers.get("X-Panel-Token", "")
        return secrets.compare_digest(supplied, self.token)

    def _send(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path in {"/", "/index.html"}:
            if not self._authorized(query):
                self.send_error(403, "Open the panel through the link Claude gave you.")
                return
            body = _HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/state":
            if not self._authorized(query):
                self.send_error(403, "Invalid token")
                return
            active = (query.get("business") or [None])[0]
            self._send(_state(active))
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if not self._authorized(query):
            self.send_error(403, "Invalid token")
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send({"ok": False, "error": "Malformed JSON."}, 400)
            return
        routes = {
            "/api/permissions": _save_permissions,
            "/api/business": _save_business,
            "/api/business/delete": _delete_business,
            "/api/business/refresh": _refresh_catalog,
        }
        handler = routes.get(parsed.path)
        if handler is None:
            self.send_error(404)
            return
        try:
            self._send(handler(body))
        except Exception as exc:
            self._send({"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}, 500)


_SERVER: ThreadingHTTPServer | None = None
_URL = ""


def start_panel(port: int = 0, *, open_browser: bool = False) -> str:
    """Start (or reuse) the panel and return its tokenised URL."""
    global _SERVER, _URL
    if _SERVER is not None:
        if open_browser:
            webbrowser.open(_URL)
        return _URL
    _Handler.token = secrets.token_urlsafe(24)
    _SERVER = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=_SERVER.serve_forever, daemon=True, name="panel")
    thread.start()
    _URL = f"http://127.0.0.1:{_SERVER.server_address[1]}/?token={_Handler.token}"
    if open_browser:
        webbrowser.open(_URL)
    return _URL


def main() -> None:
    """Standalone launcher: `manager-full-panel`."""
    import argparse

    parser = argparse.ArgumentParser(description="Manager.io MCP permissions panel")
    parser.add_argument("--port", type=int, default=0, help="port (default: random free)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args()
    url = start_panel(args.port, open_browser=not args.no_browser)
    print(f"Manager.io MCP control panel: {url}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
