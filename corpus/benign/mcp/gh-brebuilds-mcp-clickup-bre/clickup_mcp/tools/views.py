"""Views tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_views",
            description="Get views for a workspace or space",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID (optional if space_id provided)"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "Space ID (optional if workspace_id provided)"
                    }
                }
            }
        ),
        Tool(
            name="get_view",
            description="Get a specific view",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_id": {
                        "type": "string",
                        "description": "View ID"
                    }
                },
                "required": ["view_id"]
            }
        ),
        Tool(
            name="get_view_tasks",
            description="Get tasks from a view",
            inputSchema={
                "type": "object",
                "properties": {
                    "view_id": {
                        "type": "string",
                        "description": "View ID"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number"
                    }
                },
                "required": ["view_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Views category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_views":
        if "workspace_id" in arguments:
            response = await client.get(f"/team/{arguments['workspace_id']}/view")
        elif "space_id" in arguments:
            response = await client.get(f"/space/{arguments['space_id']}/view")
        else:
            return [TextContent(type="text", text='{"error": "workspace_id or space_id is required"}')]
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_view":
        view_id = arguments["view_id"]
        response = await client.get(f"/view/{view_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_view_tasks":
        view_id = arguments["view_id"]
        params = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        response = await client.get(f"/view/{view_id}/task", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
