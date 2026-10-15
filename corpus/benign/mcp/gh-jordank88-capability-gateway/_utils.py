"""
_utils.py — shared helpers every tool module imports.

Not a tool (no run()). Gives every tool the same I/O contract:

    run(args: dict) -> dict            # the only thing the gateway calls
    ok(**fields)  -> {"success": True, ...}
    fail(msg, error_code=None, **fields) -> {"success": False, "error": msg, ...}

…plus a subprocess wrapper that can't hang its caller, and a credential
lookup that prefers the OS keyring over environment variables.
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Optional: load a .env next to this file so tools can read secrets/config
# from it. python-dotenv is not required — without it, real environment
# variables still work.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_args(defaults: dict | None = None) -> dict:
    """
    Read JSON args from the first CLI argument or stdin (piped only), so
    every tool module is also runnable on its own:

        python tools/git_status.py '{"repo": "."}'

    Merges with defaults so callers only need to handle present keys.
    """
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        raw = ""
    args = json.loads(raw) if raw.strip() else {}
    if defaults:
        merged = dict(defaults)
        merged.update(args)
        return merged
    return args


def emit(result: dict) -> None:
    """Write JSON result to stdout and flush."""
    print(json.dumps(result), flush=True)


def ok(**kwargs) -> dict:
    """Build a success result dict."""
    return {"success": True, **kwargs}


def fail(message: str, error_code: str | None = None, **kwargs) -> dict:
    """Build a failure result dict. error_code is what _tool_error_enrichment keys on."""
    result = {"success": False, "error": message}
    if error_code:
        result["error_code"] = error_code
    result.update(kwargs)
    return result


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def resolve_path(p: str, must_exist: bool = True) -> Path:
    """Resolve a path to absolute; raise FileNotFoundError if must_exist and it doesn't."""
    resolved = Path(p).resolve()
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"PathNotFound: {p}")
    return resolved


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

KEYRING_SERVICE = os.environ.get("CAPABILITY_GATEWAY_KEYRING_SERVICE", "capability-gateway")
_keyring_available: bool | None = None  # cached after first attempt


def get_secret(key: str, default: str | None = None) -> str | None:
    """
    Resolve a credential by name. Resolution order:
      1. OS keyring (Windows Credential Manager, macOS Keychain, SecretService)
         under the service name KEYRING_SERVICE — if `keyring` is installed
      2. Environment variable (including anything loaded from .env)
      3. `default`

    Prefer this over os.environ in tools: secrets can then move out of a
    plaintext .env without touching any tool code.
    """
    global _keyring_available

    if _keyring_available is not False:
        try:
            import keyring as _kr
            value = _kr.get_password(KEYRING_SERVICE, key)
            _keyring_available = True
            if value is not None:
                return value
        except Exception:
            _keyring_available = False  # don't retry on every call

    value = os.environ.get(key)
    if value is not None:
        return value
    return default


# ---------------------------------------------------------------------------
# Subprocess
# ---------------------------------------------------------------------------

def run_cmd(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: int = 30,
    env: dict | None = None,
) -> dict:
    """
    Run a subprocess and return {stdout, stderr, returncode}. Never raises on
    a non-zero exit; raises RuntimeError on command-not-found or timeout.

    Three details that each cost real debugging time:

    * stdin=DEVNULL — under the MCP stdio transport the gateway's own stdin
      is the JSON-RPC pipe. A child that probes stdin (credential prompts,
      some CLIs' interactive auth flows) can inherit it and hang forever.
    * CREATE_NO_WINDOW (Windows) — when the parent has no console (e.g.
      launched by pythonw / a scheduler), each console child gets a fresh
      console window that flashes on screen. Redirecting output doesn't
      prevent that; only this flag does.
    * The timeout bounds OUR wait, not just the child. subprocess.run's own
      timeout kills the child and then drains its pipes with an *untimed*
      communicate(), which hangs if a grandchild still holds the handles.
      Running it in a daemon thread and joining with a deadline means
      run_cmd itself can never block past timeout + grace.
    """
    merged_env = {**os.environ, **(env or {})}
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    box: dict = {}

    def _target() -> None:
        try:
            box["result"] = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                errors="replace",  # an undecodable byte becomes U+FFFD, not an exception
                timeout=timeout,
                env=merged_env,
                stdin=subprocess.DEVNULL,
                creationflags=no_window,
            )
        except FileNotFoundError:
            box["error"] = "not_found"
        except subprocess.TimeoutExpired:
            box["error"] = "timeout"
        except Exception as exc:  # pragma: no cover — re-raised as-is below
            box["error"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    grace = 10
    thread.join(timeout=timeout + grace)

    if thread.is_alive():
        raise RuntimeError(
            f"TimeoutExceeded: '{' '.join(cmd)}' exceeded {timeout}s "
            f"(subprocess did not return even {grace}s past its own timeout)"
        )

    error = box.get("error")
    if error == "not_found":
        raise RuntimeError(f"CommandNotFound: '{cmd[0]}' not found in PATH")
    if error == "timeout":
        raise RuntimeError(f"TimeoutExceeded: '{' '.join(cmd)}' exceeded {timeout}s")
    if isinstance(error, Exception):
        raise error

    result = box["result"]
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
