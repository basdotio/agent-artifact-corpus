"""Documents tools (6 tools)."""
import json
from typing import List, Optional

from mcp.types import Tool, TextContent

from clickup_mcp.client import client

TOOLS: List[Tool] = [
        Tool(
            name="search_documents",
            description="Search documents in a workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["workspace_id"]
            }
        ),
        Tool(
            name="get_document",
            description="Get a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="create_document",
            description="Create a new document with rich formatting",
            inputSchema={
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "Workspace ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Document name"
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content (supports markdown/HTML)"
                    },
                    "parent_id": {
                        "type": "string",
                        "description": "Parent document/page ID (optional)"
                    }
                },
                "required": ["workspace_id", "name"]
            }
        ),
        Tool(
            name="update_document",
            description="Update a document with formatting and embeds",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "New document name"
                    },
                    "content": {
                        "type": "string",
                        "description": "New document content (supports markdown/HTML)"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="delete_document",
            description="Delete a document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="create_document_page",
            description="Create a page in a document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Page name"
                    },
                    "content": {
                        "type": "string",
                        "description": "Page content"
                    }
                },
                "required": ["document_id", "name"]
            }
        ),

]


async def handle(name: str, arguments: dict) -> Optional[List[TextContent]]:
    """Handle a call belonging to the Documents category.

    Returns None when `name` is not one of this module's tools so the
    top-level dispatcher can try the next category.
    """
    if name == "search_documents":
        workspace_id = arguments["workspace_id"]
        params = {}
        if "query" in arguments:
            params["query"] = arguments["query"]
        response = await client.get(f"/team/{workspace_id}/doc", params=params)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "get_document":
        document_id = arguments["document_id"]
        response = await client.get(f"/doc/{document_id}")
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "create_document":
        workspace_id = arguments["workspace_id"]
        data = {"name": arguments["name"]}
        if "content" in arguments:
            data["content"] = arguments["content"]
        if "parent_id" in arguments:
            data["parent_id"] = arguments["parent_id"]
        response = await client.post(f"/team/{workspace_id}/doc", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "update_document":
        document_id = arguments["document_id"]
        data = {}
        if "name" in arguments:
            data["name"] = arguments["name"]
        if "content" in arguments:
            data["content"] = arguments["content"]
        response = await client.put(f"/doc/{document_id}", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    elif name == "delete_document":
        document_id = arguments["document_id"]
        response = await client.delete(f"/doc/{document_id}")
        return [TextContent(type="text", text=json.dumps({"success": True, "message": "Document deleted"}, indent=2))]

    elif name == "create_document_page":
        document_id = arguments["document_id"]
        data = {
            "name": arguments["name"],
            "content": arguments.get("content", "")
        }
        response = await client.post(f"/doc/{document_id}/page", json=data)
        return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

    return None
