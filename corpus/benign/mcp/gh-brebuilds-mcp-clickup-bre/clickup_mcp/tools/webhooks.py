"""Webhooks tools (4 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_webhooks",
            description="Get webhooks for a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="create_webhook",
            description="Create a webhook",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "Webhook endpoint URL"
                    },
                    "client_id": {
                        "type": "string",
                        "description": "Client ID"
                    },
                    "events": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Events to subscribe to"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Task ID filter (optional)"
                    },
                    "list_id": {
                        "type": "string",
                        "description": "List ID filter (optional)"
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "Folder ID filter (optional)"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID filter (optional)"
                    },
                    "health": {
                        "type": "object",
                        "description": "Health check configuration"
                    }
                },
                "required": ["workspace_id", "endpoint", "client_id", "events"]
            }
        ),
        Tool(
            name="update_webhook",
            description="Update a webhook",
            inputSchema={
                "type": "object",
                "properties": {
                    "webhook_id": {
                        "type": "string",
                        "description": "Webhook ID"
                    },
                    "endpoint": {
                        "type": "string",
                        "description": "New webhook endpoint URL"
                    },
                    "events": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Events to subscribe to"
                    },
                    "status": {
                        "type": "string",
                        "description": "Webhook status (active, inactive)"
                    }
                },
                "required": ["webhook_id"]
            }
        ),
        Tool(
            name="delete_webhook",
            description="Delete a webhook",
            inputSchema={
                "type": "object",
                "properties": {
                    "webhook_id": {
                        "type": "string",
                        "description": "Webhook ID"
                    }
                },
                "required": ["webhook_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Webhooks category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_webhooks":
        workspace_id = arguments["workspace_id"]
        response = await client.get(f"/team/{workspace_id}/webhook")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_webhook":
        workspace_id = arguments["workspace_id"]
        data = {
            "endpoint": arguments["endpoint"],
            "client_id": arguments["client_id"],
            "events": arguments["events"]
        }
        for key in ["task_id", "list_id", "folder_id", "space_id", "health"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.post(f"/team/{workspace_id}/webhook", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_webhook":
        webhook_id = arguments["webhook_id"]
        data = {}
        for key in ["endpoint", "events", "status"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/webhook/{webhook_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "delete_webhook":
        webhook_id = arguments["webhook_id"]
        response = await client.delete(f"/webhook/{webhook_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Webhook deleted"}, indent=2))]

    return None
