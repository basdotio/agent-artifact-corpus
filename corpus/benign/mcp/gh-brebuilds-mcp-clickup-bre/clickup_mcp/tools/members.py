"""Members tools (2 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_team_members",
            description="Get members of a team",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    }
                },
                "required": ["team_id"]
            }
        ),
        Tool(
            name="get_team_member",
            description="Get a specific team member",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_id": {
                        "type": "string",
                        "description": "Team ID"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    }
                },
                "required": ["team_id", "user_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Members category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_team_members":
        team_id = arguments["team_id"]
        response = await client.get(f"/team/{team_id}/member")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_team_member":
        team_id = arguments["team_id"]
        user_id = arguments["user_id"]
        response = await client.get(f"/team/{team_id}/member/{user_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
