#!/usr/bin/env python3
"""Laya development CLI: JSON stdin/files in, validated advisory JSON out.

Agent-agnostic by design: standard library only, no credentials in arguments, one JSON object on
stdout, and a non-zero exit code with ``status: unknown`` when nothing could be decided. Any
coding agent that can run a shell command can call it; see references/integration.md.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from dev_workflows import prepare, interpret
from laya_protocol import (
    MAX_OPTION_TEXT_CHARS,
    PROTOCOL,
    DecisionError,
    require,
    validate_request,
    validate_answers,
)

SKILL_VERSION = "0.4.1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def env_file_candidates(explicit=None):
    """Ordered (path, origin) pairs for the credential file, first existing one wins.

    The XDG, home and optional explicit paths make the helper usable by any host agent. The
    Hermes-compatible paths remain last so an existing local installation keeps working.
    """
    home = Path.home()
    candidates = []
    if explicit:
        candidates.append((Path(explicit).expanduser(), "--env-file"))
    if os.environ.get("LAYA_ENV_FILE"):
        candidates.append((Path(os.environ["LAYA_ENV_FILE"]).expanduser(), "$LAYA_ENV_FILE"))
    if os.environ.get("LAYA_HOME"):
        candidates.append((Path(os.environ["LAYA_HOME"]).expanduser() / "laya.env", "$LAYA_HOME/laya.env"))
    candidates.append((home / ".config" / "laya" / "laya.env", "~/.config/laya/laya.env"))
    candidates.append((home / ".laya.env", "~/.laya.env"))
    hermes_home = Path(os.environ.get("HERMES_HOME", str(home / ".hermes"))).expanduser()
    candidates.append((hermes_home / "secrets" / "laya.env", "${HERMES_HOME:-~/.hermes}/secrets/laya.env"))
    candidates.append((home / ".hermes" / "secrets" / "laya.env", "~/.hermes/secrets/laya.env"))

    seen, unique = set(), []
    for path, origin in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append((path, origin))
    return unique


def load_config(env_file=None):
    """Read the credential file that exists, then let environment variables win.

    Values already exported in the environment override the file, so a caller can point the same
    helper at a different gateway without writing a file.
    """
    values = {}
    found = None
    for path, origin in env_file_candidates(env_file):
        if path.is_file():
            found = (path, origin)
            break
    if env_file and found is None:
        raise DecisionError("configuration_error", "Env file %s does not exist." % env_file)
    if found is not None:
        for line in found[0].read_text(encoding="utf-8").splitlines():
            line = line.strip().removeprefix("export ")
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep and key.strip().startswith("LAYA_"):
                try:
                    parts = shlex.split(value, comments=True)
                except ValueError:
                    raise DecisionError("configuration_error", "Invalid quoting in the Laya env file.") from None
                require(len(parts) <= 1, "Env values containing spaces must be quoted.", "configuration_error")
                values[key.strip()] = parts[0] if parts else ""
    values.update({k: v for k, v in os.environ.items() if k.startswith("LAYA_")})
    if not values.get("LAYA_BASE_URL"):
        raise DecisionError(
            "configuration_error",
            "LAYA_BASE_URL is not set. Export it, or put it in one of: %s"
            % ", ".join(origin for _path, origin in env_file_candidates(env_file)),
        )
    return values


def fetch(config, path, payload=None):
    base = config.get("LAYA_BASE_URL", "").rstrip("/")
    url = urllib.parse.urlsplit(base)
    require(url.scheme in ("http", "https") and url.hostname and not url.username and not url.password and not url.query and not url.fragment, "Configure a valid LAYA_BASE_URL API root.", "configuration_error")
    require(path.startswith("/") and not path.startswith("//") and "?" not in path and "#" not in path, "Invalid API path.", "configuration_error")
    try:
        timeout = float(config.get("LAYA_TIMEOUT_SECONDS", "15"))
    except ValueError:
        raise DecisionError("configuration_error", "LAYA_TIMEOUT_SECONDS must be a number.") from None
    require(0 < timeout <= 120, "Timeout must be between 0 and 120 seconds.", "configuration_error")
    headers = {"Content-Type": "application/json"}
    if config.get("LAYA_API_KEY"):
        headers["Authorization"] = "Bearer " + config["LAYA_API_KEY"]
    body = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    request = urllib.request.Request(base + path, data=body, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(2_000_001)
        require(len(raw) <= 2_000_000, "Response too large.", "invalid_response")
        value = json.loads(raw)
    except urllib.error.HTTPError as error:
        # Never echo gateway bodies: they may contain input data or credentials.
        hints = {401: "Gateway rejected credentials.", 403: "Token cannot access this model.", 404: "Endpoint or model is unavailable.", 413: "Reduce the request size.", 422: "Shorten state/options or check the decision schema; nothing was inferred.", 429: "Gateway rate limit reached."}
        raise DecisionError("http_" + str(error.code), hints.get(error.code, "HTTP request failed; no decision is available.")) from None
    except (TimeoutError, socket.timeout):
        raise DecisionError("timeout", "Request timed out; continue with the existing development workflow.") from None
    except urllib.error.URLError:
        raise DecisionError("connection_error", "Cannot reach the configured Laya endpoint.") from None
    except (ValueError, UnicodeError):
        raise DecisionError("invalid_response", "Backend returned invalid JSON.") from None
    return value, round((time.monotonic() - started) * 1000, 1)


def decide(config, payload, model=None):
    validate_request(payload)
    model = model or config.get("LAYA_MODEL") or "laya-latest"
    native = config.get("LAYA_NATIVE_DECISIONS", "false").lower() == "true"
    if native:
        result, elapsed = fetch(config, config.get("LAYA_DECISION_PATH", "/decisions"), {"model": model, **payload})
    else:
        result, elapsed = fetch(config, config.get("LAYA_CHAT_PATH", "/chat/completions"), {
            "model": model, "stream": False, "messages": [{"role": "user", "content": json.dumps({"laya_protocol": PROTOCOL, **payload}, ensure_ascii=False, allow_nan=False)}]})
    require(isinstance(result, dict) and result.get("model") == model, "Backend model identity does not match the request.", "invalid_response")
    outer = result
    if not native:
        try:
            result = json.loads(result["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError):
            raise DecisionError("invalid_response", "Chat content is not a decision object.") from None
        require(isinstance(result, dict) and result.get("laya_protocol") == PROTOCOL, "Adapter does not support dynamic decisions. Do not interpret preset answers as custom answers.", "unsupported_protocol")
    require(isinstance(result, dict) and result.get("status", "ok") not in ("unknown", "degraded", "error"), "Backend could not make a decision.", "backend_degraded")
    require(result.get("context", {}).get("input_truncated") is not True, "Backend truncated the input; reduce the evidence.", "invalid_response")
    answers = validate_answers(result.get("answers"), payload["questions"])
    return {"status": "advisory", "auto_action": False, "model": model, "checkpoint": result.get("checkpoint"),
            "routing": result.get("routing"), "calibration": result.get("calibration", "deployment_unverified"), "answers": answers,
            "latency_ms": elapsed, "backend_latency_ms": outer.get("laya_latency_ms", result.get("latency_ms")), "usage": result.get("usage", outer.get("usage")), "context": result.get("context")}


# Fixtures for `selftest`. `contract` cases must always pass; `baseline` cases pin what the
# shipped deployment measured, so a failure means re-measure, not necessarily breakage.
FIXTURES = (
    ("select_en", "baseline", "select", {
        "request": "Fix the login crash and add a regression test",
        "candidates": [
            {"id": "debug", "description": "Locate the stack trace and fix the source code"},
            {"id": "docs", "description": "Write user documentation"},
            {"id": "dependency", "description": "Check dependency versions and installation"},
        ]}, lambda r: r.get("suggested_id") == "debug"),
    ("routing_zh", "contract", "select", {
        "request": "修复登录崩溃并补回归测试",
        "candidates": [
            {"id": "debug", "description": "定位堆栈并修复源代码"},
            {"id": "docs", "description": "编写文档"},
        ]}, lambda r: r.get("checkpoint") == "multilingual"),
    ("triage_heuristic_priority", "contract", "triage", {
        "request": "fix CI", "command": "pytest -q", "exit_code": 1,
        "first_error": "ModuleNotFoundError: No module named 'requests'", "environment": "Ubuntu CI"},
        lambda r: r.get("suggested_area") == "dependency" and r.get("laya_role") == "tiebreaker_only"),
    ("change_review_floor", "contract", "change-review", {
        "summary": "Add OAuth session validation and a token table migration",
        "changed_files": ["app/auth/session.py", "migrations/004_tokens.sql", "tests/test_auth.py"],
        "diff_stats": {"files": 3, "additions": 140, "deletions": 12},
        "tests": {"unit": "passed", "integration": "not_run"}},
        lambda r: r.get("effective_risk") == "high" and r.get("minimum_test_scope") == "integration"
        and "migration-review" in (r.get("recommended_reviews") or [])),
)


def selftest(config):
    """Prove the live deployment still works, and record what it is currently good at."""
    cases = []
    listing, elapsed = fetch(config, "/models")
    names = [m.get("id") for m in listing.get("data", [])] if isinstance(listing, dict) else []
    cases.append({"case": "models_reachable", "kind": "contract",
                  "ok": bool([n for n in names if isinstance(n, str) and n.startswith("laya")]),
                  "detail": names, "latency_ms": elapsed})
    for name, kind, mode, payload, check in FIXTURES:
        try:
            result = main_like_decide(config, mode, payload)
            ok = bool(check(result))
            detail = {key: result.get(key) for key in
                      ("checkpoint", "suggested_id", "laya_suggested_id", "suggested_area", "laya_area",
                       "effective_risk", "minimum_test_scope", "needs_review") if key in result}
        except DecisionError as error:
            ok, detail = False, {"error": error.code}
        cases.append({"case": name, "kind": kind, "ok": ok, "detail": detail})
    oversized = dict(FIXTURES[0][3])
    oversized = {"request": oversized["request"],
                 "candidates": [dict(c, description="x" * (MAX_OPTION_TEXT_CHARS + 1)) for c in oversized["candidates"]]}
    try:
        validate_request(prepare("select", oversized))
        guarded = False
    except DecisionError as error:
        guarded = error.code in ("invalid_input", "context_budget_exceeded")
    cases.append({"case": "local_guard_rejects_oversized_option", "kind": "contract", "ok": guarded,
                  "detail": "rejected before any request" if guarded else "guard did not fire"})
    contract = [c for c in cases if c["kind"] == "contract"]
    baseline = [c for c in cases if c["kind"] == "baseline"]
    return {"status": "ok" if all(c["ok"] for c in contract) else "degraded",
            "protocol": PROTOCOL, "skill_version": SKILL_VERSION, "cases": cases,
            "contract_passed": sum(1 for c in contract if c["ok"]), "contract_total": len(contract),
            "baseline_passed": sum(1 for c in baseline if c["ok"]), "baseline_total": len(baseline),
            "notes": ["contract cases cover plumbing, routing and deterministic policy; baseline cases pin measured model quality",
                      "a failing baseline case means re-measure on your own samples before trusting the branch"]}


def main_like_decide(config, mode, payload):
    """Shared path so selftest exercises exactly what a caller does."""
    validated = validate_request(prepare(mode, payload))
    output = decide(config, validated)
    output.update(interpret(mode, payload, output["answers"]))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=["models", "decide", "select", "rerank", "triage", "verify", "change-review", "preset", "selftest"])
    parser.add_argument("--input", default="-", help="JSON file, or - for stdin; preset takes plain text")
    parser.add_argument("--env-file", help="Literal env file; existing environment values take precedence")
    parser.add_argument("--model")
    parser.add_argument("--dry-run", action="store_true", help="Show the request schema without credentials or HTTP calls")
    parser.add_argument("--version", action="store_true", help="Print the helper/protocol version and exit")
    args = parser.parse_args()
    try:
        if args.version:
            print(json.dumps({"helper": "laya-agent-skill", "skill_version": SKILL_VERSION, "protocol": PROTOCOL}, ensure_ascii=False))
            return 0
        if not args.mode:
            parser.error("mode is required unless --version is used")
        data = None
        if args.mode not in ("models", "selftest"):
            raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
            data = raw if args.mode == "preset" else json.loads(raw)
        if args.mode not in ("models", "preset", "selftest"):
            payload = validate_request(prepare(args.mode, data))
            if args.dry_run:
                print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
                return 0
        require(not args.dry_run, "Dry-run applies to development/custom decisions only.")
        config = load_config(args.env_file)
        if args.mode == "models":
            listing, elapsed = fetch(config, "/models")
            require(isinstance(listing, dict) and isinstance(listing.get("data"), list), "Invalid model list.", "invalid_response")
            output = {"status": "ok", "models": [m["id"] for m in listing["data"]], "latency_ms": elapsed}
        elif args.mode == "selftest":
            output = selftest(config)
        elif args.mode == "preset":
            require(args.model and args.model.startswith("laya-preset-"), "Choose an explicit laya-preset-* model.")
            outer, elapsed = fetch(config, config.get("LAYA_CHAT_PATH", "/chat/completions"), {"model": args.model, "stream": False, "messages": [{"role": "user", "content": data}]})
            result = json.loads(outer["choices"][0]["message"]["content"])
            require(outer.get("model") == args.model and isinstance(result.get("answers"), dict), "Invalid preset response.", "invalid_response")
            # A preset's schema is deployment-specific; do not claim dynamic validation.
            output = {"status": "advisory", "auto_action": False, "schema_validation": "preset_unverified",
                      "model": args.model, "checkpoint": result.get("checkpoint"), "routing": result.get("routing"),
                      "calibration": result.get("calibration", "deployment_unverified"),
                      "answers": result["answers"], "latency_ms": elapsed, "context": result.get("context")}
        else:
            output = decide(config, payload, args.model)
            output.update(interpret(args.mode, data, output["answers"]))
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if output.get("status") != "degraded" else 2
    except DecisionError as error:
        output = {"status": "unknown", "auto_action": False, "error": {"code": error.code, "message": str(error)}, "fallback": "Continue with the main model and existing tools; no action was authorized."}
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        output = {"status": "unknown", "auto_action": False, "error": {"code": "input_or_response_error", "message": "Could not read valid input or parse the backend response."}}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
