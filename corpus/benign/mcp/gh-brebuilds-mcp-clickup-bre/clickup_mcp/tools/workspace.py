"""Workspace & Organization tools (18 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="get_authorized_user",
            description="Get the authenticated user's information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_teams",
            description="Get all teams the authenticated user is part of",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_workspaces",
            description="Get all workspaces",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_workspace",
            description="Get a specific workspace by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_spaces",
            description="Get all spaces in a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "archived": {
                        "type": "boolean",
                        "description": "Include archived spaces"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_space",
            description="Get a specific space by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "The space ID"
                    }
                },
                "required": ["space_id"]
            }
        ),
        Tool(
            name="create_space",
            description="Create a new space",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "The workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Space name"
                    },
                    "multiple_assignees": {
                        "type": "boolean",
                        "description": "Allow multiple assignees"
                    },
                    "features": {
                        "type": "object",
                        "description": "Space features configuration"
                    }
                },
                "required": ["workspace_id", "name"]
            }
        ),
        Tool(
            name="update_space",
            description="Update a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "The space ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New space name"
                    },
                    "multiple_assignees": {
                        "type": "boolean",
                        "description": "Allow multiple assignees"
                    },
                    "features": {
                        "type": "object",
                        "description": "Space features configuration"
                    }
                },
                "required": ["space_id"]
            }
        ),
        Tool(
            name="get_folders",
            description="Get all folders in a space",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "The space ID"
                    },
                    "archived": {
                        "type": "boolean",
                        "description": "Include archived folders"
                    }
                },
                "required": ["space_id"]
            }
        ),
        Tool(
            name="get_folder",
            description="Get a specific folder by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "The folder ID"
                    }
                },
                "required": ["folder_id"]
            }
        ),
        Tool(
            name="create_folder",
            description="Create a new folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "space_id": {
                        "type": "string",
                        "description": "The space ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Folder name"
                    }
                },
                "required": ["space_id", "name"]
            }
        ),
        Tool(
            name="update_folder",
            description="Update a folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "The folder ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New folder name"
                    }
                },
                "required": ["folder_id"]
            }
        ),
        Tool(
            name="get_lists",
            description="Get all lists in a folder or space",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "The folder ID (optional if space_id provided)"
                    },
                    "space_id": {
                        "type": "string",
                        "description": "The space ID (optional if folder_id provided)"
                    },
                    "archived": {
                        "type": "boolean",
                        "description": "Include archived lists"
                    }
                }
            }
        ),
        Tool(
            name="get_list",
            description="Get a specific list by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "The list ID"
                    }
                },
                "required": ["list_id"]
            }
        ),
        Tool(
            name="create_list",
            description="Create a new list",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {
                        "type": "string",
                        "description": "The folder ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "List name"
                    },
                    "content": {
                        "type": "string",
                        "description": "List content/description"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "due_date_time": {
                        "type": "boolean",
                        "description": "Include time in due date"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (1=urgent, 2=high, 3=normal, 4=low)"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status name"
                    }
                },
                "required": ["folder_id", "name"]
            }
        ),
        Tool(
            name="update_list",
            description="Update a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "The list ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New list name"
                    },
                    "content": {
                        "type": "string",
                        "description": "New list content/description"
                    },
                    "due_date": {
                        "type": "integer",
                        "description": "Due date timestamp"
                    },
                    "due_date_time": {
                        "type": "boolean",
                        "description": "Include time in due date"
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority (1=urgent, 2=high, 3=normal, 4=low)"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "Assignee user ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "Status name"
                    }
                },
                "required": ["list_id"]
            }
        ),
        Tool(
            name="get_list_members",
            description="Get members of a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "The list ID"
                    }
                },
                "required": ["list_id"]
            }
        ),
        Tool(
            name="get_list_views",
            description="Get views for a list",
            inputSchema={
                "type": "object",
                "properties": {
                    "list_id": {
                        "type": "string",
                        "description": "The list ID"
                    }
                },
                "required": ["list_id"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Workspace & Organization category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "get_authorized_user":
        response = await client.get("/user")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_teams":
        response = await client.get("/team")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_workspaces":
        response = await client.get("/team")
        teams = response.json()
        workspaces = []
        for team in teams.get("teams", []):
            workspaces.extend(team.get("workspaces", []))
        return [TextContent(type="text", text=json.dumps(workspaces, indent=2))]

    elif name == "get_workspace":
        workspace_id = arguments["workspace_id"]
        response = await client.get(f"/team/{workspace_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_spaces":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "archived" in arguments:
            params["archived"] = arguments["archived"]
        response = await client.get(f"/team/{workspace_id}/space", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_space":
        space_id = arguments["space_id"]
        response = await client.get(f"/space/{space_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_space":
        workspace_id = arguments["workspace_id"]
        data = {"name": arguments["name"]}
        if "multiple_assignees" in arguments:
            data["multiple_assignees"] = arguments["multiple_assignees"]
        if "features" in arguments:
            data["features"] = arguments["features"]
        response = await client.post(f"/team/{workspace_id}/space", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_space":
        space_id = arguments["space_id"]
        data = {}
        if "name" in arguments:
            data["name"] = arguments["name"]
        if "multiple_assignees" in arguments:
            data["multiple_assignees"] = arguments["multiple_assignees"]
        if "features" in arguments:
            data["features"] = arguments["features"]
        response = await client.put(f"/space/{space_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_folders":
        space_id = arguments["space_id"]
        params = {}
        if "archived" in arguments:
            params["archived"] = arguments["archived"]
        response = await client.get(f"/space/{space_id}/folder", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_folder":
        folder_id = arguments["folder_id"]
        response = await client.get(f"/folder/{folder_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_folder":
        space_id = arguments["space_id"]
        data = {"name": arguments["name"]}
        response = await client.post(f"/space/{space_id}/folder", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_folder":
        folder_id = arguments["folder_id"]
        data = {}
        if "name" in arguments:
            data["name"] = arguments["name"]
        response = await client.put(f"/folder/{folder_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_lists":
        params = {}
        if "archived" in arguments:
            params["archived"] = arguments["archived"]
        
        if "folder_id" in arguments:
            response = await client.get(f"/folder/{arguments['folder_id']}/list", params=params)
        elif "space_id" in arguments:
            response = await client.get(f"/space/{arguments['space_id']}/list", params=params)
        else:
            return [TextContent(type="text", text='{"error": "Either folder_id or space_id is required"}')]
        
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_list":
        list_id = arguments["list_id"]
        response = await client.get(f"/list/{list_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_list":
        folder_id = arguments["folder_id"]
        data = {"name": arguments["name"]}
        if "content" in arguments:
            data["content"] = arguments["content"]
        if "due_date" in arguments:
            data["due_date"] = arguments["due_date"]
        if "due_date_time" in arguments:
            data["due_date_time"] = arguments["due_date_time"]
        if "priority" in arguments:
            data["priority"] = arguments["priority"]
        if "assignee" in arguments:
            data["assignee"] = arguments["assignee"]
        if "status" in arguments:
            data["status"] = arguments["status"]
        response = await client.post(f"/folder/{folder_id}/list", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_list":
        list_id = arguments["list_id"]
        data = {}
        for key in ["name", "content", "due_date", "due_date_time", "priority", "assignee", "status"]:
            if key in arguments:
                data[key] = arguments[key]
        response = await client.put(f"/list/{list_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_list_members":
        list_id = arguments["list_id"]
        response = await client.get(f"/list/{list_id}/member")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_list_views":
        list_id = arguments["list_id"]
        response = await client.get(f"/list/{list_id}/view")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
