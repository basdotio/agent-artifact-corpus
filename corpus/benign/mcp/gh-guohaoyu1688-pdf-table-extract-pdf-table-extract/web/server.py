"""Loopback HTTP review service with same-origin mutation protection."""

import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..core.errors import PDFError, failure, success
from ..core.extract import extract_tables, inspect_pdf, render_page


def make_server(
    host: str = "127.0.0.1", port: int = 8766, pdf: str | None = None, quiet: bool = False
) -> ThreadingHTTPServer:
    token = secrets.token_urlsafe(32)
    assets = Path(__file__).parent

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            if not quiet:
                super().log_message(format, *args)

        def valid_host(self) -> bool:
            allowed = {f"{host}:{self.server.server_port}"}
            if host in {"127.0.0.1", "localhost"}:
                allowed |= {
                    f"localhost:{self.server.server_port}",
                    f"127.0.0.1:{self.server.server_port}",
                }
            return self.headers.get("Host") in allowed

        def send(self, status: int, data: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; "
                "style-src 'self'; img-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(data)

        def json(self, status: int, data: dict) -> None:
            self.send(
                status,
                json.dumps(data, ensure_ascii=False).encode(),
                "application/json; charset=utf-8",
            )

        def do_GET(self) -> None:
            if not self.valid_host():
                self.json(403, failure(PDFError("forbidden", "Unexpected Host header")))
                return
            route = urlparse(self.path)
            try:
                if route.path == "/api/config":
                    self.json(
                        200,
                        success({"csrf": token, "pdf": str(Path(pdf).resolve()) if pdf else ""}),
                    )
                elif route.path == "/api/render":
                    query = parse_qs(route.query)
                    self.send(
                        200,
                        render_page(query["path"][0], int(query.get("page", [1])[0])),
                        "image/png",
                    )
                elif route.path in {"/", "/app.js", "/style.css"}:
                    name = "index.html" if route.path == "/" else route.path[1:]
                    mime = {
                        "index.html": "text/html; charset=utf-8",
                        "app.js": "application/javascript",
                        "style.css": "text/css",
                    }
                    self.send(200, (assets / name).read_bytes(), mime[name])
                else:
                    self.json(404, failure(PDFError("not_found", "Route not found", 3)))
            except (PDFError, OSError, ValueError, KeyError) as exc:
                self.json(
                    400,
                    failure(
                        exc if isinstance(exc, PDFError) else PDFError("invalid_input", str(exc), 2)
                    ),
                )

        def do_POST(self) -> None:
            if (
                not self.valid_host()
                or self.headers.get("X-PTE-CSRF") != token
                or self.headers.get("Content-Type", "").split(";")[0] != "application/json"
            ):
                self.json(403, failure(PDFError("forbidden", "Missing same-origin request token")))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise PDFError("invalid_input", "Body must be between 1 byte and 1 MiB", 2)
                payload = json.loads(self.rfile.read(length))
                if self.path == "/api/inspect":
                    result = inspect_pdf(payload["path"])
                elif self.path == "/api/extract":
                    result = extract_tables(**payload)
                else:
                    self.json(404, failure(PDFError("not_found", "Route not found", 3)))
                    return
                self.json(200, success(result))
            except (PDFError, OSError, ValueError, KeyError, TypeError) as exc:
                self.json(
                    400,
                    failure(
                        exc if isinstance(exc, PDFError) else PDFError("invalid_input", str(exc), 2)
                    ),
                )

    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str, port: int, pdf: str | None, quiet: bool) -> None:
    server = make_server(host, port, pdf, quiet)
    if not quiet:
        print(f"Review UI: http://{host}:{server.server_port}", file=sys.stderr)
    try:
        server.serve_forever()
    finally:
        server.server_close()
