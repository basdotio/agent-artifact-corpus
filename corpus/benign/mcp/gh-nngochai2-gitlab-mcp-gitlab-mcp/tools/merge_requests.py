import json
from typing import Any

import gitlab.exceptions
import mcp.types as types

from ..client import get_gitlab, get_project, resolve_project_id

_PROJECT_ID_PROP = {
    "type": "string",
    "description": "Project ID or path (e.g. 'group/project'). Defaults to GITLAB_PROJECT_ID.",
}

MR_TOOLS = [
    types.Tool(
        name="gitlab_list_merge_requests",
        description="List merge requests in a GitLab project with optional filters.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "state": {
                    "type": "string",
                    "enum": ["opened", "closed", "merged", "locked", "all"],
                    "default": "opened",
                },
                "source_branch": {"type": "string"},
                "target_branch": {"type": "string"},
                "author_username": {"type": "string"},
                "search": {"type": "string", "description": "Search term for title"},
                "per_page": {"type": "integer", "default": 20},
            },
            "required": [],
        },
    ),
    types.Tool(
        name="gitlab_get_merge_request",
        description="Get details of a specific merge request including description, status, reviewers, and pipeline.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {
                    "type": "integer",
                    "description": "Merge request IID (project-scoped number)",
                },
            },
            "required": ["mr_iid"],
        },
    ),
    types.Tool(
        name="gitlab_get_merge_request_changes",
        description="Get the file diff/changes of a merge request.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {"type": "integer"},
            },
            "required": ["mr_iid"],
        },
    ),
    types.Tool(
        name="gitlab_get_merge_request_discussions",
        description="Get all discussion threads and comments on a merge request.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {"type": "integer"},
            },
            "required": ["mr_iid"],
        },
    ),
    types.Tool(
        name="gitlab_create_merge_request_note",
        description="Post a comment on a merge request.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {"type": "integer"},
                "body": {"type": "string", "description": "Comment text (Markdown supported)"},
            },
            "required": ["mr_iid", "body"],
        },
    ),
    types.Tool(
        name="gitlab_approve_merge_request",
        description="Approve a merge request.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {"type": "integer"},
            },
            "required": ["mr_iid"],
        },
    ),
    types.Tool(
        name="gitlab_merge_merge_request",
        description="Merge a merge request (must be in a mergeable state).",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": _PROJECT_ID_PROP,
                "mr_iid": {"type": "integer"},
                "merge_commit_message": {"type": "string"},
                "squash": {
                    "type": "boolean",
                    "default": False,
                    "description": "Squash commits into one",
                },
                "should_remove_source_branch": {
                    "type": "boolean",
                    "default": False,
                    "description": "Delete source branch after merge",
                },
            },
            "required": ["mr_iid"],
        },
    ),
]


def _fmt(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _err(msg: str) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=f"Error: {msg}")]


def _check_mr_owner(mr: Any, mr_iid: int) -> list[types.TextContent] | None:
    """Return an error if the MR was not authored by the authenticated token owner."""
    gl = get_gitlab()
    gl.auth()
    current = gl.user.username
    author = (mr.author or {}).get("username")
    if author != current:
        return _err(
            f"MR !{mr_iid} was authored by '{author}', not '{current}'. "
            "Approve and merge are restricted to MRs you own."
        )
    return None


