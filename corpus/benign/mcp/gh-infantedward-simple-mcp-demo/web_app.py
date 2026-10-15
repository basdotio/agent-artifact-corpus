import json
from threading import Lock
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2025-06-18"


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class MCPHttpClient:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url
        self.session = requests.Session()
        self.session_id: str | None = None
        self.protocol_version = PROTOCOL_VERSION
        self._lock = Lock()
        self._request_id = 1

    def _next_id(self) -> int:
        request_id = self._request_id
        self._request_id += 1
        return request_id

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        return headers

    def _extract_json_rpc_response(self, response: requests.Response) -> dict[str, Any]:
        content_type = response.headers.get("Content-Type", "")

        if content_type.startswith("application/json"):
            return response.json()

        if content_type.startswith("text/event-stream"):
            for chunk in response.text.split("\n\n"):
                for line in chunk.splitlines():
                    if line.startswith("data: "):
                        return json.loads(line.removeprefix("data: "))

        raise ValueError(f"Unsupported response content type: {content_type}")

    def _post(self, message: dict[str, Any]) -> dict[str, Any] | None:
        response = self.session.post(
            self.server_url,
            headers=self._headers(),
            json=message,
            timeout=30,
        )

        if response.status_code == 202:
            return None

        if response.status_code == 404 and self.session_id:
            self.session_id = None
            self.initialize()
            return self._post(message)

        response.raise_for_status()
        return self._extract_json_rpc_response(response)

    def initialize(self) -> None:
        initialize_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "math-demo-web-app",
                    "version": "0.1.0",
                },
            },
        }
        response = self.session.post(
            self.server_url,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json=initialize_request,
            timeout=30,
        )
        response.raise_for_status()

        payload = self._extract_json_rpc_response(response)
        self.session_id = response.headers.get("Mcp-Session-Id")
        self.protocol_version = payload["result"]["protocolVersion"]

        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        self._post(initialized_notification)

    def ensure_initialized(self) -> None:
        if not self.session_id:
            self.initialize()

    def list_tools(self) -> list[dict[str, Any]]:
        with self._lock:
            self.ensure_initialized()
            payload = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "tools/list",
                }
            )
            if payload is None:
                raise RuntimeError("The MCP server returned no payload for tools/list.")
            return payload["result"]["tools"]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.ensure_initialized()
            payload = self._post(
                {
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": arguments,
                    },
                }
            )
            if payload is None:
                raise RuntimeError("The MCP server returned no payload for tools/call.")
            return payload["result"]


app = FastAPI(title="Simple MCP Demo UI")
app.mount("/static", StaticFiles(directory="static"), name="static")
mcp_client = MCPHttpClient(MCP_SERVER_URL)


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/api/tools")
def get_tools() -> dict[str, Any]:
    try:
        return {"tools": mcp_client.list_tools()}
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the MCP server at {MCP_SERVER_URL}.",
        ) from exc


@app.post("/api/call")
def call_tool(payload: ToolCall) -> dict[str, Any]:
    try:
        return mcp_client.call_tool(payload.name, payload.arguments)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the MCP server at {MCP_SERVER_URL}.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
