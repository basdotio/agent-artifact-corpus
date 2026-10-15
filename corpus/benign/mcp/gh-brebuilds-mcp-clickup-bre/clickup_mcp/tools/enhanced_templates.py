"""Enhanced Template Operations tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="create_task_template",
            description="Create a new task template",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Template name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Template description"
                    },
                    "task_data": {
                        "type": "object",
                        "description": "Default task data for template"
                    }
                },
                "required": ["workspace_id", "name"]
            }
        ),
        Tool(
            name="update_task_template",
            description="Update a task template",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New template name"
                    },
                    "description": {
                        "type": "string",
                        "description": "New template description"
                    },
                    "task_data": {
                        "type": "object",
                        "description": "Updated default task data"
                    }
                },
                "required": ["template_id"]
            }
        ),
        Tool(
            name="delete_task_template",
            description="Delete a task template",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template ID"
                    }
                },
                "required": ["template_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Enhanced Template Operations category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "create_task_template":
        workspace_id = arguments["workspace_id"]
        data = {"name": arguments["name"]}
        if "description" in arguments:
            data["description"] = arguments["description"]
        if "task_data" in arguments:
            data["task_data"] = arguments["task_data"]
        response = await client.post(f"/team/{workspace_id}/taskTemplate", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_task_template":
        template_id = arguments["template_id"]
        data = {}
        for key in ["name", "description", "task_data"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/taskTemplate/{template_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "delete_task_template":
        template_id = arguments["template_id"]
        response = await client.delete(f"/taskTemplate/{template_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Template deleted"}, indent=2))]

    return None