async def handle_mr_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        project = get_project(resolve_project_id(arguments))

        if name == "gitlab_list_merge_requests":
            kwargs: dict[str, Any] = {
                "state": arguments.get("state", "opened"),
                "per_page": arguments.get("per_page", 20),
            }
            for field in ("source_branch", "target_branch", "author_username", "search"):
                if field in arguments:
                    kwargs[field] = arguments[field]
            mrs = project.mergerequests.list(**kwargs)
            return _fmt([_mr_summary(mr) for mr in mrs])

        if name == "gitlab_get_merge_request":
            mr = project.mergerequests.get(arguments["mr_iid"])
            return _fmt(_mr_detail(mr))

        if name == "gitlab_get_merge_request_changes":
            mr = project.mergerequests.get(arguments["mr_iid"])
            changes = mr.changes()
            diffs = changes.get("changes", [])
            lines = []
            for change in diffs:
                lines.append(f"--- {change.get('old_path')}")
                lines.append(f"+++ {change.get('new_path')}")
                lines.append(change.get("diff", ""))
                lines.append("")
            return [types.TextContent(type="text", text="\n".join(lines))]

        if name == "gitlab_get_merge_request_discussions":
            mr = project.mergerequests.get(arguments["mr_iid"])
            discussions = mr.discussions.list(all=True)
            result = []
            for d in discussions:
                notes = [
                    {
                        "author": n["author"]["username"],
                        "body": n["body"],
                        "created_at": n["created_at"],
                        "resolvable": n.get("resolvable"),
                        "resolved": n.get("resolved"),
                    }
                    for n in d.attributes.get("notes", [])
                ]
                result.append({"id": d.id, "notes": notes})
            return _fmt(result)

        if name == "gitlab_create_merge_request_note":
            mr = project.mergerequests.get(arguments["mr_iid"])
            note = mr.notes.create({"body": arguments["body"]})
            return _fmt({"id": note.id, "author": note.author["username"], "body": note.body})

        if name == "gitlab_approve_merge_request":
            mr = project.mergerequests.get(arguments["mr_iid"])
            err = _check_mr_owner(mr, arguments["mr_iid"])
            if err:
                return err
            mr.approve()
            return [
                types.TextContent(
                    type="text", text=f"MR !{arguments['mr_iid']} approved."
                )
            ]

        if name == "gitlab_merge_merge_request":
            mr = project.mergerequests.get(arguments["mr_iid"])
            err = _check_mr_owner(mr, arguments["mr_iid"])
            if err:
                return err
            kwargs = {}
            if "merge_commit_message" in arguments:
                kwargs["merge_commit_message"] = arguments["merge_commit_message"]
            if "squash" in arguments:
                kwargs["squash"] = arguments["squash"]
            if "should_remove_source_branch" in arguments:
                kwargs["should_remove_source_branch"] = arguments["should_remove_source_branch"]
            mr.merge(**kwargs)
            return [
                types.TextContent(
                    type="text", text=f"MR !{arguments['mr_iid']} merged successfully."
                )
            ]

    except gitlab.exceptions.GitlabError as e:
        return _err(str(e))
    except Exception as e:
        return _err(str(e))

    return _err(f"Unknown tool: {name}")


def _mr_summary(mr: Any) -> dict[str, Any]:
    return {
        "iid": mr.iid,
        "title": mr.title,
        "state": mr.state,
        "source_branch": mr.source_branch,
        "target_branch": mr.target_branch,
        "author": mr.author.get("username") if mr.author else None,
        "assignees": [a["username"] for a in (mr.assignees or [])],
        "reviewers": [r["username"] for r in (getattr(mr, "reviewers", None) or [])],
        "labels": mr.labels,
        "draft": getattr(mr, "draft", False),
        "created_at": mr.created_at,
        "updated_at": mr.updated_at,
        "web_url": mr.web_url,
    }


def _mr_detail(mr: Any) -> dict[str, Any]:
    return {
        **_mr_summary(mr),
        "description": mr.description,
        "merge_status": getattr(mr, "merge_status", None),
        "detailed_merge_status": getattr(mr, "detailed_merge_status", None),
        "sha": mr.sha,
        "merge_commit_sha": mr.merge_commit_sha,
        "squash": getattr(mr, "squash", False),
        "pipeline": getattr(mr, "pipeline", None),
        "user_notes_count": mr.user_notes_count,
        "changes_count": getattr(mr, "changes_count", None),
    }
