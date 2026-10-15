"""Checklists tools (4 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_task_checklists",
            description="Get checklists for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task_checklist",
            description="Create a checklist for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Checklist name"
                    }
                },
                "required": ["task_id", "name"]
            }
        ),
        Tool(
            name="create_checklist_item",
            description="Create a checklist item",
            inputSchema={
                "type": "object",
                "properties": {
                    "checklist_id": {
                        "type": "string",
                        "description": "Checklist ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Item name"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID"
                    }
                },
                "required": ["checklist_id", "name"]
            }
        ),
        Tool(
            name="update_checklist_item",
            description="Update a checklist item",
            inputSchema={
                "type": "object",
                "properties": {
                    "checklist_id": {
                        "type": "string",
                        "description": "Checklist ID"
                    },
                    "checklist_item_id": {
                        "type": "string",
                        "description": "Checklist item ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New item name"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID"
                    },
                    "resolved": {
                        "type": "boolean",
                        "description": "Is resolved"
                    }
                },
                "required": ["checklist_id", "checklist_item_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Checklists category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_task_checklists":
        task_id = arguments["task_id"]
        response = await client.get(f"/task/{task_id}/checklist")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task_checklist":
        task_id = arguments["task_id"]
        data = {"name": arguments["name"]}
        response = await client.post(f"/task/{task_id}/checklist", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_checklist_item":
        checklist_id = arguments["checklist_id"]
        data = {"name": arguments["name"]}
        if "assignee" in arguments:
            data["assignee"] = arguments["assignee"]
        response = await client.post(f"/checklist/{checklist_id}/checklist_item", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_checklist_item":
        checklist_id = arguments["checklist_id"]
        checklist_item_id = arguments["checklist_item_id"]
        data = {}
        for key in ["name", "assignee", "resolved"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/checklist/{checklist_id}/checklist_item/{checklist_item_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
