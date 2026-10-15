import json
from typing import Any

import gitlab.exceptions
import mcp.types as types

from ..client import get_project, resolve_project_id

_PROJECT_ID_PROP = {
    "type": "string",
    "description": "Project ID or path (e.g. 'group/project'). Defaults to GITLAB_PROJECT_ID.",
}

ISSUE_TOOLS = [
    types.Tool(
        name="gitlab_list_issues",
        description="List issues in a GitLab project with optional filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "state": {
                    "type": "string",
                    "enum": ["opened", "closed", "all"],
                    "default": "opened",
                    "description": "Filter by issue state",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names to filter by",
                },
                "assignee_username": {
                    "type": "string",
                    "description": "Filter by assignee username",
                },
                "search": {
                    "type": "string",
                    "description": "Search term to filter issues by title/description",
                },
                "per_page": {
                    "type": "integer",
                    "default": 20,
                    "description": "Number of results per page (max 100)",
                },
            },
            "required": [],
        },
    ),
    types.Tool(
        name="gitlab_get_issue",
        description="Get details of a specific GitLab issue.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "issue_iid": {
                    "type": "integer",
                    "description": "Issue IID (project-scoped issue number)",
                },
            },
            "required": ["issue_iid"],
        },
    ),
    types.Tool(
        name="gitlab_create_issue",
        description="Create a new issue in a GitLab project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "title": {"type": "string", "description": "Issue title"},
                "description": {"type": "string", "description": "Issue description (Markdown)"},
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "assignee_usernames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of usernames to assign the issue to",
                },
                "milestone_id": {
                    "type": "integer",
                    "description": "Milestone ID to associate with the issue",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
            },
            "required": ["title"],
        },
    ),
    types.Tool(
        name="gitlab_update_issue",
        description=(
            "Update an existing GitLab issue (title, description, labels, assignees, state). "
            "Use gitlab_create_issue_note after this to log what changed and why."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "issue_iid": {"type": "integer"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "labels": {
                    "type": "string",
                    "description": "Comma-separated label names (replaces existing labels)",
                },
                "state_event": {
                    "type": "string",
                    "enum": ["close", "reopen"],
                    "description": "Transition the issue state",
                },
                "assignee_usernames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Replace assignees with this list (empty list clears assignees)",
                },
            },
            "required": ["issue_iid"],
        },
    ),
    types.Tool(
        name="gitlab_close_issue",
        description="Close a GitLab issue.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "issue_iid": {"type": "integer"},
            },
            "required": ["issue_iid"],
        },
    ),
    types.Tool(
        name="gitlab_delete_issue",
        description=(
            "Permanently delete a GitLab issue. Use when an issue is wrong or unnecessary. "
            "Requires Owner or Admin role. Prefer gitlab_close_issue if the issue should be "
            "kept for history."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "issue_iid": {"type": "integer"},
            },
            "required": ["issue_iid"],
        },
    ),
    types.Tool(
        name="gitlab_create_issue_note",
        description="Post a comment on a GitLab issue. Use after updates to log what changed and why.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "issue_iid": {"type": "integer"},
                "body": {"type": "string", "description": "Comment text (Markdown supported)"},
            },
            "required": ["issue_iid", "body"],
        },
    ),
    types.Tool(
        name="gitlab_link_issues",
        description=(
            "Create a blocking/related link between two GitLab issues. "
            "Use link_type='blocks' to express DAG dependencies from decompose-issues: "
            "issue A blocks issue B means B cannot start until A is done."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project containing the source issue. Defaults to GITLAB_PROJECT_ID.",
                },
                "issue_iid": {
                    "type": "integer",
                    "description": "IID of the source issue",
                },
                "target_project_id": {
                    "type": "string",
                    "description": "Project containing the target issue. Defaults to source project_id.",
                },
                "target_issue_iid": {
                    "type": "integer",
                    "description": "IID of the target issue",
                },
                "link_type": {
                    "type": "string",
                    "enum": ["relates_to", "blocks", "is_blocked_by"],
                    "default": "blocks",
                    "description": (
                        "'blocks': source blocks target; "
                        "'is_blocked_by': source is blocked by target; "
                        "'relates_to': general relation"
                    ),
                },
            },
            "required": ["issue_iid", "target_issue_iid"],
        },
    ),
]


