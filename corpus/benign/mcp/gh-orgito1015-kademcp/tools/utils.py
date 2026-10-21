"""
Shared utilities: subprocess command runner and file helpers.

NOTE ON ISOLATION: run_cmd / run_python execute external commands and arbitrary
code with the permissions of the MCP server process. There is no in-process
OS-level sandbox (no seccomp, namespaces, or filesystem jail). The intended
isolation boundary is the Docker container this server ships in, which runs as
the unprivileged `ctf` user. Do not run this server directly on a host you care
about. Set KADEMCP_WORKSPACE to confine user-supplied file/binary *paths* to a
directory (see resolve_workspace_path); this restricts path access but does not
sandbox code execution.
"""

import asyncio
import os
import signal
import tempfile

TIMEOUT = 20  # seconds per tool call
# The largest per-request timeout a web tool may ask for. Kept below TIMEOUT so
# the request finishes (or errors) before run_cmd's global kill fires.
MAX_HTTP_TIMEOUT = TIMEOUT - 2

# Optional path confinement. When set, user-supplied filepaths must resolve to
# a location inside this directory. Unset -> paths are unrestricted (legacy).
WORKSPACE = os.environ.get("KADEMCP_WORKSPACE")


def clamp_int(value, default: int, minimum: int, maximum: int) -> int:
    """Coerce value to an int within [minimum, maximum], falling back to default.

    Schema bounds aren't enforced by every MCP client, so numeric fields that
    reach shell utilities are clamped here as a defensive second line.
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))


def resolve_workspace_path(path: str) -> tuple[str | None, str | None]:
    """Return (real_path, error). Enforces KADEMCP_WORKSPACE confinement if set.

    Returns (None, err) if the path escapes the workspace. Symlinks are resolved
    (realpath) before the check so a symlink inside the workspace can't point out.
    """
    real = os.path.realpath(path)
    if WORKSPACE:
        root = os.path.realpath(WORKSPACE)
        if real != root and not real.startswith(root + os.sep):
            return None, f"[error] path '{path}' is outside the allowed workspace"
    return real, None


async def run_cmd(*args: str, input_data: bytes | None = None, timeout: int = TIMEOUT) -> str:
    """
    Run a command as a subprocess, capturing stdout + stderr.
    Returns combined output as a string, or an error message on failure.
    """
    proc = None
    try:
        # start_new_session=True puts the child in its own process group so a
        # timeout can kill the whole tree (child + any descendants it spawned),
        # not just the immediate child.
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE if input_data else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=input_data), timeout=timeout
        )
        out = stdout.decode(errors="replace")
        err = stderr.decode(errors="replace")
        combined = out
        if err.strip():
            combined += f"\n[stderr]\n{err}"
        return combined.strip() or "(no output)"
    except asyncio.TimeoutError:
        if proc is not None:
            # Kill the entire process group, then reap so we don't leak zombies.
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
        return f"[error] command timed out after {timeout}s"
    except FileNotFoundError as e:
        return f"[error] tool not found: {e}. Is it installed?"
    except Exception as e:
        return f"[error] {e}"


async def run_python(code: str, timeout: int = TIMEOUT) -> str:
    """Execute Python code in a subprocess and return output.

    NOT sandboxed: the code runs with the server process's permissions. Isolation
    relies on the container. See the module docstring.
    """
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        fname = f.name
    try:
        result = await run_cmd("python3", fname, timeout=timeout)
    finally:
        os.unlink(fname)
    return result


def write_tempfile(data: bytes, suffix: str = "") -> str:
    """Write bytes to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        return f.name


def decode_input(raw: str, assume_hex: bool = True) -> bytes:
    """
    Accept hex-encoded (0x... or plain hex) or raw string input.
    Returns bytes.

    A leading "0x"/"0X" is always treated as an explicit hex marker.
    Without that prefix, `assume_hex` controls whether an ambiguous
    hex-looking string (e.g. "dead", "beef") is auto-decoded as hex.
    Set assume_hex=False for values a user is likely to type literally,
    like a known XOR key, so "dead" isn't silently reinterpreted as
    2 raw bytes instead of the 4 ASCII bytes the user meant.
    """
    # Only strip for the hex-prefix check and hex-parse attempt; the raw/ASCII
    # fallback returns the *original* string so boundary whitespace that is
    # meaningful (e.g. in an XOR key or ciphertext) is preserved.
    stripped = raw.strip()
    if stripped.startswith("0x") or stripped.startswith("0X"):
        return bytes.fromhex(stripped[2:])
    if assume_hex:
        try:
            return bytes.fromhex(stripped)
        except ValueError:
            return raw.encode()
    return raw.encode()
