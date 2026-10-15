"""Zero-dependency MCP server runtime (JSON-RPC 2.0 over stdio).

Write a tool as a plain Python function, decorate it, and you have a Model
Context Protocol server that Claude Desktop, Claude Code, Cursor or any other
MCP client can launch::

    from mcp_forge import Server

    app = Server("weather", "1.0.0")

    @app.tool(description="Current temperature for a city.",
              input_schema={"type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"]})
    def temperature(city: str) -> str:
        return f"{city}: 21 C"

    if __name__ == "__main__":
        app.run()

Design notes that matter in production:

* Nothing but JSON-RPC ever reaches stdout. Use :func:`log` for diagnostics;
  a stray ``print()`` is the single most common reason an MCP server fails to
  start inside a client.
* Tool arguments are validated against the declared ``inputSchema`` before the
  handler runs, so handlers never see malformed input.
* Every tool call has a timeout. A hung tool returns an error to the client
  instead of freezing the conversation.
* Exceptions become ``isError`` tool results (the model can read and recover
  from them); protocol mistakes become JSON-RPC errors.
"""

from __future__ import annotations

import inspect
import json
import sys
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any, Callable, IO, Iterable

from .validate import SchemaError, validate

__all__ = ["Server", "Tool", "ToolError", "log", "PROTOCOL_VERSIONS"]

#: Protocol revisions this runtime speaks, newest first.
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

_STDERR_LOCK = threading.Lock()


def log(*parts: Any) -> None:
    """Write a diagnostic line to stderr (never stdout)."""
    message = " ".join(str(p) for p in parts)
    with _STDERR_LOCK:
        print(message, file=sys.stderr, flush=True)


class ToolError(Exception):
    """Raise inside a tool to return a clean error to the model."""


@dataclass
class Tool:
    name: str
    handler: Callable[..., Any]
    description: str = ""
    title: str = ""
    input_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    output_schema: dict[str, Any] | None = None
    timeout: float = 30.0

    def describe(self) -> dict[str, Any]:
        spec: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
        if self.title:
            spec["title"] = self.title
        if self.output_schema:
            spec["outputSchema"] = self.output_schema
        return spec


def _schema_from_signature(handler: Callable[..., Any]) -> dict[str, Any]:
    """Build a permissive object schema from the handler's parameter names."""
    properties: dict[str, Any] = {}
    required: list[str] = []
    hints = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    for parameter in inspect.signature(handler).parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        entry: dict[str, Any] = {}
        json_type = hints.get(parameter.annotation)
        if json_type:
            entry["type"] = json_type
        properties[parameter.name] = entry
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _as_content(result: Any) -> tuple[list[dict[str, Any]], Any]:
    """Normalise a handler return value into (content, structuredContent)."""
    if result is None:
        return [{"type": "text", "text": "ok"}], None
    if isinstance(result, str):
        return [{"type": "text", "text": result}], None
    if isinstance(result, list) and all(isinstance(i, dict) and "type" in i for i in result):
        return result, None
    if isinstance(result, dict) and result.get("type") in {"text", "image", "audio", "resource"}:
        return [result], None
    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    structured = result if isinstance(result, dict) else {"result": result}
    return [{"type": "text", "text": text}], structured


