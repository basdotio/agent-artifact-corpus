"""Local human dashboard. Bound to loopback, no external assets or model calls."""
import json
import base64
import sys
import time
import uuid
import zipfile
import webbrowser
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

from .store import Store, checked_id
from .importer import parse_import, preview_import, commit_import
from .backup import create_backup, restore_backup
from .conversations import list_conversations, list_sources, analysis_pack


def snapshot(store, restricted=False, query="", kind=""):
    if len(query) > 500:
        raise ValueError("Query too long")
    with store.locked():
        records = [r for r in store._all() if restricted or r["sensitivity"] != "restricted"]
        from .governance import effective
        all_rows = {r["id"]: r for r in store._all()}
        records = [{**r, "effective_state": effective(store, r, all_rows)} for r in records]
        proposals = []
        for path in sorted(store._safe(store.meta / "proposals").glob("*.json")):
            p = json.loads(store._safe(path).read_text(encoding="utf-8"))
            if not restricted and p["record"]["sensitivity"] == "restricted":
                continue
            if p["state"] == "pending":
                before = None
                if p["expected_revision"] is not None:
                    try:
                        before = store._get(p["record"]["id"])
                    except ValueError as exc:
                        if str(exc) != "Record not found":
                            raise
                if before and not restricted and before["sensitivity"] == "restricted":
                    continue
                proposals.append({**p, "before": before})
        matching = [r for r in records if (not kind or r["kind"] == kind)
                    and query.casefold() in (r["title"] + " " + r["content"] + " " + " ".join(r["tags"])).casefold()]
        matching.sort(key=lambda r: r["updated_at"], reverse=True)
        visible_ids = {r["id"] for r in records}
        edges = [{"source": source, "target": r["id"]} for r in records
                 for source in r.get("source_ids", []) if source in visible_ids and source != r["id"]]
        degrees = Counter(e[side] for e in edges for side in ("source", "target"))
        graph_records = sorted(records, key=lambda r: (degrees[r["id"]], r["updated_at"]), reverse=True)[:60]
        graph_ids = {r["id"] for r in graph_records}
        fields = ("id", "title", "kind", "status", "revision", "created_at", "updated_at", "tags", "sensitivity")
        return {
            "total": len(records), "confirmed": sum(r["status"] == "confirmed" for r in records),
            "pending": len(proposals), "kinds": dict(Counter(r["kind"] for r in records)),
            "created_dates": [r.get("imported_at", r["created_at"]) for r in records],
            "records": [{k: r[k] for k in fields} | {"excerpt": r["content"][:180],
                        "claim_type": r.get("claim_type"), "conversation": r.get("conversation"),
                        "memory": r.get("memory", {}), "effective_state": r["effective_state"]} for r in matching[:200]],
            "matching": len(matching), "proposals": proposals, "restricted": restricted,
            "graph": {"nodes": [{k: r[k] for k in ("id", "title", "kind")} for r in graph_records],
                      "edges": [e for e in edges if e["source"] in graph_ids and e["target"] in graph_ids],
                      "total_nodes": len(records)},
        }


def history(store, record_id, restricted=False):
    with store.locked():
        current = store._get(record_id)
        store._visible(current, restricted)
        directory = store._safe(store.meta / "history" / checked_id(record_id))
        records = [store.decode(store._safe(p).read_text(encoding="utf-8")) for p in directory.glob("*.md")]
        return sorted([r for r in records if restricted or r["sensitivity"] != "restricted"], key=lambda r: r["revision"], reverse=True)