def _fmt(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _err(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"Error: {msg}")]


async def handle_issue_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        project = get_project(resolve_project_id(arguments))

        if name == "gitlab_list_issues":
            kwargs: dict[str, Any] = {
                "state": arguments.get("state", "opened"),
                "per_page": arguments.get("per_page", 20),
            }
            for field in ("labels", "assignee_username", "search"):
                if field in arguments:
                    kwargs[field] = arguments[field]
            issues = project.issues.list(**kwargs)
            return _fmt([_issue_summary(i) for i in issues])

        if name == "gitlab_get_issue":
            issue = project.issues.get(arguments["issue_iid"])
            return _fmt(_issue_detail(issue))

        if name == "gitlab_create_issue":
            kwargs = {"title": arguments["title"]}
            for field in ("description", "labels", "milestone_id", "due_date"):
                if field in arguments:
                    kwargs[field] = arguments[field]
            if "assignee_usernames" in arguments:
                ids = _resolve_user_ids(arguments["assignee_usernames"])
                if ids:
                    kwargs["assignee_ids"] = ids
            issue = project.issues.create(kwargs)
            return _fmt(_issue_detail(issue))

        if name == "gitlab_update_issue":
            issue = project.issues.get(arguments["issue_iid"])
            for field in ("title", "description", "labels", "state_event"):
                if field in arguments:
                    setattr(issue, field, arguments[field])
            if "assignee_usernames" in arguments:
                ids = _resolve_user_ids(arguments["assignee_usernames"])
                issue.assignee_ids = ids
            issue.save()
            return _fmt(_issue_detail(issue))

        if name == "gitlab_close_issue":
            issue = project.issues.get(arguments["issue_iid"])
            issue.state_event = "close"
            issue.save()
            return [types.TextContent(type="text", text=f"Issue #{arguments['issue_iid']} closed.")]

        if name == "gitlab_delete_issue":
            issue = project.issues.get(arguments["issue_iid"])
            issue.delete()
            return [
                types.TextContent(
                    type="text", text=f"Issue #{arguments['issue_iid']} permanently deleted."
                )
            ]

        if name == "gitlab_create_issue_note":
            issue = project.issues.get(arguments["issue_iid"])
            note = issue.notes.create({"body": arguments["body"]})
            return _fmt({"id": note.id, "author": note.author["username"], "body": note.body})

        if name == "gitlab_link_issues":
            issue = project.issues.get(arguments["issue_iid"])
            target_project_id = arguments.get("target_project_id") or resolve_project_id(arguments)
            link = issue.links.create(
                {
                    "target_project_id": target_project_id,
                    "target_issue_iid": arguments["target_issue_iid"],
                    "link_type": arguments.get("link_type", "blocks"),
                }
            )
            return _fmt(
                {
                    "source_iid": arguments["issue_iid"],
                    "target_iid": arguments["target_issue_iid"],
                    "link_type": arguments.get("link_type", "blocks"),
                    "link_id": getattr(link, "id", None),
                }
            )

    except gitlab.exceptions.GitlabError as e:
        return _err(str(e))
    except Exception as e:
        return _err(str(e))

    return _err(f"Unknown tool: {name}")


def _resolve_user_ids(usernames: list[str]) -> list[int]:
    from ..client import get_gitlab

    gl = get_gitlab()
    ids = []
    for username in usernames:
        users = gl.users.list(username=username)
        if users:
            ids.append(users[0].id)
    return ids


def _issue_summary(issue: Any) -> dict[str, Any]:
    return {
        "iid": issue.iid,
        "title": issue.title,
        "state": issue.state,
        "author": issue.author.get("username") if issue.author else None,
        "assignees": [a["username"] for a in (issue.assignees or [])],
        "labels": issue.labels,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "web_url": issue.web_url,
    }


def _issue_detail(issue: Any) -> dict[str, Any]:
    return {
        **_issue_summary(issue),
        "description": issue.description,
        "milestone": issue.milestone,
        "due_date": issue.due_date,
        "closed_at": issue.closed_at,
        "user_notes_count": issue.user_notes_count,
    }
