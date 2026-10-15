import json
import os
import httpx
from mcp import types

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8080/api")


def api_url(path):
    return f"{API_BASE}{path}"


def get_client(token=None):
    headers = {}
    if token:
        headers['X-Agent-Token'] = token
    return httpx.Client(headers=headers)


TOOL_DEFS = [
    types.Tool(
        name="list_tickets",
        description="Search and list tickets with optional filters: cycle_id, project_id, status, assignee, search, no_cycle",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Agent token (optional for read)"},
                "cycle_id": {"type": "integer", "description": "Filter by cycle ID"},
                "project_id": {"type": "integer", "description": "Filter by project ID"},
                "status": {"type": "string", "description": "Status: todo, progress, review, done, cancel"},
                "assignee": {"type": "string", "description": "Filter by assignee name"},
                "assignee_id": {"type": "integer", "description": "Filter by assignee user ID"},
                "search": {"type": "string", "description": "Server-side search on name and description"},
                "no_cycle": {"type": "boolean", "description": "Only tickets without a cycle (the Backlog page)"},
            },
        },
    ),
    types.Tool(
        name="get_ticket",
        description="Get full ticket details including comments, PR links, relationships, and history",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Ticket ID"},
            },
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="create_ticket",
        description="Create a new ticket. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "name": {"type": "string", "description": "Ticket title"},
                "description": {"type": "string", "description": "Markdown description"},
                "type": {"type": "string", "description": "bug, feature, or chore"},
                "priority": {"type": "string", "description": "urgent, high, medium, low, or none"},
                "status": {"type": "string", "description": "Initial status"},
                "project_id": {"type": "integer", "description": "Project ID"},
                "cycle_id": {"type": "integer", "description": "Cycle ID"},
                "assignee": {"type": "string", "description": "Assignee name"},
                "assignee_id": {"type": "integer", "description": "Assignee user ID"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["agent_token", "name"],
        },
    ),
    types.Tool(
        name="update_ticket",
        description="Update ticket fields. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Ticket ID"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "name": {"type": "string"}, "description": {"type": "string"},
                "type": {"type": "string"}, "priority": {"type": "string"},
                "status": {"type": "string"}, "assignee": {"type": "string"},
                "assignee_id": {"type": "integer", "description": "Assignee user ID"},
                "due_date": {"type": "string"},
                "cycle_id": {"type": "integer", "description": "Cycle ID (set to move ticket into a cycle)"},
                "project_id": {"type": "integer", "description": "Project ID"},
            },
            "required": ["ticket_id", "agent_token"],
        },
    ),
    types.Tool(
        name="delete_ticket",
        description="Delete a ticket. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Ticket ID"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
            },
            "required": ["ticket_id", "agent_token"],
        },
    ),
    types.Tool(
        name="reorder_tickets",
        description="Reorder tickets across status columns. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "items": {"type": "array", "description": "List of {id, status, sort_order} objects"},
            },
            "required": ["agent_token", "items"],
        },
    ),
    types.Tool(
        name="add_comment",
        description="Add a comment to a ticket. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"}, "body": {"type": "string"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "pr_url": {"type": "string"}, "pr_title": {"type": "string"},
            },
            "required": ["ticket_id", "body", "agent_token"],
        },
    ),
    types.Tool(
        name="list_comments",
        description="List comments on a ticket.",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}},
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="submit_pr_link",
        description="Link a PR to a ticket. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"}, "url": {"type": "string"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "title": {"type": "string"}, "status": {"type": "string"},
            },
            "required": ["ticket_id", "url", "agent_token"],
        },
    ),
    types.Tool(
        name="list_pr_links",
        description="List PR links for a ticket.",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}},
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="delete_pr_link",
        description="Remove a PR link. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"}, "pr_id": {"type": "integer"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
            },
            "required": ["ticket_id", "pr_id", "agent_token"],
        },
    ),
    types.Tool(
        name="list_relationships",
        description="List ticket relationships (dependencies, blocks, related).",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}},
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="add_relationship",
        description="Create a relationship between tickets. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"}, "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "related_ticket_id": {"type": "integer"}, "relationship_type": {"type": "string"},
            },
            "required": ["ticket_id", "agent_token", "related_ticket_id"],
        },
    ),
    types.Tool(
        name="remove_relationship",
        description="Remove a ticket relationship. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"}, "relationship_id": {"type": "integer"},
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
            },
            "required": ["ticket_id", "relationship_id", "agent_token"],
        },
    ),
    types.Tool(
        name="get_ticket_history",
        description="Get change history for a ticket.",
        inputSchema={
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}},
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="get_stats",
        description="Get aggregate dashboard stats: inbox count, triage count, my tickets count.",
        inputSchema={
            "type": "object",
            "properties": {"cycle_id": {"type": "integer", "description": "Filter by cycle"}},
        },
    ),
    types.Tool(
        name="list_projects",
        description="List projects with id, name, description, color, git_repo_url, and ticket counts. Read-only.",
        inputSchema={
            "type": "object",
            "properties": {
                "cycle_id": {"type": "integer", "description": "Only return projects attached to this cycle"},
            },
        },
    ),
    types.Tool(
        name="list_cycles",
        description="List cycles with id, title, status, dates, project_ids, and ticket_count. Read-only.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "Only return cycles attached to this project"},
                "status": {"type": "string", "description": "Filter by cycle status (pending, in_progress, completed, cancelled)"},
            },
        },
    ),
    types.Tool(
        name="create_cycle",
        description="Create a new cycle. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "title": {"type": "string", "description": "Cycle title (required)"},
                "description": {"type": "string"},
                "status": {"type": "string", "description": "pending / in_progress / completed / cancelled"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "project_ids": {"type": "array", "items": {"type": "integer"}, "description": "Projects to attach to the cycle"},
            },
            "required": ["agent_token", "title"],
        },
    ),
    types.Tool(
        name="update_cycle",
        description="Update a cycle. PATCH semantics — only fields provided are changed. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "cycle_id": {"type": "integer", "description": "Cycle ID (required)"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "project_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["agent_token", "cycle_id"],
        },
    ),
    types.Tool(
        name="list_attachments",
        description="List attachments on a ticket. Returns filename, size, uploader, created_at, and a download URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "Ticket ID"},
            },
            "required": ["ticket_id"],
        },
    ),
    types.Tool(
        name="upload_attachment",
        description=("Upload a file attachment to a ticket. Provide the file as base64 in `file_base64` "
                     "(plus `filename` and optional `content_type`). Max size 25MB. Requires agent_token."),
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "ticket_id": {"type": "integer", "description": "Ticket ID (required)"},
                "filename": {"type": "string", "description": "Original filename (required)"},
                "file_base64": {"type": "string", "description": "Base64-encoded file contents (required)"},
                "content_type": {"type": "string", "description": "MIME type (optional)"},
            },
            "required": ["agent_token", "ticket_id", "filename", "file_base64"],
        },
    ),
    types.Tool(
        name="delete_attachment",
        description="Delete an attachment from a ticket. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string", "description": "Your agent token (required)"},
                "ticket_id": {"type": "integer", "description": "Ticket ID (required)"},
                "attachment_id": {"type": "integer", "description": "Attachment ID (required)"},
            },
            "required": ["agent_token", "ticket_id", "attachment_id"],
        },
    ),
]

