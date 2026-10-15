"""Loopback-only UI/API. No document persistence or remote inference."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
from .demo import DEMOS

WEB = Path(__file__).parent / "web"


def handler_for(engine):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # do not log passage contents or URLs

        def send(self, status, body, mime="application/json"):
            data = json.dumps(body, ensure_ascii=False).encode() if mime == "application/json" else body
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "Loopback Host required."})
            path = urlsplit(self.path).path
            if path == "/api/status":
                return self.send(200, {"backend": engine.backend.identity, "version": "0.1.0", "network_inference": False})
            if path == "/api/demos":
                return self.send(200, DEMOS)
            assets = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path in assets:
                name, mime = assets[path]
                return self.send(200, (WEB / name).read_bytes(), mime)
            return self.send(404, {"error": "Not found."})

        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not self.valid_host() or (origin is not None and origin not in allowed):
                return self.send(403, {"error": "Only same-origin loopback requests are accepted."})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send(415, {"error": "Use application/json."})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    return self.send(413, {"error": "Request must be 1–65,536 bytes."})
                payload = json.loads(self.rfile.read(size))
                if self.path == "/api/decide":
                    result = engine.decide(payload)
                elif self.path == "/api/evidence":
                    result = engine.evidence(payload)
                else:
                    return self.send(404, {"error": "Not found."})
                return self.send(200, result)
            except (ValueError, TypeError, KeyError) as exc:
                return self.send(400, {"error": str(exc)})
            except Exception:
                return self.send(500, {"error": "Local inference failed. Check model installation and available memory."})
    return Handler


def serve(engine, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(engine))
    print(f"Evidence Gate: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
