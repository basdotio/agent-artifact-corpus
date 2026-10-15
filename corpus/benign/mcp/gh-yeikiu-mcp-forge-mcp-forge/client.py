"""A tiny stdio MCP client, used by ``mcp-forge doctor`` and by your tests.

It launches any MCP server command as a subprocess and speaks JSON-RPC to it,
so you can assert on real protocol traffic instead of calling your handlers
directly::

    with StdioClient([sys.executable, "server.py"]) as client:
        info = client.initialize()
        tools = client.list_tools()
        result = client.call_tool("temperature", {"city": "Las Palmas"})
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from typing import Any

__all__ = ["StdioClient", "ProtocolError"]


class ProtocolError(RuntimeError):
    """The server answered with a JSON-RPC error or broke the protocol."""


class StdioClient:
    def __init__(self, command: list[str], *, cwd: str | None = None,
                 env: dict[str, str] | None = None, timeout: float = 20.0) -> None:
        self.command = command
        self.timeout = timeout
        self._next_id = 0
        self.stderr: list[str] = []
        #: lines the server wrote to stdout that were not JSON-RPC at all
        self.noise: list[str] = []
        self.process = subprocess.Popen(  # noqa: S603 - the caller chooses the command
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._drain = threading.Thread(target=self._read_stderr, daemon=True)
        self._drain.start()

    # ------------------------------------------------------------- plumbing

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        for line in self.process.stderr:
            self.stderr.append(line.rstrip("\n"))

    def stderr_tail(self, limit: int = 160) -> str:
        """Last stderr line, trimmed -- enough to diagnose, short enough to paste."""
        if not self.stderr:
            return "(empty)"
        line = self.stderr[-1].strip()
        return line[:limit] + ("..." if len(line) > limit else "")

    def send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a request and return its ``result`` (raises on JSON-RPC error)."""
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            request["params"] = params
        response = self._exchange(request)
        if "error" in response:
            error = response["error"]
            raise ProtocolError(f"{method} -> [{error.get('code')}] {error.get('message')}")
        return response.get("result")

    def send_raw(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send an arbitrary message and return the raw response (errors included)."""
        return self._exchange(request)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def send_text(self, text: str) -> dict[str, Any]:
        """Write a raw line (even invalid JSON) and read back one response."""
        assert self.process.stdin is not None
        self.process.stdin.write(text + "\n")
        self.process.stdin.flush()
        return self._read_one(f"raw line {text[:30]!r}")

    def _exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        self._write(request)
        return self._read_one(f"{request.get('method')!r}")

    def _read_one(self, what: str) -> dict[str, Any]:
        """Read stdout until a JSON-RPC message arrives; anything else is noise."""
        assert self.process.stdout is not None
        result: dict[str, Any] = {}

        def read() -> None:
            while True:
                line = self.process.stdout.readline()  # type: ignore[union-attr]
                if not line:  # EOF: the server died
                    return
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    result["value"] = json.loads(stripped)
                except json.JSONDecodeError:
                    self.noise.append(stripped)
                    continue
                return

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        reader.join(self.timeout)
        if "value" not in result:
            detail = "the server closed stdout" if self.process.poll() is not None \
                else f"no response within {self.timeout}s"
            raise ProtocolError(
                f"{detail} for {what}. "
                f"stdout noise: {self.noise[-2:] or '(none)'}. "
                f"last stderr: {self.stderr_tail()}"
            )
        return result["value"]

    def _write(self, message: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        if self.process.poll() is not None:
            raise ProtocolError(
                f"server exited with code {self.process.returncode}. "
                f"last stderr: {self.stderr_tail()}"
            )
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    # ----------------------------------------------------------------- MCP

    def initialize(self, protocol_version: str = "2025-06-18") -> dict[str, Any]:
        result = self.send("initialize", {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "mcp-forge-doctor", "version": "1.0.0"},
        })
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        return self.send("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.send("tools/call", {"name": name, "arguments": arguments or {}})

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.wait(timeout=5)
        except Exception:  # noqa: BLE001 - shutting down is best effort
            self.process.kill()

    def __enter__(self) -> "StdioClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def python_server(path: str) -> list[str]:
    """Command that runs a Python MCP server script with the current interpreter."""
    return [sys.executable, path]
