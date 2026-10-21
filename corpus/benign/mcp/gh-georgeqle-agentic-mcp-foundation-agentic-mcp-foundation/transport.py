"""Private loopback RPC and exclusive local ownership for shared coordinators."""

import hmac
import json
import os
import secrets
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from . import PROTOCOL_VERSION, LifecycleError


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + secrets.token_hex(8))
    try:
        with temporary.open("x", encoding="utf-8") as output:
            os.chmod(temporary, 0o600)
            json.dump(value, output, sort_keys=True, allow_nan=False)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def file_lock(path: Path, blocking=True, shared=False):
    try:
        import fcntl
    except ImportError as exc:
        raise LifecycleError(
            "UNSUPPORTED_PLATFORM", "Shared coordinator requires POSIX locks"
        ) from exc
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+") as handle:
        try:
            fcntl.flock(
                handle,
                (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | (0 if blocking else fcntl.LOCK_NB),
            )
        except BlockingIOError as exc:
            raise LifecycleError("BUSY", "Another process owns this runtime", True) from exc
        yield


def rpc(endpoint, operation, payload=None, timeout=15):
    # Discovery is local user state, but never let a corrupted record redirect credentials.
    port = endpoint.get("port")
    if (
        endpoint.get("protocol") != PROTOCOL_VERSION
        or type(port) is not int
        or not 1 <= port <= 65535
    ):
        raise LifecycleError("INCOMPATIBLE_RUNTIME", "Malformed/incompatible coordinator endpoint")
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.post(
                f"http://127.0.0.1:{port}/rpc",
                headers={"Authorization": "Bearer " + endpoint["token"]},
                json={"operation": operation, "payload": payload or {}},
            )
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise LifecycleError(
            "COORDINATOR_UNAVAILABLE",
            "Coordinator unavailable; reconnect and recover the same job/key before retrying",
            True,
        ) from exc
    if not body.get("ok"):
        error = body["error"]
        raise LifecycleError(error["code"], error["message"], error["retryable"])
    return body["result"]


class SharedClient:
    """Adapter-independent discovery, single-start and idle generation replacement."""

    def __init__(self, directory, identity, command, settings):
        self.directory, self.identity = directory, identity
        self.command, self.settings = command, settings
        self.endpoint = None

    def discover(self):
        try:
            endpoint = json.loads((self.directory / "endpoint.json").read_text())
            return endpoint, rpc(endpoint, "health", timeout=2)
        except (OSError, ValueError):
            return None, None
        except LifecycleError as exc:
            if exc.code != "COORDINATOR_UNAVAILABLE":
                raise
            return None, None

    def connect(self):
        with file_lock(self.directory / "startup.lock"):
            endpoint, health = self.discover()
            if health and health.get("contract_major") != self.identity.get("contract_major"):
                raise LifecycleError("INCOMPATIBLE_RUNTIME", "Active tool contract is incompatible")
            if health and health.get("build") != self.identity.get("build"):
                rpc(endpoint, "retire")
                deadline = time.monotonic() + 15
                while self.discover()[0] and time.monotonic() < deadline:
                    time.sleep(0.05)
                endpoint, health = self.discover()
                if endpoint:
                    raise LifecycleError("BUSY", "Previous runtime is still draining", True)
            if endpoint:
                self.endpoint = endpoint
                return
            atomic_json(self.directory / "settings.json", self.settings)
            log_path = self.directory / "coordinator.log"
            if log_path.exists() and log_path.stat().st_size > 5 * 1024**2:
                log_path.replace(self.directory / "coordinator.previous.log")
            with log_path.open("ab") as log:
                process = subprocess.Popen(
                    self.command,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                endpoint, health = self.discover()
                if endpoint:
                    if health.get("build") != self.identity.get("build"):
                        raise LifecycleError("INCOMPATIBLE_RUNTIME", "Coordinator build mismatch")
                    self.endpoint = endpoint
                    return
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            raise LifecycleError("STARTUP_FAILED", f"Coordinator startup failed; see {log_path}")

    def call(self, operation, payload=None):
        if self.endpoint is None:
            self.connect()
        try:
            return rpc(self.endpoint, operation, payload)
        except LifecycleError as exc:
            if exc.code != "COORDINATOR_UNAVAILABLE":
                raise
            # Mutating submissions carry a durable idempotency key; retry the exact envelope once.
            self.endpoint = None
            self.connect()
            return rpc(self.endpoint, operation, payload)


def serve(directory, identity, dispatch, on_close):
    """Hold owner.lock for the entire server lifetime; no PID-based process termination."""
    with file_lock(directory / "owner.lock", blocking=False):
        token = secrets.token_urlsafe(32)

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                if not hmac.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + token
                ):
                    self.send_error(401)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if self.path != "/rpc" or not 0 < length <= 1024 * 1024:
                        raise LifecycleError("INVALID_REQUEST", "Invalid RPC path or body size")
                    request = json.loads(self.rfile.read(length))
                    operation, payload = request["operation"], request["payload"]
                    if not isinstance(payload, dict):
                        raise LifecycleError("INVALID_REQUEST", "Payload must be an object")
                    if operation == "health":
                        result = {**identity, "protocol": PROTOCOL_VERSION, "pid": os.getpid()}
                    elif operation == "retire":
                        result = dispatch(operation, payload)
                        threading.Thread(target=server.shutdown, daemon=True).start()
                    else:
                        result = dispatch(operation, payload)
                    body = {"ok": True, "result": result}
                except Exception as exc:  # noqa: BLE001 - protocol error boundary
                    error = (
                        exc.report()
                        if isinstance(exc, LifecycleError)
                        else {
                            "code": "INVALID_REQUEST",
                            "message": str(exc)[:2000],
                            "retryable": False,
                        }
                    )
                    body = {"ok": False, "error": error}
                raw = json.dumps(body, allow_nan=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # The coordinator retains the job after a client disconnects.

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        endpoint = {
            "protocol": PROTOCOL_VERSION,
            "port": server.server_port,
            "token": token,
            **identity,
        }
        atomic_json(directory / "endpoint.json", endpoint)
        try:
            server.serve_forever(poll_interval=0.1)
        finally:
            server.server_close()
            on_close()
            try:
                path = directory / "endpoint.json"
                if json.loads(path.read_text()).get("token") == token:
                    path.unlink()
            except (OSError, ValueError):
                pass
