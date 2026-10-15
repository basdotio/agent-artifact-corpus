#!/usr/bin/env python3
"""A fake server for the error paths (SKILL.md R10: never break the real server to see an error).

Answers every request with what you tell it, and prints each request it got — method, path, and the
body — so the run report can show what the app actually sent.

    fake_server.py --port 18099 --status 500
    fake_server.py --port 18099 --status 401 --body '{"ok":false,"message":"unauthorized"}'
    fake_server.py --port 18099 --status 502 --body '<html>Bad gateway</html>' --type text/html
    fake_server.py --port 18099 --status 200 --delay 40          # a server that answers too late
    fake_server.py --port 18099 --routes routes.json --status 404  # {"GET /api/items": {"status": 200, "body": "[]"}}
                                                                   # --status is what every OTHER path gets

    fake_server.py --port 18099 --status 200 --body '{"ok":true}' --header "Set-Cookie: sessionid=QA_fake"

Reaching it from an emulator: `adb reverse tcp:<port> tcp:<port>` and http://127.0.0.1:<port> in the
app. http://10.0.2.2:<port> reaches the computer from the device's SHELL, but on API 37 the app's own
uid timed out on it (measured) — check with `net.sh reach`, which asks **as the app** on a debuggable
build with `android.package` set, and from the device's shell otherwise (it says which). A physical phone
needs --host 0.0.0.0 and the computer's address.

Signing in against it: a cookie session needs the `Set-Cookie` header (--header, or "headers" in a
route). An account switch as a fake account (SKILL.md R11) also needs every screen it visits to get a
route — empty lists, not errors — or the errors hide what the previous account left behind.

Why it exists: Python's own `HTTPServer` looks the host up in DNS (`getfqdn`) before listening; on a
Mac that hung, the port sat in CLOSED, and it looked exactly like a blocked sandbox (measured).
"""
import argparse
import json
import os
import socketserver
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "android"))
from ui import hide_secrets_in_text          # noqa: E402  — one hiding rule for the whole harness (R11)


class NoLookupServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer.server_bind() calls socket.getfqdn(): the hang. Bind without it.
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name, self.server_port = host, port


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--status", type=int, default=500)
    p.add_argument("--body", default="")
    p.add_argument("--type", default="application/json")
    p.add_argument("--delay", type=float, default=0, help="seconds before answering")
    p.add_argument("--header", action="append", default=[], help='"Name: value", repeatable — e.g. a Set-Cookie')
    p.add_argument("--routes", help='JSON file: {"METHOD /path": {"status": …, "body": …, "type": …, "delay": …, "headers": {…}}}')
    a = p.parse_args()
    for h in a.header:
        # It used to start and then fail inside every request: the app saw a dropped connection,
        # which reads as a network failure, not as the status the test asked for.
        if ":" not in h:
            raise SystemExit(f'--header {h!r}: expected "Name: value"')
    routes = json.load(open(a.routes)) if a.routes else {}
    for key, route in routes.items():
        # A route whose body is written as JSON (an object, a number) used to crash the handler thread
        # and the app saw a connection reset, which reads as a network failure (audit).
        if "body" in route and not isinstance(route["body"], str):
            route["body"] = json.dumps(route["body"])
        try:
            route["status"] = int(route.get("status", a.status))
        except (TypeError, ValueError):
            raise SystemExit(f'route {key!r}: "status" must be a number, not {route.get("status")!r}')

    class Handler(BaseHTTPRequestHandler):
        def answer(self):
            length = int(self.headers.get("Content-Length") or 0)
            sent = self.rfile.read(length) if length else b""
            route = routes.get(f"{self.command} {self.path.split('?')[0]}", {})
            status, body = route.get("status", a.status), route.get("body", a.body)
            kind, delay = route.get("type", a.type), route.get("delay", a.delay)
            # The body goes into the run report, and a sign-in or a token refresh posts the credential
            # in it (audit). Same hiding as everywhere else (R11).
            # Hidden first, cut second: cut first, an object under a secret key never closes and what
            # was inside it printed. The query string too — `?api_key=…` is a credential like any other.
            shown_body = hide_secrets_in_text(sent.decode(errors="replace"))[:300] if sent else ""
            shown_path = hide_secrets_in_text(self.path, inline=True)
            print(f"{time.strftime('%H:%M:%S')} {self.command} {shown_path} → {status}"
                  + (f"  body: {shown_body}" if sent else ""), flush=True)
            if delay:
                time.sleep(delay)
            raw = body.encode()
            self.send_response(status)
            # A list of pairs, not a dict: two `--header "Set-Cookie: …"` are two headers, and a dict
            # kept only the last one (audit) — which is exactly how a server sets two cookies.
            pairs = [tuple(h.split(":", 1)) for h in a.header]
            pairs += [(str(k), str(v)) for k, v in route.get("headers", {}).items()]
            for name, value in pairs:
                self.send_header(name.strip(), str(value).strip())
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            # HEAD carries the headers and no body — a client that reads one hangs or errors.
            if self.command != "HEAD":
                self.wfile.write(raw)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = answer

        def log_message(self, *args):
            pass

    server = NoLookupServer((a.host, a.port), Handler)
    print(f"fake server on http://{a.host}:{a.port} — every request gets {a.status} unless a route says otherwise", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
