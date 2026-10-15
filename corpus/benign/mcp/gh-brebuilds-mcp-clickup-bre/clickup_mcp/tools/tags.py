"""Tags tools (3 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_tags",
            description="Get tags for a workspace",
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
            name="create_tag",
            description="Create a tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Tag name"
                    },
                    "tag_fg": {
                        "type": "string",
                        "description": "Tag foreground color"
                    },
                    "tag_bg": {
                        "type": "string",
                        "description": "Tag background color"
                    }
                },
                "required": ["workspace_id", "name"]
            }
        ),
        Tool(
            name="update_tag",
            description="Update a tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag_name": {
                        "type": "string",
                        "description": "Tag name"
                    },
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "tag_fg": {
                        "type": "string",
                        "description": "Tag foreground color"
                    },
                    "tag_bg": {
                        "type": "string",
                        "description": "Tag background color"
                    }
                },
                "required": ["tag_name", "workspace_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Tags category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_tags":
        workspace_id = arguments["workspace_id"]
        response = await client.get(f"/team/{workspace_id}/tag")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_tag":
        workspace_id = arguments["workspace_id"]
        data = {"name": arguments["name"]}
        if "tag_fg" in arguments:
            data["tag_fg"] = arguments["tag_fg"]
        if "tag_bg" in arguments:
            data["tag_bg"] = arguments["tag_bg"]
        response = await client.post(f"/team/{workspace_id}/tag", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_tag":
        tag_name = arguments["tag_name"]
        workspace_id = arguments["workspace_id"]
        data = {}
        if "tag_fg" in arguments:
            data["tag_fg"] = arguments["tag_fg"]
        if "tag_bg" in arguments:
            data["tag_bg"] = arguments["tag_bg"]
        response = await client.put(f"/team/{workspace_id}/tag/{tag_name}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
