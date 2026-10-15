"""Central queue API and TCP workers, with no shared worker filesystem.

Only the API owns SQLite on its local disk. Claims and every lease mutation are
serialized by JobQueue transactions on that host, using the server clock. This
is a deployable single-coordinator architecture, not a replicated database.
Execution and external effects remain at-least-once after failures.
"""
import argparse
from dataclasses import asdict, replace
import hmac
import json
import math
import os
from pathlib import Path
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
from socketserver import ThreadingMixIn

from .jobs import Job, JobQueue, LostLease, _duration


MAX_REQUEST_BYTES = 2_200_000
MAX_RESPONSE_BYTES = 3_000_000


class QueueTransportError(RuntimeError):
    """A request failed; callers must not assume a mutation was not committed."""


def _token(value):
    if not isinstance(value, str) or len(value) < 32 or len(value) > 512 or not value.isascii() or any(c.isspace() for c in value):
        raise ValueError("QUEUE_TOKEN must be a 32..512 character ASCII secret without whitespace")
    return value


def _json(raw):
    def reject_constant(value):
        raise ValueError("non-finite JSON value")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=pairs)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("invalid JSON") from exc


def _identity(value, name="id"):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise ValueError(f"{name} must be a bounded string")
    return value


def _lease(value):
    value = _duration(value)
    if value > 3600:
        raise ValueError("lease_seconds must be at most 3600")
    return value


class QueueApplication:
    """Bounded authenticated WSGI API. One credential grants operator access.

    Deploy behind TLS and a private firewall; this API is not tenant isolation.
    Job data is untrusted, never executed as Python or shell code.
    """
    def __init__(self, database, token):
        self.queue, self.token = JobQueue(database), _token(token)

    def _job(self, data):
        current = self.queue.get(_identity(data.get("id")))
        if current is None:
            raise LostLease("job does not exist")
        return replace(current, worker=_identity(data.get("worker"), "worker"),
                       lease_token=_identity(data.get("lease_token"), "lease_token"))

    def dispatch(self, operation, data):
        if not isinstance(data, dict):
            raise ValueError("request must be an object")
        allowed = {
            "enqueue": {"task", "payload", "idempotency_key", "max_attempts"},
            "get": {"id"}, "cancel": {"id"}, "claim": {"worker", "lease_seconds"},
            "heartbeat": {"id", "worker", "lease_token", "lease_seconds"},
            "check": {"id", "worker", "lease_token"},
            "complete": {"id", "worker", "lease_token", "result"},
            "fail": {"id", "worker", "lease_token", "error", "retry"},
        }
        if operation not in allowed:
            raise KeyError("unknown operation")
        if set(data) - allowed[operation]:
            raise ValueError("unknown request field")
        if operation == "enqueue":
            value = self.queue.enqueue(data.get("task"), data.get("payload"),
                idempotency_key=data.get("idempotency_key"), max_attempts=data.get("max_attempts", 3))
        elif operation in ("get", "cancel"):
            value = getattr(self.queue, operation)(_identity(data.get("id")))
        elif operation == "claim":
            value = self.queue.claim(data.get("worker"), lease_seconds=_lease(data.get("lease_seconds", 30)))
        else:
            job = self._job(data)
            if operation == "heartbeat":
                value = self.queue.heartbeat(job, lease_seconds=_lease(data.get("lease_seconds", 30)))
            elif operation == "check":
                # The authority is the coordinator's clock, never a worker clock.
                current = self.queue.get(job.id)
                if (current.status != "running" or current.worker != job.worker
                        or current.lease_token != job.lease_token
                        or current.lease_until is None or current.lease_until <= time.time()):
                    raise LostLease("job ownership was lost")
                value = current.cancel_requested
            elif operation == "complete":
                if "result" not in data:
                    raise ValueError("result is required")
                value = self.queue.complete(job, data["result"])
            else:
                if type(data.get("retry", True)) is not bool or not isinstance(data.get("error"), str):
                    raise ValueError("error must be a string and retry must be boolean")
                value = self.queue.fail(job, data["error"], retry=data.get("retry", True))
        return asdict(value) if isinstance(value, Job) else value

    def __call__(self, environ, start_response):
        def response(status, value):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                                    ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
            return [body]
        if environ.get("REQUEST_METHOD") == "GET" and environ.get("PATH_INFO") == "/health":
            return response("200 OK", {"ok": True})
        provided = environ.get("HTTP_AUTHORIZATION", "")
        if not isinstance(provided, str) or not provided.isascii() or not hmac.compare_digest(provided, "Bearer " + self.token):
            return response("401 Unauthorized", {"error": "authentication required"})
        if environ.get("REQUEST_METHOD") != "POST":
            return response("405 Method Not Allowed", {"error": "POST required"})
        if environ.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
            return response("415 Unsupported Media Type", {"error": "JSON required"})
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
            if not 1 <= length <= MAX_REQUEST_BYTES:
                return response("413 Payload Too Large", {"error": "invalid request size"})
            raw = environ["wsgi.input"].read(length)
            if len(raw) != length:
                raise ValueError("incomplete request body")
            path = environ.get("PATH_INFO", "")
            if not path.startswith("/v1/") or "/" in path[4:]:
                return response("404 Not Found", {"error": "unknown operation"})
            value = self.dispatch(path[4:], _json(raw))
            return response("200 OK", {"value": value})
        except LostLease:
            return response("409 Conflict", {"error": "stale or expired lease"})
        except KeyError:
            return response("404 Not Found", {"error": "unknown operation"})
        except (ValueError, TypeError, OverflowError, RecursionError):
            return response("400 Bad Request", {"error": "invalid request"})
        except sqlite3.Error:
            return response("503 Service Unavailable", {"error": "queue unavailable"})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the bearer credential to a redirect destination.
        return None


