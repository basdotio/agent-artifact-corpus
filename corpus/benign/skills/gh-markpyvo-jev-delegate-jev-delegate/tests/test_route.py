#!/usr/bin/env python3
"""Run with: python3 tests/test_route.py

Covers the policy (pure function) and the HTTP wiring against a local mock
server. It does NOT hit the real TypeSafe API; run
  TYPESAFE_API_KEY=... python3 scripts/route.py "rename foo to bar in utils.py"
once yourself to confirm the live request shape.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import route  # noqa: E402


def ans(choice="ordinary", conf=0.8, effort=1.0, risky=0.05, wide=0.1):
    return {
        "tier": {"type": "choice", "choice": choice, "confidence": conf,
                 "probabilities": {"mechanical": 0.0, "ordinary": 0.0, "hard": 0.0}},
        "effort": {"type": "score", "score": effort, "confidence": 0.7},
        "risky": {"type": "noul", "noul": risky},
        "wide": {"type": "noul", "noul": wide},
    }


def d(**kw):
    return route.decide(ans(**kw), 0.3, 0.6, "high")


def test_policy():
    assert d(choice="ordinary")["tier"] == "balanced"
    assert d(choice="mechanical", conf=0.9, effort=0.3)["tier"] == "fast"
    # low confidence: never downgrade
    assert d(choice="mechanical", conf=0.5, effort=0.3)["tier"] == "balanced"
    # signals disagree: mechanical label but high effort -> stay balanced
    assert d(choice="mechanical", conf=0.9, effort=2.0)["tier"] == "balanced"
    # wide task never goes to the small-window tier
    assert d(choice="mechanical", conf=0.9, effort=0.3, wide=0.8)["tier"] == "balanced"
    # upgrade needs only modest confidence
    assert d(choice="hard", conf=0.35)["tier"] == "deep"
    assert d(choice="hard", conf=0.2)["tier"] == "balanced"
    # risky forces deep even when Jev says mechanical
    assert d(choice="mechanical", conf=0.95, effort=0.1, risky=0.8)["tier"] == "deep"
    # unknown label falls back to balanced
    assert d(choice="???")["tier"] == "balanced"


def test_effort_hint_cap():
    assert route.effort_hint(0.2, "high") == "low"
    assert route.effort_hint(1.0, "high") == "medium"
    assert route.effort_hint(3.0, "high") == "high"      # capped
    assert route.effort_hint(3.0, "xhigh") == "xhigh"


def test_request_shape():
    req = route.build_request("do a thing")
    assert req["model"] == "jev-latest"
    assert req["state"] == {"task": "do a thing"}
    assert set(req["questions"]) == {"tier", "effort", "risky", "wide"}
    assert req["questions"]["tier"]["type"] == "choice"
    assert set(req["questions"]["tier"]["criteria"]) == {"mechanical", "ordinary", "hard"}
    assert req["questions"]["effort"]["type"] == "score"
    assert len(req["questions"]["effort"]["criteria"]) == 4
    assert req["questions"]["risky"]["type"] == "noul"
    # long tasks are truncated
    assert len(route.build_request("x" * 100000)["state"]["task"]) == route.MAX_TASK_CHARS


class Handler(BaseHTTPRequestHandler):
    mode = "ok"
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Handler.seen.append((self.headers.get("Authorization"), body))
        if Handler.mode == "500":
            self.send_response(500); self.end_headers(); return
        task = body["state"]["task"]
        if "typo" in task:
            a = ans("mechanical", 0.92, 0.2)
        elif "race condition" in task:
            a = ans("hard", 0.8, 2.6)
        else:
            a = ans("ordinary", 0.7, 1.0)
        out = json.dumps({"model": "jev-1.13.0", "answers": a, "usage": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def run_cli(url, *tasks, key="test-key"):
    env = {**os.environ, "HOME": tempfile.mkdtemp()}
    env.pop("TYPESAFE_API_KEY", None)
    env.pop("JEV_API_KEY", None)
    if key:
        env["TYPESAFE_API_KEY"] = key
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "route.py"), "--url", url, *tasks],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout), env["HOME"]


def test_cli_against_mock():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/v1/systemone"

    Handler.mode = "ok"
    Handler.seen.clear()
    out, home = run_cli(url, "fix the typo in README", "find the race condition in the queue", "add a unit test")
    assert [o["tier"] for o in out] == ["fast", "deep", "balanced"], out   # order preserved
    assert [o["model"] for o in out] == ["haiku", "opus", "sonnet"]
    assert all(auth == "Bearer test-key" for auth, _ in Handler.seen)
    assert len(Handler.seen) == 3

    # decisions logged, but never the task text
    log = (Path(home) / ".jev-delegate" / "decisions.jsonl").read_text()
    assert "typo" not in log and "README" not in log
    assert len(log.splitlines()) == 3

    # Jev down -> inherit, exit code still 0
    Handler.mode = "500"
    out, _ = run_cli(url, "anything")
    assert out[0]["tier"] == "inherit" and out[0]["model"] is None

    # no key -> inherit
    out, _ = run_cli(url, "anything", key=None)
    assert out[0]["tier"] == "inherit" and "TYPESAFE_API_KEY" in out[0]["reason"]

    # unreachable host -> inherit (fail open)
    out, _ = run_cli("http://127.0.0.1:9/v1/systemone", "anything")
    assert out[0]["tier"] == "inherit"
    srv.shutdown()


def test_report():
    srv_home = tempfile.mkdtemp()
    log = Path(srv_home) / "d.jsonl"
    rows = [{"tier": "fast", "latency_ms": 200}, {"tier": "balanced", "latency_ms": 300},
            {"tier": "deep", "latency_ms": 250}, {"tier": "fast", "latency_ms": 180}]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "report.py"), "--log", str(log)],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "4 routed tasks" in r.stdout and "50%" in r.stdout, r.stdout


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
