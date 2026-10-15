import json
from typing import Any

import requests


SERVER_URL = "http://127.0.0.1:8000/mcp"
PROTOCOL_VERSION = "2025-06-18"


def post_message(
    message: dict[str, Any],
    session_id: str | None = None,
    protocol_version: str | None = None,
) -> requests.Response:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    if protocol_version:
        headers["MCP-Protocol-Version"] = protocol_version

    return requests.post(SERVER_URL, headers=headers, json=message, timeout=30)


def print_json(title: str, payload: Any) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2))


def extract_json_rpc_response(response: requests.Response) -> dict[str, Any]:
    content_type = response.headers.get("Content-Type", "")

    if content_type.startswith("application/json"):
        return response.json()

    if content_type.startswith("text/event-stream"):
        for chunk in response.text.split("\n\n"):
            for line in chunk.splitlines():
                if line.startswith("data: "):
                    return json.loads(line.removeprefix("data: "))

    raise ValueError(f"Unsupported response content type: {content_type}")


def main() -> None:
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {
                "name": "manual-requests-client",
                "version": "0.1.0",
            },
        },
    }
    initialize_response = post_message(initialize_request)
    initialize_response.raise_for_status()
    initialize_payload = extract_json_rpc_response(initialize_response)

    session_id = initialize_response.headers.get("Mcp-Session-Id")
    negotiated_version = initialize_payload["result"]["protocolVersion"]
    print_json("initialize", initialize_payload)
    print(f"\nSession id: {session_id}")

    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    notification_response = post_message(
        initialized_notification,
        session_id=session_id,
        protocol_version=negotiated_version,
    )
    print(f"\ninitialized notification status: {notification_response.status_code}")

    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    }
    list_tools_response = post_message(
        list_tools_request,
        session_id=session_id,
        protocol_version=negotiated_version,
    )
    list_tools_response.raise_for_status()
    print_json("tools/list", extract_json_rpc_response(list_tools_response))

    call_tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "divide",
            "arguments": {
                "a": 42,
                "b": 6,
            },
        },
    }
    call_tool_response = post_message(
        call_tool_request,
        session_id=session_id,
        protocol_version=negotiated_version,
    )
    call_tool_response.raise_for_status()
    print_json("tools/call", extract_json_rpc_response(call_tool_response))


if __name__ == "__main__":
    main()