class Server:
    """An MCP server: register tools, then :meth:`run` it over stdio."""

    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        *,
        instructions: str = "",
        max_workers: int = 4,
        default_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self.version = version
        self.instructions = instructions
        self.max_workers = max(1, int(max_workers))
        self.default_timeout = default_timeout
        self.tools: dict[str, Tool] = {}
        self.initialized = False
        self._pool: ThreadPoolExecutor | None = None
        self._write_lock = threading.Lock()

    # ---------------------------------------------------------------- tools

    def tool(
        self,
        name: str | None = None,
        *,
        description: str = "",
        title: str = "",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that registers a function as an MCP tool."""

        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or handler.__name__
            if tool_name in self.tools:
                raise ValueError(f"duplicate tool name: {tool_name}")
            doc = description or (inspect.getdoc(handler) or "").strip()
            self.tools[tool_name] = Tool(
                name=tool_name,
                handler=handler,
                description=doc,
                title=title,
                input_schema=input_schema or _schema_from_signature(handler),
                output_schema=output_schema,
                timeout=self.default_timeout if timeout is None else timeout,
            )
            return handler

        return decorator

    def add_tool(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self.tools[tool.name] = tool

    # ------------------------------------------------------------- dispatch

    def dispatch(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC message. Returns the response, or ``None`` for notifications."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _error(message.get("id") if isinstance(message, dict) else None,
                          INVALID_REQUEST, "Expected a JSON-RPC 2.0 message")

        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(request_id, INVALID_PARAMS, "params must be an object")

        if request_id is None:  # notification
            if method == "notifications/initialized":
                self.initialized = True
            return None

        if method == "initialize":
            return _ok(request_id, self._initialize(params))
        if method == "ping":
            return _ok(request_id, {})
        if method == "tools/list":
            tools = [t.describe() for t in self.tools.values()]
            return _ok(request_id, {"tools": tools})
        if method == "tools/call":
            return self._call(request_id, params)
        if isinstance(method, str) and method.startswith("notifications/"):
            return None
        return _error(request_id, METHOD_NOT_FOUND, f"Unknown method: {method!r}")

    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        result: dict[str, Any] = {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.name, "version": self.version},
        }
        if self.instructions:
            result["instructions"] = self.instructions
        return result

    def _call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or name not in self.tools:
            return _error(request_id, INVALID_PARAMS, f"Unknown tool: {name!r}")
        if not isinstance(arguments, dict):
            return _error(request_id, INVALID_PARAMS, "arguments must be an object")

        tool = self.tools[name]
        try:
            validate(arguments, tool.input_schema)
        except SchemaError as exc:
            return _error(request_id, INVALID_PARAMS, f"Invalid arguments for {name}: {exc}")

        try:
            result = self._run(tool, arguments)
        except FutureTimeout:
            log(f"[{self.name}] tool {name} timed out after {tool.timeout}s")
            return _ok(request_id, _tool_error(f"Tool {name!r} timed out after {tool.timeout}s"))
        except ToolError as exc:
            return _ok(request_id, _tool_error(str(exc)))
        except TypeError as exc:
            return _error(request_id, INVALID_PARAMS, f"Invalid arguments for {name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - tool failures are data, not crashes
            log(f"[{self.name}] tool {name} raised:\n{traceback.format_exc()}")
            return _ok(request_id, _tool_error(f"{type(exc).__name__}: {exc}"))

        content, structured = _as_content(result)
        payload: dict[str, Any] = {"content": content, "isError": False}
        if structured is not None and tool.output_schema:
            payload["structuredContent"] = structured
        return _ok(request_id, payload)

    def _run(self, tool: Tool, arguments: dict[str, Any]) -> Any:
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=self.max_workers,
                                            thread_name_prefix=f"{self.name}-tool")
        future = self._pool.submit(tool.handler, **arguments)
        return future.result(timeout=tool.timeout)

    # ----------------------------------------------------------------- stdio

    def run(self, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> None:
        """Serve over stdio until stdin closes."""
        source: Iterable[str] = stdin if stdin is not None else sys.stdin
        sink = stdout if stdout is not None else sys.stdout
        log(f"[{self.name}] v{self.version} ready with {len(self.tools)} tool(s)")
        for line in source:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self._write(sink, _error(None, PARSE_ERROR, f"Invalid JSON: {exc}"))
                continue
            try:
                response = self.dispatch(message)
            except Exception as exc:  # noqa: BLE001 - never die on one bad request
                log(f"[{self.name}] dispatch failure:\n{traceback.format_exc()}")
                response = _error(message.get("id") if isinstance(message, dict) else None,
                                  INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")
            if response is not None:
                self._write(sink, response)
        if self._pool is not None:
            self._pool.shutdown(wait=False)
        log(f"[{self.name}] stdin closed, exiting")

    def _write(self, sink: IO[str], payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._write_lock:
            sink.write(line + "\n")
            sink.flush()


def _ok(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}
