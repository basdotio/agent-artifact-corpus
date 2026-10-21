# SPDX-License-Identifier: MIT
"""Anonymous usage telemetry (Schema v2) for llm-crawler-audit. Opt-out: DO_NOT_TRACK=1 or MCP_TELEMETRY_OPT_OUT=1."""
from __future__ import annotations
import atexit
import json
import os
import platform
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

SERVER_NAME = "llm-crawler-audit"
try:
    import importlib.metadata
    MCP_SERVER_VERSION = importlib.metadata.version("llm-crawler-audit")
except Exception:
    MCP_SERVER_VERSION = "0.1.0"

GATEWAY_URLS = [
    "https://llm-crawler.builditwithai.xyz/e",
    "https://llm-crawler-audit-telemetry.reachsuren.workers.dev/e",
]
SCHEMA_VERSION = 2
SYNTHETIC_PATTERNS = ("fuzz", "test", "probe", "monitor")
SECRET_KEYS = ("secret", "token", "api_key", "apikey", "password", "authorization")

def _telemetry_disabled() -> bool:
    for var in ("DO_NOT_TRACK", "MCP_TELEMETRY_OPT_OUT", "DISABLE_TELEMETRY", "NO_TELEMETRY"):
        if os.getenv(var, "").lower() in ("1", "true", "yes", "on"):
            return True
    return False

TELEMETRY_DISABLED = _telemetry_disabled()

def _is_synthetic_client(name: str) -> bool:
    n = (name or "").lower()
    return any(p in n for p in SYNTHETIC_PATTERNS)

def scrub_props(props: Dict[str, Any]) -> Dict[str, Any]:
    """secret_text hygiene: never emit plaintext keys or secrets over wire."""
    clean: Dict[str, Any] = {}
    for k, v in props.items():
        kl = k.lower()
        if any(s in kl for s in SECRET_KEYS) or kl in ("key", "api-key", "_key"):
            clean[k] = "[REDACTED]"
        elif isinstance(v, str) and len(v) > 300:
            clean[k] = v[:300]
        else:
            clean[k] = v
    return clean

def _init_identity():
    try:
        d = Path.home() / ".llm-crawler-audit"
        f = d / "installation_id"
        if TELEMETRY_DISABLED:
            return (f.read_text(encoding="utf-8").strip() if f.exists() else f"anon_{uuid.uuid4()}"), False
        if f.exists():
            return f.read_text(encoding="utf-8").strip(), False
        d.mkdir(parents=True, exist_ok=True)
        nid = f"inst_{uuid.uuid4()}"
        f.write_text(nid, encoding="utf-8")
        return nid, True
    except Exception:
        return f"anon_{uuid.uuid4()}", False

DISTINCT_ID, IS_FIRST_INSTALL = _init_identity()
SESSION_ID = f"sess_{uuid.uuid4()}"

def _env_meta() -> Dict[str, Any]:
    tz = time.strftime("%z")
    ftz = f"{tz[:3]}:{tz[3:]}" if len(tz) == 5 else "+00:00"
    rc, agent = "cli", "unknown"
    if os.getenv("CLAUDE_CODE") or os.getenv("CLAUDE_PROJECT_DIR"):
        rc, agent = "claude_code", "claude"
    elif os.getenv("CURSOR_TRACE") or os.getenv("CURSOR_SESSION"):
        rc, agent = "cursor", "cursor"
    return {
        "schema_version": SCHEMA_VERSION,
        "mcp_server_name": SERVER_NAME,
        "mcp_server_version": MCP_SERVER_VERSION,
        "$os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_arch": platform.machine(),
        "in_virtual_env": sys.prefix != sys.base_prefix,
        "timezone_offset": ftz,
        "run_context": rc,
        "agent_name": agent,
        "discovery_channel": "direct",
        "install_source": "uvx" if "uv" in sys.executable else "pip",
        "session_id": SESSION_ID,
        "has_ever_worked": True,
        "mcp_client_name": rc,
        "mcp_client_version": "unknown",
        "mcp_protocol_version": "2024-11-05",
        "client_capabilities": {},
        "traceparent": "",
        "trace_id": "",
        "span_id": "",
        "$process_person_profile": False,
    }

_QUEUE: list[Dict[str, Any]] = []
_LOCK = threading.Lock()
_WORKER: Optional[threading.Thread] = None
_STOP = threading.Event()

def _send_sync(payload: Dict[str, Any]):
    if _telemetry_disabled():
        return
    data = json.dumps(payload).encode()
    for url in GATEWAY_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"llm-crawler-audit-telemetry/{MCP_SERVER_VERSION}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.0) as r:
                if r.status in (200, 201, 204):
                    break
        except Exception:
            continue

def _pump():
    while not _STOP.is_set():
        with _LOCK:
            batch, _QUEUE[:] = _QUEUE[:], []
        for e in batch:
            _send_sync(e)
        time.sleep(0.5)

def _ensure():
    global _WORKER
    if _WORKER is None or not _WORKER.is_alive():
        _WORKER = threading.Thread(target=_pump, daemon=True)
        _WORKER.start()

def track_event(name: str, props: Optional[Dict[str, Any]] = None):
    if _telemetry_disabled():
        return
    base = _env_meta()
    if props:
        base.update(scrub_props(props))
    if _is_synthetic_client(str(base.get("mcp_client_name", ""))):
        return
    with _LOCK:
        _QUEUE.append({"event": name, "distinct_id": DISTINCT_ID, "properties": base})
    _ensure()

def track_tool_call(
    tool_name: str,
    duration_ms: float,
    status: str = "success",
    rows_returned: int = 0,
    result_chars: int = 0,
    intent: Optional[str] = None,
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    cat: Optional[str] = None,
    msg: Optional[str] = None,
):
    actual_cat = error_category or cat or "APIError"
    actual_msg = error_message or msg or "failed"
    props: Dict[str, Any] = {
        "tool_name": tool_name,
        "status": status if status in ("success", "error", "warning") else "error",
        "latency_ms": max(0, int(duration_ms)),
        "rows_returned": max(0, int(rows_returned)),
        "result_chars": max(0, int(result_chars)),
    }
    if intent:
        props["intent"] = str(intent)[:300]
    if status != "success":
        props["error_category"] = actual_cat
        props["error_message"] = str(actual_msg)[:250]
    track_event("tool_executed", props)

def flush_and_close():
    _STOP.set()
    with _LOCK:
        batch, _QUEUE[:] = _QUEUE[:], []
    for e in batch:
        _send_sync(e)

atexit.register(flush_and_close)
