"""One-purpose loopback HTTP intermediary for the frozen transport cells."""

from __future__ import annotations

import base64
import http.client
import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock


class ProxyHandler(BaseHTTPRequestHandler):
    server: ProxyServer

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_POST(self) -> None:
        if self.path != "/mcp":
            self.send_error(404)
            return
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.record("client_request", raw)
        outbound = raw
        frame = json.loads(raw)
        params = frame.get("params", {})
        continuation = params.get("name") == "create_guarded_issue" and "inputResponses" in params
        if continuation and self.server.mode == "strip":
            params.pop("requestState", None)
            outbound = json.dumps(frame, separators=(",", ":")).encode()
        self.server.record("upstream_request", outbound)
        upstream = http.client.HTTPConnection("127.0.0.1", self.server.upstream_port, timeout=8)
        try:
            upstream.request(
                "POST",
                "/mcp",
                body=outbound,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "MCP-Protocol-Version": "2026-07-28",
                    "Mcp-Method": self.headers.get("Mcp-Method", ""),
                    "Mcp-Name": self.headers.get("Mcp-Name", ""),
                    "Authorization": self.headers.get("Authorization", ""),
                },
            )
            reply = upstream.getresponse()
            content = reply.read()
            status = reply.status
        finally:
            upstream.close()
        self.server.record("upstream_response", content, status=status)
        if continuation and self.server.mode == "drop":
            self.server.record("dropped_response", b"")
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if continuation and self.server.mode == "delay":
            time.sleep(0.5)
            self.server.record("delayed_response", content, status=status)
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            self.server.record("client_response", content, status=status)
        except (BrokenPipeError, ConnectionResetError):
            self.server.record("client_disconnected", b"")


class ProxyServer(ThreadingHTTPServer):
    def __init__(self, port: int, upstream_port: int, mode: str, log_path: Path) -> None:
        if mode not in {"drop", "delay", "strip"}:
            raise ValueError("unsupported proxy mode")
        super().__init__(("127.0.0.1", port), ProxyHandler)
        self.upstream_port = upstream_port
        self.mode = mode
        self.log_path = log_path
        self._lock = Lock()

    def record(self, event: str, value: bytes, *, status: int | None = None) -> None:
        entry: dict[str, str | int] = {
            "event": event,
            "bodyBase64": base64.b64encode(value).decode("ascii"),
        }
        if status is not None:
            entry["status"] = status
        with self._lock, self.log_path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(entry, sort_keys=True) + "\n")


def main() -> None:
    port = int(os.environ["PROXY_PORT"])
    upstream_port = int(os.environ["PROXY_UPSTREAM_PORT"])
    if not all(1 <= item <= 65535 for item in (port, upstream_port)):
        raise SystemExit("ports must be assigned loopback ports")
    log_path = Path(os.environ["PROXY_LOG"])
    with ProxyServer(port, upstream_port, os.environ["PROXY_MODE"], log_path) as server:
        server.serve_forever(poll_interval=0.1)


if __name__ == "__main__":
    main()
