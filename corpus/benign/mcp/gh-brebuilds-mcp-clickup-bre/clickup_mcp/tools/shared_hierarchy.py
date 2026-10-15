"""Shared Hierarchy tools (1 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_shared_hierarchy",
            description="Get shared hierarchy for a workspace",
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

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Shared Hierarchy category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_shared_hierarchy":
        workspace_id = arguments["workspace_id"]
        response = await client.get(f"/team/{workspace_id}/shared")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
