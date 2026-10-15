#!/usr/bin/env python3
"""
Test client for the Python MCP server.
Usage: python scripts/test_client.py <server_url>
Example: python scripts/test_client.py mcp-fass.vercel.app
"""

import sys
import json
import requests


def test_mcp_server(server_url: str):
    """Test the MCP server with proper initialization sequence."""
    # Ensure the URL has the correct protocol
    if not server_url.startswith(("http://", "https://")):
        base_url = f"https://{server_url}"
    else:
        base_url = server_url

    # Remove trailing slash if present
    base_url = base_url.rstrip("/")

    print(f"Testing MCP Server at: {base_url}")

    # Test 0: Check server info
    print("\n0. Testing server info...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 1: Initialize request
    print("\n1. Testing initialize request...")
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
            "clientInfo": {"name": "TestClient", "version": "1.0.0"},
        },
    }

    try:
        response = requests.post(f"{base_url}/mcp", json=initialize_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Initialized notification
    print("\n2. Testing initialized notification...")
    initialized_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    try:
        response = requests.post(f"{base_url}/mcp", json=initialized_notification)
        print(f"Status: {response.status_code}")
        print(f"Response length: {len(response.content)} bytes")
        if response.content:
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            except ValueError:
                print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 3: Tools list request
    print("\n3. Testing tools/list request...")
    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    try:
        response = requests.post(f"{base_url}/mcp", json=tools_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 4: Tool call - echo
    print("\n4. Testing tools/call request (echo)...")
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "Hello from test client!"}},
    }

    try:
        response = requests.post(f"{base_url}/mcp", json=tool_call_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 5: Tool call - get_time
    print("\n5. Testing tools/call request (get_time)...")
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "get_time", "arguments": {}},
    }

    try:
        response = requests.post(f"{base_url}/mcp", json=tool_call_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 6: Tool call - add_numbers
    print("\n6. Testing tools/call request (add_numbers)...")
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "add_numbers", "arguments": {"a": 42, "b": 8}},
    }

    try:
        response = requests.post(f"{base_url}/mcp", json=tool_call_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_client.py <server_url>")
        print("Example: python scripts/test_client.py mcp-fass.vercel.app")
        print("Example: python scripts/test_client.py https://mcp-fass.vercel.app")
        return

    server_url = sys.argv[1]
    test_mcp_server(server_url)


if __name__ == "__main__":
    main()
