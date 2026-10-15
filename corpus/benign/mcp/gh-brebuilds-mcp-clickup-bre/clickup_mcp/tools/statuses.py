"""Statuses tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_list_statuses",
            description="Get statuses for a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    }
                },
                "required": ["list_id"]
            }
        ),
        Tool(
            name="create_list_status",
            description="Create a status for a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status name"
                    },
                    "type": {
                        "type": "string",
                        "description": "Status type (open, custom, closed)"
                    },
                    "orderindex": {
                        "type": "integer",
                        "description": "Order index"
                    }
                },
                "required": ["list_id", "status", "type"]
            }
        ),
        Tool(
            name="update_list_status",
            description="Update a list status",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    },
                    "status_id": {
                        "type": "string",
                        "description": "Status ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status name"
                    },
                    "orderindex": {
                        "type": "integer",
                        "description": "Order index"
                    }
                },
                "required": ["list_id", "status_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Statuses category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_list_statuses":
        list_id = arguments["list_id"]
        response = await client.get(f"/list/{list_id}/field")
        # Filter for status fields
        result = response.json()
        statuses = [f for f in result.get("fields", []) if f.get("type") == "status"]
        return [TextContent(type="text", text=json.dumps(statuses, indent=2))]

    elif name == "create_list_status":
        list_id = arguments["list_id"]
        data = {
            "status": arguments["status"],
            "type": arguments["type"]
        }
        if "orderindex" in arguments:
            data["orderindex"] = arguments["orderindex"]
        response = await client.post(f"/list/{list_id}/field", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_list_status":
        list_id = arguments["list_id"]
        status_id = arguments["status_id"]
        data = {}
        if "status" in arguments:
            data["status"] = arguments["status"]
        if "orderindex" in arguments:
            data["orderindex"] = arguments["orderindex"]
        response = await client.put(f"/list/{list_id}/field/{status_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
