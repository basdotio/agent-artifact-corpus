# SPDX-License-Identifier: MIT
"""Anonymous usage telemetry: identity, environment signals, and transport to
the gateway (https://web-vitals.builditwithai.xyz/e). Opt-out and privacy: see README."""

from __future__ import annotations

import atexit
import json
import os
import platform
import signal
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

GATEWAY_URLS = [
    "https://web-vitals.builditwithai.xyz/e",
    "https://core-web-vitals-mcp-install-telemetry.reachsuren.workers.dev/e",
]
SCHEMA_VERSION = 2
SERVER_NAME = "core-web-vitals-mcp"

STATUS_OK = {"success", "warning", "cancelled"}
STATUS_ERR = {"error", "exception"}
ERROR_CATEGORIES = {
    "APIError", "ValidationError", "SchemaHallucination", "IAMError",
    "TimeoutError", "RateLimitError", "NotFoundError", "SourceUnavailable",
    "MissingApiKey", "InternalError", "Cancelled", "InitError"
}

try:
    import importlib.metadata
    MCP_SERVER_VERSION = importlib.metadata.version("core-web-vitals-mcp")
except Exception:
    try:
        from core_web_vitals_mcp import __version__ as MCP_SERVER_VERSION
    except Exception:
        MCP_SERVER_VERSION = "0.1.0"


def _telemetry_disabled() -> bool:
    for var in (
        "CORE_WEB_VITALS_TELEMETRY",
        "WEB_VITALS_TELEMETRY",
    ):
        if os.getenv(var, "").lower() in ("false", "0", "off"):
            return True
    for var in (
        "MCP_TELEMETRY_OPT_OUT",
        "DISABLE_TELEMETRY",
        "DO_NOT_TRACK",
        "NO_TELEMETRY",
    ):
        if os.getenv(var, "").lower() in ("1", "true", "yes", "on"):
            return True
    return False


TELEMETRY_DISABLED = _telemetry_disabled()
INTERNAL_RUN = os.getenv("CORE_WEB_VITALS_INTERNAL", "").lower() in ("1", "true", "yes")


def _init_anonymous_identity():
    try:
        config_dir = Path.home() / ".core_web_vitals_mcp"
        id_file = config_dir / "installation_id"

        if TELEMETRY_DISABLED:
            if id_file.exists():
                return id_file.read_text(encoding="utf-8").strip(), False
            return f"anon_{uuid.uuid4()}", False

        if id_file.exists():
            return id_file.read_text(encoding="utf-8").strip(), False

        config_dir.mkdir(parents=True, exist_ok=True)
        new_id = f"inst_{uuid.uuid4()}"
        id_file.write_text(new_id, encoding="utf-8")
        return new_id, True
    except Exception:
        return f"anon_{uuid.uuid4()}", False


DISTINCT_ID, IS_FIRST_INSTALL = _init_anonymous_identity()
SESSION_ID = f"sess_{uuid.uuid4()}"


def _get_env_metadata() -> Dict[str, Any]:
    tz_offset = time.strftime("%z")
    formatted_tz = f"{tz_offset[:3]}:{tz_offset[3:]}" if len(tz_offset) == 5 else "+00:00"

    in_venv = sys.prefix != sys.base_prefix or bool(os.getenv("VIRTUAL_ENV")) or bool(os.getenv("CONDA_PREFIX"))

    run_context = "cli"
    agent_name = "unknown"
    if os.getenv("CLAUDE_CODE") or os.getenv("CLAUDE_PROJECT_DIR"):
        run_context = "claude_code"
        agent_name = "claude"
    elif os.getenv("CURSOR_TRACE") or os.getenv("CURSOR_SESSION"):
        run_context = "cursor"
        agent_name = "cursor"
    elif os.getenv("VSCODE_PID"):
        run_context = "vscode"
        agent_name = "copilot"
    elif os.getenv("ANTIGRAVITY_SESSION") or os.getenv("GEMINI_CLI"):
        run_context = "antigravity"
        agent_name = "antigravity"

    return {
        "schema_version": SCHEMA_VERSION,
        "mcp_server_name": SERVER_NAME,
        "mcp_server_version": MCP_SERVER_VERSION,
        "$os": platform.system(),
        "python_version": platform.python_version(),
        "cpu_arch": platform.machine(),
        "in_virtual_env": in_venv,
        "timezone_offset": formatted_tz,
        "run_context": run_context,
        "agent_name": agent_name,
        "discovery_channel": "direct",
        "install_source": "uvx" if "uv" in sys.executable else "pip",
        "session_id": SESSION_ID,
        "has_ever_worked": True,
        "mcp_client_name": run_context,
        "mcp_client_version": "unknown",
        "mcp_protocol_version": "2026-07-28",
        "client_capabilities": {},
        "traceparent": "",
        "trace_id": "",
        "span_id": "",
        "$process_person_profile": False,
    }


_EVENT_QUEUE: List[Dict[str, Any]] = []
_QUEUE_LOCK = threading.Lock()
_WORKER_THREAD: Optional[threading.Thread] = None
_SHUTDOWN = threading.Event()


def _flush_queue():
    while not _SHUTDOWN.is_set():
        batch = []
        with _QUEUE_LOCK:
            if _EVENT_QUEUE:
                batch = _EVENT_QUEUE[:]
                _EVENT_QUEUE.clear()
        if batch:
            for event in batch:
                _send_event_sync(event)
        time.sleep(0.5)


def _send_event_sync(payload: Dict[str, Any]):
    if TELEMETRY_DISABLED:
        return
    data = json.dumps(payload).encode("utf-8")
    for url in GATEWAY_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": f"core-web-vitals-mcp/{MCP_SERVER_VERSION}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status in (200, 201, 204):
                    break
        except Exception:
            continue


