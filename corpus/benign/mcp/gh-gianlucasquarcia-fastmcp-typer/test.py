"""
Integration test for the FastMCP Test MCP Server.

Starts the server locally on HTTP, connects with an MCP client, and
exercises every tool through the protocol — exactly as a real caller would.

Usage:
    # Default (auto-picks a free port):
    python test.py

    # Custom query for the weather tool:
    python test.py --latitude 48.85 --longitude 2.35

    # Specify an explicit port:
    python test.py --port 9200
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import IO, Any

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_DIR = Path(__file__).resolve().parent
SERVER_PY = SERVER_DIR / "mcp_server_cli.py"
STARTUP_TIMEOUT = 30
TOOL_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    """Return a free TCP port on localhost, chosen by the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _is_port_in_use(port: int) -> bool:
    """Return True if something is already listening on the given localhost port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_result(result) -> Any:
    """Pretty-print a tool result and return the parsed JSON."""
    try:
        text = result.content[0].text
        parsed = json.loads(text)
        print(json.dumps(parsed, indent=2, default=str)[:3000])
        return parsed
    except (json.JSONDecodeError, IndexError, AttributeError):
        print(result.content[0].text[:3000])
        return None


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


class ServerHandle:
    """A running server subprocess plus its captured stderr.

    Output is never sent to subprocess.PIPE. A pipe has a small OS buffer;
    if the child writes enough (e.g. request logs) before anyone reads it,
    the child blocks on write() — which can make the server unresponsive to
    HTTP requests, and can also deadlock a later blocking read() of the
    other stream. stdout is discarded and stderr goes to a temp file, so
    the child never blocks on output regardless of how much it logs.
    """

    def __init__(
        self,
        proc: subprocess.Popen,
        stderr_file: IO[bytes],
        resources: contextlib.ExitStack,
    ):
        self.proc = proc
        self._stderr_file = stderr_file
        self._resources = resources

    def read_stderr(self) -> str:
        """Read everything the server has written to stderr so far."""
        self._stderr_file.seek(0)
        data = self._stderr_file.read()
        return data.decode(errors="replace") if data else ""

    def close(self) -> None:
        self._resources.close()


def _start_server(port: int, env_overrides: dict[str, str]) -> ServerHandle:
    """Launch the MCP server as a subprocess on the given port."""
    env = {**os.environ, **env_overrides}
    # On Windows, isolate the child in its own process group so that signaling
    # it to stop later (CTRL_BREAK_EVENT) does not also terminate this script.
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with contextlib.ExitStack() as stack:
        stderr_file = stack.enter_context(tempfile.TemporaryFile())
        proc = subprocess.Popen(
            [
                sys.executable,
                str(SERVER_PY),
                "run",
                "--transport",
                "http",
                "--port",
                str(port),
            ],
            cwd=SERVER_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            creationflags=creationflags,
        )
        # Hand ownership of the temp file to the handle (closed in _stop_server).
        return ServerHandle(proc, stderr_file, stack.pop_all())


async def _wait_for_server(url: str, timeout: float = STARTUP_TIMEOUT) -> None:
    """Poll the server until it accepts connections."""
    deadline = time.monotonic() + timeout
    async with httpx2.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    return
            except httpx2.ConnectError:
                pass
            await asyncio.sleep(0.3)
    raise TimeoutError(f"Server did not start within {timeout}s")


def _stop_server(handle: ServerHandle) -> None:
    """Stop the server subprocess (and any children it spawned).

    On Windows, a venv's python.exe can be a launcher stub that execs the
    real interpreter as a *child* process. By the time that stub has exited
    (gracefully or not), the OS may have already severed the parent/child
    link, so the grandchild running the actual server becomes an orphan that
    taskkill can no longer find via the tree. To avoid that race, kill the
    whole process tree immediately while the relationship is still live,
    rather than waiting for a graceful shutdown first.
    """
    proc = handle.proc
    try:
        if os.name == "nt":
            _kill_process_tree(proc)
            proc.wait()
        elif proc.poll() is None:
            try:
                proc.send_signal(signal.SIGTERM)
            except (ValueError, OSError):
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    finally:
        handle.close()


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Force-kill a process and all of its descendants, if still alive."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    elif proc.poll() is None:
        proc.kill()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


async def test_list_tools(session: ClientSession) -> list[str]:
    """List available tools and return their names."""
    _section("LIST TOOLS")
    tools_result = await session.list_tools()
    names = []
    for t in tools_result.tools:
        print(f"  - {t.name}: {(t.description or '')[:80]}")
        names.append(t.name)
    print(f"\n  Total: {len(names)} tools")
    assert "sort_numbers" in names, "Expected 'sort_numbers' tool not found"
    assert "open_meteo_current_forecast" in names, (
        "Expected 'open_meteo_current_forecast' tool not found"
    )
    print("  [PASS] expected tools registered")
    return names


async def test_sort_numbers(session: ClientSession, numbers: list[int]) -> list:
    """Call the sort_numbers tool and validate the response."""
    _section(f"TEST: sort_numbers(numbers={numbers})")

    t0 = time.time()
    result = await session.call_tool("sort_numbers", {"numbers": numbers})
    elapsed = time.time() - t0

    parsed = _print_result(result)
    assert parsed == sorted(numbers), f"Expected sorted list, got {parsed!r}"

    print(f"\n  Elapsed: {elapsed:.2f}s")
    print("  [PASS] sort_numbers returned correctly sorted list")
    return parsed


async def test_open_meteo_current_forecast(
    session: ClientSession, latitude: float, longitude: float
) -> dict:
    """Call the open_meteo_current_forecast tool and validate the response shape."""
    _section("TEST: open_meteo_current_forecast")

    t0 = time.time()
    result = await session.call_tool(
        "open_meteo_current_forecast", {"latitude": latitude, "longitude": longitude}
    )
    elapsed = time.time() - t0

    parsed = _print_result(result)
    assert parsed is not None, "Failed to parse tool response as JSON"
    assert "current" in parsed, "Expected 'current' key in forecast response"

    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"  current: {parsed.get('current')}")
    print("  [PASS] open_meteo_current_forecast returned valid response")
    return parsed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_tests(
    port: int, numbers: list[int], latitude: float, longitude: float
) -> bool:
    """Connect to the local server and run all tests."""
    mcp_url = f"http://localhost:{port}/mcp"

    async with (
        httpx2.AsyncClient(timeout=httpx2.Timeout(TOOL_TIMEOUT)) as http,
        streamable_http_client(mcp_url, http_client=http) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        await test_list_tools(session)
        await test_sort_numbers(session, numbers)
        await test_open_meteo_current_forecast(session, latitude, longitude)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Integration test for the FastMCP Test MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to run the test server on (default: auto-pick a free port)",
    )
    parser.add_argument(
        "--numbers",
        "-n",
        type=int,
        nargs="+",
        default=[5, 2, 9, 1, 5, 6],
        help="Numbers to sort (default: 5 2 9 1 5 6)",
    )
    parser.add_argument(
        "--latitude",
        type=float,
        default=37.7749,
        help="Latitude for the forecast tool (default: 37.7749)",
    )
    parser.add_argument(
        "--longitude",
        type=float,
        default=-122.4194,
        help="Longitude for the forecast tool (default: -122.4194)",
    )

    args = parser.parse_args()

    port = args.port
    if port is None:
        port = _find_free_port()
    elif _is_port_in_use(port):
        print(f"  [FAIL] Port {port} is already in use by another process.")
        print(
            "  Choose a different port with --port, or omit --port to auto-select a free one."
        )
        sys.exit(1)

    # --- Start server, run tests, stop server ---
    _section("Starting FastMCP Test MCP Server")
    print(f"  port:    {port}")
    print(f"  server:  {SERVER_PY}")

    handle = _start_server(port, {})
    try:
        asyncio.run(_wait_for_server(f"http://localhost:{port}/mcp"))
        print("  Server is up.\n")

        ok = asyncio.run(
            run_tests(
                port=port,
                numbers=args.numbers,
                latitude=args.latitude,
                longitude=args.longitude,
            )
        )

        _section("DONE — all tests passed" if ok else "DONE — some tests failed")

    except TimeoutError:
        print(f"\n  [FAIL] Server did not start within {STARTUP_TIMEOUT}s")
        stderr = handle.read_stderr()
        if stderr:
            print(f"\n  Server stderr:\n{stderr[:2000]}")
        sys.exit(1)

    except Exception as exc:  # noqa: BLE001 - top-level CLI: report any failure
        print(f"\n  [FAIL] {exc}")
        sys.exit(1)

    finally:
        _stop_server(handle)
        print("  Server stopped.")


if __name__ == "__main__":
    main()