TOOL_DEFS.extend([
    # ── Folders ──
    types.Tool(
        name="list_folders",
        description="List folders in a doc space (global or project).",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "space": {"type": "string", "description": "'global' or 'project'"},
                "project_id": {"type": "integer"},
            },
            "required": ["space"],
        },
    ),
    types.Tool(
        name="create_folder",
        description="Create a folder in a doc space. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "name": {"type": "string"},
                "space": {"type": "string"},
                "project_id": {"type": "integer"},
                "parent_folder_id": {"type": "integer"},
            },
            "required": ["agent_token", "name", "space"],
        },
    ),
    types.Tool(
        name="update_folder",
        description="Rename, reparent, or reorder a folder. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "folder_id": {"type": "integer"},
                "name": {"type": "string"},
                "parent_folder_id": {"type": "integer"},
                "sort_order": {"type": "integer"},
            },
            "required": ["agent_token", "folder_id"],
        },
    ),
    types.Tool(
        name="delete_folder",
        description="Delete a folder. Pass recursive=true if non-empty. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "folder_id": {"type": "integer"},
                "recursive": {"type": "boolean"},
            },
            "required": ["agent_token", "folder_id"],
        },
    ),
    # ── Documents ──
    types.Tool(
        name="list_documents",
        description="List documents with optional filters: space, project_id, folder_id, tag.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "space": {"type": "string"},
                "project_id": {"type": "integer"},
                "folder_id": {"type": "integer"},
                "tag": {"type": "string"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="get_document",
        description="Get full document details (title, current body, tags, links, attachments).",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "include_body": {"type": "boolean", "description": "Default true"},
                "include_attachments": {"type": "boolean", "description": "Default false"},
                "include_links": {"type": "boolean", "description": "Default false"},
            },
            "required": ["document_id"],
        },
    ),
    types.Tool(
        name="create_document",
        description="Create a doc with v1 in one call. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "title": {"type": "string"},
                "space": {"type": "string"},
                "project_id": {"type": "integer"},
                "folder_id": {"type": "integer"},
                "body_md": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "change_note": {"type": "string"},
            },
            "required": ["agent_token", "title", "space"],
        },
    ),
    types.Tool(
        name="update_document_metadata",
        description="Update title, folder, or tags WITHOUT creating a new version. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "title": {"type": "string"},
                "folder_id": {"type": "integer"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["agent_token", "document_id"],
        },
    ),
    types.Tool(
        name="save_document",
        description=(
            "Save a new version of a doc. Creates a new version row and advances "
            "the current pointer. Requires agent_token."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "body_md": {"type": "string"},
                "title": {"type": "string"},
                "change_note": {"type": "string"},
            },
            "required": ["agent_token", "document_id", "body_md"],
        },
    ),
    types.Tool(
        name="delete_document",
        description="Delete a doc and its versions, tags, links, attachments. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
            },
            "required": ["agent_token", "document_id"],
        },
    ),
    types.Tool(
        name="search_documents",
        description="Full-text search over current doc bodies + titles + tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "space": {"type": "string"},
                "project_id": {"type": "integer"},
                "tag": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["q"],
        },
    ),
    # ── Versions ──
    types.Tool(
        name="list_document_versions",
        description="List version metadata for a doc.",
        inputSchema={
            "type": "object",
            "properties": {"document_id": {"type": "integer"}},
            "required": ["document_id"],
        },
    ),
    types.Tool(
        name="get_document_version",
        description="Get the full body of a specific version.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer"},
                "version_id": {"type": "integer"},
            },
            "required": ["document_id", "version_id"],
        },
    ),
    types.Tool(
        name="rollback_document",
        description=(
            "Restore a previous version (moves the current pointer; history is preserved). "
            "Requires agent_token."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "version_id": {"type": "integer"},
                "change_note": {"type": "string"},
            },
            "required": ["agent_token", "document_id", "version_id"],
        },
    ),
    # ── Tags ──
    types.Tool(
        name="list_tags",
        description="List/autocomplete tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="create_tag",
        description="Explicit tag creation (usually unnecessary; created on first use).",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["agent_token", "name"],
        },
    ),
    types.Tool(
        name="delete_tag",
        description="Delete a tag globally.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "tag_id": {"type": "integer"},
            },
            "required": ["agent_token", "tag_id"],
        },
    ),
    # ── Links ──
    types.Tool(
        name="link_document_to_ticket",
        description="Link a doc to a ticket (bidirectional). Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "ticket_id": {"type": "integer"},
            },
            "required": ["agent_token", "document_id", "ticket_id"],
        },
    ),
    types.Tool(
        name="unlink_document_from_ticket",
        description="Remove a doc-ticket link. Requires agent_token.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "ticket_id": {"type": "integer"},
            },
            "required": ["agent_token", "document_id", "ticket_id"],
        },
    ),
    types.Tool(
        name="list_linked_tickets",
        description="List ticket IDs linked to a doc.",
        inputSchema={
            "type": "object",
            "properties": {"document_id": {"type": "integer"}},
            "required": ["document_id"],
        },
    ),
    # ── Attachments ──
    types.Tool(
        name="upload_document_attachment",
        description=(
            "Upload a file to a doc as an attachment. Provide a local file path. "
            "Requires agent_token."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "agent_token": {"type": "string"},
                "document_id": {"type": "integer"},
                "file_path": {"type": "string", "description": "Local path on the agent host"},
                "filename": {"type": "string", "description": "Optional override of the filename"},
            },
            "required": ["agent_token", "document_id", "file_path"],
        },
    ),
    types.Tool(
        name="list_document_attachments",
        description="List attachments on a doc.",
        inputSchema={
            "type": "object",
            "properties": {"document_id": {"type": "integer"}},
            "required": ["document_id"],
        },
    ),
])