def _ensure_worker():
    global _WORKER_THREAD
    if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
        _WORKER_THREAD = threading.Thread(target=_flush_queue, daemon=True)
        _WORKER_THREAD.start()


def track_event(event_name: str, properties: Optional[Dict[str, Any]] = None):
    if TELEMETRY_DISABLED:
        return

    props = _get_env_metadata()
    if properties:
        props.update(properties)
    if INTERNAL_RUN:
        props["internal_run"] = True

    payload = {
        "event": event_name,
        "distinct_id": DISTINCT_ID,
        "properties": props,
    }

    with _QUEUE_LOCK:
        _EVENT_QUEUE.append(payload)
    _ensure_worker()


def classify_exception(exc: Optional[BaseException] = None) -> str:
    """Classifies an exception into the canonical MCP Telemetry error taxonomy."""
    if exc is None:
        return "InternalError"
    err_str = str(exc).lower()
    err_cls = exc.__class__.__name__.lower()

    if "validation" in err_cls or "valueerror" in err_cls or "typeerror" in err_cls:
        return "ValidationError"
    if "timeout" in err_cls or "timed out" in err_str:
        return "TimeoutError"
    if "ratelimit" in err_cls or "429" in err_str or "too many requests" in err_str:
        return "RateLimitError"
    if "notfound" in err_cls or "404" in err_str or "not found" in err_str or "no record found" in err_str:
        return "NotFoundError"
    if "unauthorized" in err_str or "forbidden" in err_str or "401" in err_str or "403" in err_str or "permission" in err_str:
        return "IAMError"
    if "connection" in err_str or "network" in err_str or "unavailable" in err_str or "502" in err_str or "503" in err_str or "504" in err_str:
        return "SourceUnavailable"
    if "cancelled" in err_cls or "cancel" in err_str:
        return "Cancelled"
    if "apikey" in err_str or "api_key" in err_str or "token" in err_str or "key missing" in err_str:
        return "MissingApiKey"
    if "schema" in err_str:
        return "SchemaHallucination"
    return "APIError"


_SESSION_START = time.time()
_TOOL_SEQUENCE: List[str] = []
_TOOL_COUNTS: Dict[str, int] = {}
_EXIT_REASON = "clean"
_EXIT_EXCEPTION = None


def _capture_excepthook(exc_type, exc_value, exc_traceback):
    global _EXIT_REASON, _EXIT_EXCEPTION
    _EXIT_REASON = "exception"
    _EXIT_EXCEPTION = exc_type.__name__ if exc_type else "UnknownException"
    if _original_excepthook and callable(_original_excepthook):
        _original_excepthook(exc_type, exc_value, exc_traceback)


_original_excepthook = getattr(sys, "excepthook", None)
sys.excepthook = _capture_excepthook

_original_signals = {}


def _capture_signal(sig, frame):
    global _EXIT_REASON
    _EXIT_REASON = "signal"
    orig = _original_signals.get(sig)
    if callable(orig):
        orig(sig, frame)
    else:
        sys.exit(128 + sig)


try:
    for s in (signal.SIGINT, signal.SIGTERM):
        _original_signals[s] = signal.getsignal(s)
        signal.signal(s, _capture_signal)
except (ValueError, AttributeError):
    pass


def track_tool_call(
    tool_name: str,
    duration_ms: float,
    status: str = "success",
    rows_returned: int = 0,
    result_chars: int = 0,
    intent: Optional[str] = None,
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    custom_props: Optional[Dict[str, Any]] = None,
):
    _TOOL_SEQUENCE.append(tool_name)
    if len(_TOOL_SEQUENCE) > 100:
        _TOOL_SEQUENCE.pop(0)
    _TOOL_COUNTS[tool_name] = _TOOL_COUNTS.get(tool_name, 0) + 1

    latency_int = max(0, int(duration_ms))
    props = {
        "tool_name": tool_name,
        "status": status if status in STATUS_OK | STATUS_ERR else "error",
        "latency_ms": latency_int,
        "duration_ms": latency_int,
        "rows_returned": max(0, int(rows_returned)),
        "result_chars": max(0, int(result_chars)),
    }
    if intent and isinstance(intent, str):
        props["intent"] = intent[:300]
    if status in STATUS_ERR:
        cat = error_category if (error_category and error_category in ERROR_CATEGORIES) else "APIError"
        props["error_category"] = cat
        props["error_message"] = str(error_message)[:250] if error_message else "Execution failed"
    elif error_category:
        props["error_category"] = error_category if error_category in ERROR_CATEGORIES else "InternalError"
        if error_message:
            props["error_message"] = str(error_message)[:250]
    if custom_props:
        props.update(custom_props)

    track_event("tool_executed", props)


def _emit_session_end():
    if TELEMETRY_DISABLED:
        return
    payload = {
        "session_duration_s": int(time.time() - _SESSION_START),
        "tool_sequence": list(_TOOL_SEQUENCE),
        "tool_counts": dict(_TOOL_COUNTS),
        "calls_total": len(_TOOL_SEQUENCE),
        "exit_reason": _EXIT_REASON,
    }
    if _EXIT_EXCEPTION:
        payload["exit_exception"] = _EXIT_EXCEPTION
    track_event("session_end", payload)


def flush_and_close():
    _SHUTDOWN.set()
    batch = []
    with _QUEUE_LOCK:
        batch = _EVENT_QUEUE[:]
        _EVENT_QUEUE.clear()
    for event in batch:
        _send_event_sync(event)


atexit.register(flush_and_close)
atexit.register(_emit_session_end)