class HTTPJobQueue:
    """JobQueue-compatible network client; deliberately no mutation auto-retry."""
    def __init__(self, base_url, token, *, timeout=10):
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("base_url must be a plain HTTP(S) origin without credentials")
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), _token(token), timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def _request(self, operation, data):
        try:
            raw = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (RecursionError, TypeError) as exc:
            raise ValueError("request is not bounded JSON") from exc
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("request too large")
        request = urllib.request.Request(self.base_url + "/v1/" + operation, raw,
            {"Content-Type": "application/json", "Authorization": "Bearer " + self.token}, method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as handle:
                body = handle.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise QueueTransportError("queue response too large")
            return _json(body)["value"]
        except urllib.error.HTTPError as exc:
            code = exc.code
            exc.close()
            if code == 409:
                raise LostLease("stale or expired coordinator lease") from None
            if code in (400, 413, 415):
                raise ValueError("coordinator rejected request") from None
            raise QueueTransportError(f"coordinator HTTP {code}; mutation outcome may be unknown") from None
        except (urllib.error.URLError, TimeoutError, OSError, KeyError, ValueError, TypeError, RecursionError) as exc:
            raise QueueTransportError("queue transport failed; mutation outcome may be unknown") from exc

    @staticmethod
    def _decode(value):
        return Job(**value) if value is not None else None

    @staticmethod
    def _ownership(job):
        return {"id": job.id, "worker": job.worker, "lease_token": job.lease_token}

    def enqueue(self, task, payload=None, *, idempotency_key=None, max_attempts=3):
        return self._decode(self._request("enqueue", dict(task=task, payload=payload,
                            idempotency_key=idempotency_key, max_attempts=max_attempts)))

    def get(self, identity):
        return self._decode(self._request("get", {"id": identity}))

    def claim(self, worker, *, lease_seconds=30):
        return self._decode(self._request("claim", {"worker": worker, "lease_seconds": lease_seconds}))

    def heartbeat(self, job, *, lease_seconds=30):
        return self._request("heartbeat", {**self._ownership(job), "lease_seconds": lease_seconds})

    def check(self, job):
        return self._request("check", self._ownership(job))

    def complete(self, job, result):
        return self._decode(self._request("complete", {**self._ownership(job), "result": result}))

    def fail(self, job, error, *, retry=True):
        return self._decode(self._request("fail", {**self._ownership(job), "error": str(error)[:4000], "retry": retry}))

    def cancel(self, identity):
        return self._decode(self._request("cancel", {"id": identity}))


class HTTPWorker:
    """Remote callback worker. Lease authority stays entirely on the API host."""
    def __init__(self, queue, handler, *, worker_id=None, lease_seconds=30):
        self.queue, self.handler = queue, handler
        self.worker_id, self.lease_seconds = worker_id or uuid.uuid4().hex, _lease(lease_seconds)

    def run_once(self):
        job = self.queue.claim(self.worker_id, lease_seconds=self.lease_seconds)
        if job is None:
            return None
        done, lost = threading.Event(), threading.Event()

        def renew():
            while not done.wait(self.lease_seconds / 3):
                try:
                    if not self.queue.heartbeat(job, lease_seconds=self.lease_seconds):
                        return
                except (LostLease, QueueTransportError, ValueError):
                    lost.set()
                    return

        def cancelled():
            if lost.is_set():
                raise LostLease("coordinator ownership could not be renewed")
            return self.queue.check(job)

        heartbeat = threading.Thread(target=renew, daemon=True)
        heartbeat.start()
        try:
            result = self.handler(job, cancelled)
            if lost.is_set():
                raise LostLease("coordinator ownership was lost")
            self.queue.complete(job, result)
        except LostLease:
            pass
        except QueueTransportError:
            # A transport error can mean a committed response was lost. Do not
            # blindly submit a different outcome; lease recovery is explicit.
            raise
        except Exception as exc:
            try:
                self.queue.fail(job, f"{type(exc).__name__}: {exc}")
            except LostLease:
                pass
        finally:
            done.set()
            heartbeat.join()
        return self.queue.get(job.id)

    def run_forever(self, *, stop=None, poll_seconds=.25):
        stop = stop or threading.Event()
        _duration(poll_seconds)
        while not stop.is_set():
            try:
                if self.run_once() is None:
                    stop.wait(poll_seconds)
            except QueueTransportError:
                # Back off after an ambiguous request; never replay it inline.
                stop.wait(max(poll_seconds, self.lease_seconds))


class AgentJobHandler:
    """Run the actual ReAct runtime against each worker's prepared local data.

    Configuration is trusted worker configuration; queue payloads may select
    only an exact service. Workers never execute uploaded code or choose paths
    from a task payload. A new node can repeat read-only work after a crash;
    journals are local to that node, not magically replicated between nodes.
    """
    def __init__(self, data, output, model, *, service=None, verify=False,
                 skill=None, connection=None, max_steps=8, max_calls=16,
                 max_tokens=48000, max_context_chars=60000):
        from .runtime import SYSTEM
        self.data, self.output = Path(data).resolve(), Path(output).resolve()
        self.data.mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)
        self.metrics = self.data / "metrics.sqlite"
        if connection is not None:
            from .connectors import load_sources
            from .knowledge import Knowledge
            connector = load_sources(connection)
            self.metrics = connector.metrics_database
            knowledge = Knowledge(self.data / "knowledge.sqlite")
            try:
                connector.ingest_into(knowledge)
            finally:
                knowledge.db.close()
        if not (self.data / "knowledge.sqlite").is_file() or not self.metrics.is_file():
            raise ValueError("agent-worker requires prepared knowledge.sqlite and metrics.sqlite, or an explicit connection")
        self.model, self.service, self.verify = model, service, verify
        if not model.fixture:
            model.revision = model.describe()
        system = SYSTEM
        if skill is not None:
            from .skills import load_skill
            system = load_skill(skill).prompt(system)
        if verify:
            from .domain import answer_schema
            system += "\nInspect all three tools for the exact service. Return only JSON conforming to this schema; copy service_metrics.error_rate for the entire 30-minute window, not recent_error_rate.\n" + json.dumps(answer_schema())
        self.options = dict(max_steps=max_steps, max_calls=max_calls, max_tokens=max_tokens,
                            max_context=max_context_chars, system_prompt=system)

    def __call__(self, job, cancelled):
        from .knowledge import Knowledge
        from .runtime import Runtime, RuntimeBusy
        from .tools import registry
        from .verification import scope_tools, make_diagnostic_validator
        if not isinstance(job.payload, dict) or set(job.payload) - {"service"}:
            raise ValueError("agent payload permits only service")
        service = job.payload.get("service")
        if "service" in job.payload and (not isinstance(service, str) or not service):
            raise ValueError("job service must be a nonempty string")
        if service is not None and self.service is not None and service != self.service:
            raise ValueError("job service conflicts with the worker's authorized scope")
        service = self.service if service is None else service
        if self.verify and service is None:
            raise ValueError("verified job requires an authorized service")
        # Server-generated queue IDs are UUID hex, never arbitrary path segments.
        if len(job.id) != 32 or any(c not in "0123456789abcdef" for c in job.id):
            raise ValueError("invalid queue job ID")
        output = self.output / job.id
        # Scripted decisions contain mutable call lists which Runtime consumes.
        # Give each fixture job a fresh copy; live providers keep their revision.
        if self.model.fixture:
            import copy
            model = copy.deepcopy(self.model)
        else:
            model = self.model
        knowledge = Knowledge(self.data / "knowledge.sqlite")
        try:
            tools, options = registry(knowledge, self.metrics), dict(self.options)
            if service is not None:
                tools = scope_tools(tools, service)
            if self.verify:
                options["answer_validator"] = make_diagnostic_validator(service, job.task)
            while True:
                if cancelled():
                    return {"agent_status": "cancelled", "requires_review": True}
                try:
                    result = Runtime(output, model, tools, **options).run(job.task, is_cancelled=cancelled)
                    return {"agent_status": result["status"], "answer": result["answer"],
                            "fixture": result["fixture"], "trace": str(output / "trace.json"),
                            "requires_review": result["status"] != "completed"}
                except RuntimeBusy:
                    # Same-node recovery can wait for a previous lease's pending
                    # provider call; the HTTPWorker heartbeat retains ownership.
                    time.sleep(.1)
        finally:
            knowledge.db.close()


