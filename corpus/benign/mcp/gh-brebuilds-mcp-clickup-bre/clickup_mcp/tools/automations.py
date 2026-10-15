"""Automation Rules tools (5 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_automations",
            description="Get automation rules for a workspace",
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
            name="get_automation",
            description="Get a specific automation rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID"
                    }
                },
                "required": ["automation_id"]
            }
        ),
        Tool(
            name="create_automation",
            description="Create a new automation rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Automation name"
                    },
                    "trigger": {
                        "type": "object",
                        "description": "Trigger configuration"
                    },
                    "actions": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Actions to perform"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID to apply automation"
                    }
                },
                "required": ["workspace_id", "name", "trigger", "actions"]
            }
        ),
        Tool(
            name="update_automation",
            description="Update an automation rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New automation name"
                    },
                    "trigger": {
                        "type": "object",
                        "description": "New trigger configuration"
                    },
                    "actions": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "New actions to perform"
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable/disable automation"
                    }
                },
                "required": ["automation_id"]
            }
        ),
        Tool(
            name="delete_automation",
            description="Delete an automation rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "automation_id": {
                        "type": "string",
                        "description": "Automation ID"
                    }
                },
                "required": ["automation_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Automation Rules category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_automations":
        workspace_id = arguments["workspace_id"]
        response = await client.get(f"/team/{workspace_id}/automation")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_automation":
        automation_id = arguments["automation_id"]
        response = await client.get(f"/automation/{automation_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_automation":
        workspace_id = arguments["workspace_id"]
        data = {
            "name": arguments["name"],
            "trigger": arguments["trigger"],
            "actions": arguments["actions"]
        }
        if "space_id" in arguments:
            data["space_id"] = arguments["space_id"]
        response = await client.post(f"/team/{workspace_id}/automation", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_automation":
        automation_id = arguments["automation_id"]
        data = {}
        for key in ["name", "trigger", "actions", "enabled"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/automation/{automation_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "delete_automation":
        automation_id = arguments["automation_id"]
        response = await client.delete(f"/automation/{automation_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Automation deleted"}, indent=2))]

    return None
