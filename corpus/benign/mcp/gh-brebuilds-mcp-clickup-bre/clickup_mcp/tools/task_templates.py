"""Task Templates tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_task_templates",
            description="Get task templates for a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_task_template",
            description="Get a specific task template",
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
        Tool(
            name="create_task_from_template",
            description="Create a task from a template",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "List ID"
                    },
                    "template_id": {
                        "type": "string",
                        "description": "Template ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Task name"
                    }
                },
                "required": ["list_id", "template_id", "name"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Task Templates category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_task_templates":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        response = await client.get(f"/team/{workspace_id}/taskTemplate", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_task_template":
        template_id = arguments["template_id"]
        response = await client.get(f"/taskTemplate/{template_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_task_from_template":
        list_id = arguments["list_id"]
        data = {
            "template_id": arguments["template_id"],
            "name": arguments["name"]
        }
        response = await client.post(f"/list/{list_id}/taskTemplate", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