def call_tool(name: str, arguments: dict) -> str:
    token = arguments.get('agent_token', '')
    tid = arguments.get('ticket_id')

    with get_client(token) as client:
        if name == "list_tickets":
            params = {k: v for k, v in arguments.items()
                      if k in ('cycle_id', 'project_id', 'status', 'assignee', 'assignee_id', 'search') and v}
            if arguments.get('no_cycle'):
                params['no_cycle'] = '1'
            r = client.get(api_url('/tickets'), params=params)
            r.raise_for_status()
            tickets = r.json()
            result = [{'id': t['id'], 'display_id': t['display_id'], 'name': t['name'],
                       'type': t['type'], 'priority': t['priority'], 'status': t['status'],
                       'project_name': t.get('project_name', ''),
                       'assignee': t.get('assignee', ''), 'comment_count': t.get('comment_count', 0),
                       'created_at': t['created_at']} for t in tickets]
            return json.dumps(result, indent=2)

        elif name == "get_ticket":
            r = client.get(api_url(f'/tickets/{tid}'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "create_ticket":
            r = client.post(api_url('/tickets'), json={
                'name': arguments['name'],
                'description': arguments.get('description', ''),
                'type': arguments.get('type', 'feature'),
                'priority': arguments.get('priority', 'medium'),
                'status': arguments.get('status', 'todo'),
                'project_id': arguments.get('project_id'),
                'cycle_id': arguments.get('cycle_id'),
                'assignee': arguments.get('assignee', ''),
                'assignee_id': arguments.get('assignee_id'),
                'due_date': arguments.get('due_date'),
            })
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "update_ticket":
            data = {k: v for k, v in arguments.items()
                    if k in ('name', 'description', 'type', 'priority', 'status', 'assignee', 'assignee_id', 'due_date', 'cycle_id', 'project_id') and v is not None}
            if not data: return json.dumps({"error": "No fields to update"})
            r = client.patch(api_url(f'/tickets/{tid}'), json=data)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_ticket":
            r = client.delete(api_url(f'/tickets/{tid}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        elif name == "reorder_tickets":
            r = client.put(api_url('/tickets/reorder'),
                          json={'items': arguments['items']})
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "add_comment":
            data = {'body': arguments['body'], 'author_type': 'agent', 'author_name': 'AI Agent'}
            if arguments.get('pr_url'):
                data['pr_url'] = arguments['pr_url']
                data['pr_title'] = arguments.get('pr_title', '')
            r = client.post(api_url(f'/tickets/{tid}/comments'), json=data)
            r.raise_for_status()
            return json.dumps({"status": "Comment added", "ticket_id": tid})

        elif name == "list_comments":
            r = client.get(api_url(f'/tickets/{tid}/comments'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "submit_pr_link":
            r = client.post(api_url(f'/tickets/{tid}/pr-links'), json={
                'url': arguments['url'],
                'title': arguments.get('title', ''),
                'status': arguments.get('status', 'open'),
            })
            r.raise_for_status()
            return json.dumps({"status": "PR link submitted", "ticket_id": tid})

        elif name == "list_pr_links":
            r = client.get(api_url(f'/tickets/{tid}/pr-links'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_pr_link":
            pid = arguments['pr_id']
            r = client.delete(api_url(f'/tickets/{tid}/pr-links/{pid}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        elif name == "list_relationships":
            r = client.get(api_url(f'/tickets/{tid}/relationships'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "add_relationship":
            r = client.post(api_url(f'/tickets/{tid}/relationships'), json={
                'related_ticket_id': arguments['related_ticket_id'],
                'relationship_type': arguments.get('relationship_type', 'related'),
            })
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "remove_relationship":
            rid = arguments['relationship_id']
            r = client.delete(api_url(f'/tickets/{tid}/relationships/{rid}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        elif name == "get_ticket_history":
            r = client.get(api_url(f'/tickets/{tid}/history'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "get_stats":
            params = {}
            if arguments.get('cycle_id'):
                params['cycle_id'] = arguments['cycle_id']
            r = client.get(api_url('/stats'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "list_projects":
            params = {}
            if arguments.get('cycle_id'):
                params['cycle_id'] = arguments['cycle_id']
            r = client.get(api_url('/projects'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "list_cycles":
            params = {k: v for k, v in arguments.items()
                      if k in ('project_id', 'status') and v}
            r = client.get(api_url('/cycles'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "create_cycle":
            data = {k: v for k, v in arguments.items()
                    if k in ('title', 'description', 'status', 'start_date', 'end_date', 'project_ids') and v is not None}
            r = client.post(api_url('/cycles'), json=data)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "update_cycle":
            cid = arguments['cycle_id']
            data = {k: v for k, v in arguments.items()
                    if k in ('title', 'description', 'status', 'start_date', 'end_date', 'project_ids') and v is not None}
            if not data:
                return json.dumps({"error": "No fields to update"})
            r = client.put(api_url(f'/cycles/{cid}'), json=data)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "list_attachments":
            r = client.get(api_url(f'/tickets/{tid}/attachments'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "upload_attachment":
            import base64
            try:
                data_bytes = base64.b64decode(arguments['file_base64'], validate=True)
            except Exception as e:
                return json.dumps({"error": f"Invalid base64: {e}"})
            files = {
                'file': (
                    arguments['filename'],
                    data_bytes,
                    arguments.get('content_type') or 'application/octet-stream',
                ),
            }
            r = client.post(api_url(f'/tickets/{tid}/attachments'), files=files)
            if r.status_code >= 400:
                try: return json.dumps(r.json())
                except Exception: r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_attachment":
            aid = arguments['attachment_id']
            r = client.delete(api_url(f'/tickets/{tid}/attachments/{aid}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        # ── Folders ──

        elif name == "list_folders":
            params = {k: v for k, v in arguments.items()
                      if k in ('space', 'project_id') and v is not None}
            r = client.get(api_url('/folders'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "create_folder":
            payload = {k: v for k, v in arguments.items()
                       if k not in ('agent_token',) and v is not None}
            if 'space' in payload:
                payload['space_type'] = payload.pop('space')
            r = client.post(api_url('/folders'), json=payload)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "update_folder":
            fid = arguments['folder_id']
            data = {k: v for k, v in arguments.items()
                    if k in ('name', 'sort_order') and v is not None}
            if 'parent_folder_id' in arguments:
                data['parent_folder_id'] = arguments['parent_folder_id']  # None means "move to root"
            r = client.patch(api_url(f'/folders/{fid}'), json=data)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_folder":
            fid = arguments['folder_id']
            params = {}
            if arguments.get('recursive'):
                params['recursive'] = 'true'
            r = client.delete(api_url(f'/folders/{fid}'), params=params)
            r.raise_for_status()
            return json.dumps({"deleted": True})

        # ── Documents ──

        elif name == "list_documents":
            params = {k: v for k, v in arguments.items()
                      if k in ('space', 'project_id', 'folder_id', 'tag', 'limit', 'offset')
                      and v is not None}
            r = client.get(api_url('/documents'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "get_document":
            did = arguments['document_id']
            params = {k: v for k, v in arguments.items()
                      if k in ('include_body', 'include_attachments', 'include_links')
                      and v is not None}
            r = client.get(api_url(f'/documents/{did}'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "create_document":
            payload = {k: v for k, v in arguments.items()
                       if k != 'agent_token' and v is not None}
            if 'space' in payload:
                payload['space_type'] = payload.pop('space')
            r = client.post(api_url('/documents'), json=payload)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "update_document_metadata":
            did = arguments['document_id']
            data = {k: v for k, v in arguments.items()
                    if k in ('title', 'tags') and v is not None}
            if 'folder_id' in arguments:
                data['folder_id'] = arguments['folder_id']  # None means "move out of folder"
            r = client.patch(api_url(f'/documents/{did}'), json=data)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "save_document":
            did = arguments['document_id']
            payload = {k: v for k, v in arguments.items()
                       if k not in ('agent_token', 'document_id') and v is not None}
            r = client.post(api_url(f'/documents/{did}/versions'), json=payload)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_document":
            did = arguments['document_id']
            r = client.delete(api_url(f'/documents/{did}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        elif name == "search_documents":
            params = {k: v for k, v in arguments.items()
                      if k in ('q', 'space', 'project_id', 'tag', 'limit') and v is not None}
            r = client.get(api_url('/documents/search'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        # ── Versions ──

        elif name == "list_document_versions":
            did = arguments['document_id']
            r = client.get(api_url(f'/documents/{did}/versions'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "get_document_version":
            did = arguments['document_id']
            vid = arguments['version_id']
            r = client.get(api_url(f'/documents/{did}/versions/{vid}'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "rollback_document":
            did = arguments['document_id']
            payload = {k: v for k, v in arguments.items()
                       if k in ('version_id', 'change_note') and v is not None}
            r = client.post(api_url(f'/documents/{did}/rollback'), json=payload)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        # ── Tags ──

        elif name == "list_tags":
            params = {k: v for k, v in arguments.items()
                      if k in ('q', 'limit') and v is not None}
            r = client.get(api_url('/tags'), params=params)
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "create_tag":
            r = client.post(api_url('/tags'), json={'name': arguments['name']})
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "delete_tag":
            tag_id = arguments['tag_id']
            r = client.delete(api_url(f'/tags/{tag_id}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        # ── Links ──

        elif name == "link_document_to_ticket":
            did = arguments['document_id']
            r = client.post(
                api_url(f'/documents/{did}/tickets'),
                json={'ticket_id': arguments['ticket_id']},
            )
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "unlink_document_from_ticket":
            did = arguments['document_id']
            linked_tid = arguments['ticket_id']
            r = client.delete(api_url(f'/documents/{did}/tickets/{linked_tid}'))
            r.raise_for_status()
            return json.dumps({"deleted": True})

        elif name == "list_linked_tickets":
            did = arguments['document_id']
            # We reuse GET /documents/<id> rather than adding a dedicated endpoint —
            # linked_ticket_ids is unconditionally populated and the response size is
            # bounded in practice (no FTS body in the doc serializer; current_version
            # bodies tend to be small enough that an extra round-trip per surface
            # isn't worth a new REST endpoint).
            r = client.get(api_url(f'/documents/{did}'))
            r.raise_for_status()
            doc = r.json()
            return json.dumps(doc.get('linked_ticket_ids', []), indent=2)

        # ── Attachments ──

        elif name == "upload_document_attachment":
            did = arguments['document_id']
            file_path = arguments['file_path']
            filename = arguments.get('filename') or os.path.basename(file_path)
            if not filename:
                return json.dumps({'error': 'Could not determine filename from file_path; pass an explicit filename'})
            try:
                fh = open(file_path, 'rb')
            except OSError as e:
                return json.dumps({'error': f'Cannot open file: {e}'})
            with fh:
                files = {'file': (filename, fh)}
                r = client.post(api_url(f'/documents/{did}/attachments'), files=files)
            if r.status_code >= 400:
                try:
                    return json.dumps(r.json())
                except Exception:
                    r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        elif name == "list_document_attachments":
            did = arguments['document_id']
            r = client.get(api_url(f'/documents/{did}/attachments'))
            r.raise_for_status()
            return json.dumps(r.json(), indent=2)

        return json.dumps({"error": f"Unknown tool: {name}"})