class _ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def demo_server(database, token, *, host="127.0.0.1", port=0):
    """Stdlib server for tests/local demonstrations only; never Internet-facing."""
    return make_server(host, port, QueueApplication(database, token),
                       server_class=_ThreadingWSGIServer, handler_class=_QuietHandler)


def _demo_handler(job, cancelled):
    """Synthetic bounded callback. Real deployments supply an Agent callback."""
    value = job.payload.get("value", 0)
    if type(value) is not int or abs(value) > 10**9:
        raise ValueError("synthetic value must be a bounded integer")
    if cancelled():
        return None
    return {"value": value * 2, "worker": job.worker}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve")
    server.add_argument("--database", required=True)
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--demo-server", action="store_true", help="stdlib local demonstration only")
    worker = commands.add_parser("demo-worker", help="synthetic callback only")
    worker.add_argument("--url", default="http://127.0.0.1:8765")
    worker.add_argument("--worker-id", default=None)
    worker.add_argument("--lease-seconds", type=float, default=30)
    agent = commands.add_parser("agent-worker", help="actual Runtime/Ollama worker with prepared local data")
    agent.add_argument("--url", default="http://127.0.0.1:8765")
    agent.add_argument("--worker-id", default=None)
    agent.add_argument("--lease-seconds", type=float, default=30)
    agent.add_argument("--data", type=Path, required=True)
    agent.add_argument("--output", type=Path, required=True)
    agent.add_argument("--model", required=True)
    agent.add_argument("--base-url", default="http://127.0.0.1:11434")
    agent.add_argument("--model-context", type=int, default=3072)
    agent.add_argument("--model-output", type=int, default=384)
    agent.add_argument("--timeout", type=float, default=300)
    agent.add_argument("--seed", type=int, default=42)
    agent.add_argument("--service")
    agent.add_argument("--verify", action="store_true")
    agent.add_argument("--skill", type=Path)
    agent.add_argument("--connection", type=Path)
    agent.add_argument("--max-steps", type=int, default=8)
    agent.add_argument("--max-calls", type=int, default=16)
    agent.add_argument("--max-tokens", type=int, default=48000)
    agent.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    secret = _token(os.environ.get("QUEUE_TOKEN"))
    if args.command == "serve":
        Path(args.database).resolve().parent.mkdir(parents=True, exist_ok=True)
        if args.demo_server:
            if args.host not in ("127.0.0.1", "::1", "localhost"):
                parser.error("demo server is restricted to loopback")
            with demo_server(args.database, secret, host=args.host, port=args.port) as http:
                http.serve_forever()
        else:
            try:
                from waitress import serve
            except ImportError:
                parser.error("install requirements-distributed.txt for the deployable WSGI server")
            serve(QueueApplication(args.database, secret), host=args.host, port=args.port,
                  threads=8, max_request_body_size=MAX_REQUEST_BYTES, channel_timeout=15,
                  clear_untrusted_proxy_headers=True)
    elif args.command == "demo-worker":
        HTTPWorker(HTTPJobQueue(args.url, secret), _demo_handler,
                   worker_id=args.worker_id, lease_seconds=args.lease_seconds).run_forever()
    else:
        from .model import Ollama
        model = Ollama(args.model, args.base_url, args.model_context, args.model_output, args.timeout, args.seed)
        handler = AgentJobHandler(args.data, args.output, model, service=args.service,
            verify=args.verify, skill=args.skill, connection=args.connection,
            max_steps=args.max_steps, max_calls=args.max_calls, max_tokens=args.max_tokens)
        worker = HTTPWorker(HTTPJobQueue(args.url, secret), handler,
                            worker_id=args.worker_id, lease_seconds=args.lease_seconds)
        if args.once:
            job = worker.run_once()
            # Tokens and transport credentials are never part of the job object.
            print(json.dumps(asdict(job) if job else {"status": "idle"}, ensure_ascii=False))
        else:
            worker.run_forever()


if __name__ == "__main__":
    main()