def make_server(vault, port=8765):
    store = Store(vault)
    if not store.meta.is_dir():
        raise ValueError("Run init first")
    if not 0 <= port <= 65535:
        raise ValueError("Invalid port")
    previews = {}
    preview_lock = threading.RLock()
    preview_epoch = 0

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            # Do not log personal record IDs, query terms or contents.
            pass

        def send(self, status, body, mime="application/json; charset=utf-8", filename=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            port = self.server.server_port
            return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

        def do_GET(self):
            origin = self.headers.get("Origin")
            if not self.valid_host() or (origin and origin != "http://" + self.headers.get("Host", "")):
                self.send(403, {"error": "Invalid local host"})
                return
            try:
                url = urlsplit(self.path)
                params = parse_qs(url.query)
                restricted = params.get("restricted", ["0"])[0] == "1"
                assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/governance.js": ("governance.js", "text/javascript"), "/features.js": ("features.js", "text/javascript"), "/memory.js": ("memory.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
                if url.path in assets:
                    name, mime = assets[url.path]
                    self.send(200, files("personal_os").joinpath("static", name).read_bytes(), mime + "; charset=utf-8")
                elif url.path == "/api/snapshot":
                    self.send(200, snapshot(store, restricted, params.get("q", [""])[0], params.get("kind", [""])[0]))
                elif url.path == "/api/record":
                    self.send(200, store.get(params.get("id", [""])[0], restricted, include_inactive=True))
                elif url.path == "/api/deletion-preview":
                    self.send(200, store.deletion_preview(params.get("id", [""])[0], restricted))
                elif url.path == "/api/history":
                    self.send(200, history(store, params.get("id", [""])[0], restricted))
                elif url.path == "/api/conversations":
                    self.send(200, list_conversations(store, restricted))
                elif url.path == "/api/extraction-sources":
                    self.send(200, list_sources(store, restricted))
                elif url.path == "/api/config":
                    args = ["-m", "personal_os.cli", "--vault", str(store.root), "serve"]
                    self.send(200, {"mcpServers": {"personal-os": {"command": sys.executable, "args": args}}})
                else:
                    self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, OSError) as exc:
                self.send(400, {"error": str(exc)})

        def do_POST(self):
            nonlocal preview_epoch
            origin = self.headers.get("Origin")
            if (not self.valid_host() or origin != "http://" + self.headers.get("Host", "")
                or self.headers.get("X-Personal-OS") != "dashboard"
                or self.headers.get("Content-Type", "").split(";")[0] != "application/json"):
                self.send(403, {"error": "Only this local dashboard may submit changes"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                maximum = 48 * 1024 * 1024 if self.path == "/api/restore-backup" else 16 * 1024 * 1024 if self.path == "/api/import-preview" else 500_000
                if not 1 <= length <= maximum:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Request body must be a JSON object")
                if self.path == "/api/review":
                    if data.get("action") not in ("approve", "reject"):
                        raise ValueError("Invalid review action")
                    result = store.review(data["id"], data["action"] == "approve", data.get("resolution"), data.get("scope"))
                elif self.path == "/api/memory":
                    result = store.update_memory(data["id"], data["revision"], data["memory"], data.get("restricted") is True)
                elif self.path == "/api/delete":
                    if not isinstance(data.get("impact"), str):
                        raise ValueError("Preview deletion first")
                    with preview_lock:
                        result = store.delete(data["id"], data["revision"], data["mode"], data["impact"], data.get("restricted") is True)
                        previews.clear()
                        preview_epoch += 1
                elif self.path == "/api/capture":
                    result = store.capture(data["title"], data["content"], data.get("kind", "thought"),
                                           data.get("sensitivity", "private"), source="local dashboard / user input", memory=data.get("memory"))
                elif self.path == "/api/analysis-pack":
                    result = analysis_pack(store, data["record_ids"], data["purpose"], data.get("restricted") is True)
                elif self.path == "/api/import-preview":
                    with preview_lock:
                        epoch = preview_epoch
                    if "data" in data:
                        from .documents import parse_document
                        items = parse_document(data["filename"], base64.b64decode(data["data"], validate=True))
                    else:
                        items = parse_import(data["filename"], data["text"])
                    # Preview stays only in process memory, expires after 30 minutes.
                    with preview_lock:
                        if epoch != preview_epoch:
                            raise ValueError("Deletion invalidated this preview; choose the file again")
                        expired = [key for key, value in previews.items() if time.monotonic() - value[0] > 1800]
                        for key in expired:
                            previews.pop(key, None)
                        if len(previews) >= 4:
                            previews.pop(next(iter(previews)))
                        token = uuid.uuid4().hex
                        previews[token] = (time.monotonic(), items)
                    result = {"preview_id": token, "items": preview_import(store, items)}
                elif self.path == "/api/import-commit":
                    with preview_lock:
                        preview = previews.get(data["preview_id"])
                        if not preview or time.monotonic() - preview[0] > 1800:
                            raise ValueError("Preview expired; choose the file again")
                        result = commit_import(store, preview[1], data["keys"], data.get("sensitivity", "restricted"))
                elif self.path == "/api/backup":
                    self.send(200, create_backup(store), "application/zip", "personal-os-backup.zip")
                    return
                elif self.path == "/api/restore-backup":
                    encoded = data["data"]
                    if not isinstance(encoded, str):
                        raise ValueError("Invalid backup data")
                    result = restore_backup(store, base64.b64decode(encoded, validate=True))
                else:
                    self.send(404, {"error": "Not found"})
                    return
                self.send(200, result)
            except (ValueError, KeyError, OSError, TypeError, zipfile.BadZipFile, RuntimeError) as exc:
                self.send(400, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def run(vault, port, open_browser=True):
    server = make_server(vault, port)
    address = f"http://127.0.0.1:{server.server_port}"
    print(f"Personal OS dashboard: {address}\nPress Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
