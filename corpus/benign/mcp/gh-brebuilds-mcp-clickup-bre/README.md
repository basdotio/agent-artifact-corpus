# ClickUp MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the ClickUp API v2 as **101 tools** an MCP-compatible client (Claude Desktop, Cursor, or any other MCP host) can call directly — workspaces, tasks, time tracking, goals, custom fields, documents, webhooks, automations, bulk operations, and more.

It's a thin, predictable translation layer: each tool takes a small, explicit set of arguments, makes one (or a small batch of) authenticated HTTP calls to `api.clickup.com`, and returns ClickUp's JSON response, pretty-printed, as the tool result.

## What's here

- `server.py` — the MCP entrypoint. Registers the tool list and the dispatcher, then runs over stdio.
- `clickup_mcp/` — the implementation, organized by ClickUp API area (see [Project layout](#project-layout)).
- `tests/` — 34 test functions (608+ parametrized cases) covering schema validity, request construction, response/error handling, and bulk-operation semantics. No network calls.
- `.github/workflows/ci.yml` — runs the test suite on every push/PR.

## Setup

**Requirements:** Python 3.11+, a ClickUp account, and a ClickUp API token.

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get a ClickUp API token: ClickUp → Settings → Apps → **API Token**.

3. Provide it as an environment variable, either exported directly:
   ```bash
   export CLICKUP_API_TOKEN=your_api_token_here
   ```
   or in a `.env` file in the repo root:
   ```
   CLICKUP_API_TOKEN=your_api_token_here
   ```
   The server reads `CLICKUP_API_TOKEN` at import time and refuses to start without it.

4. Run it directly to confirm it starts (it communicates over stdio, so it will sit waiting for an MCP client):
   ```bash
   python server.py
   ```

### Connecting an MCP client

Add an entry to your client's MCP server config (Claude Desktop's `claude_desktop_config.json`, Cursor's `mcp.json`, etc.):

```json
{
  "mcpServers": {
    "clickup": {
      "command": "python",
      "args": ["/path/to/mcp-clickup-bre/server.py"],
      "env": {
        "CLICKUP_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

## Design notes

100+ tools sharing one file (or, now, one package) only stays maintainable if the boring parts are genuinely uniform. A few choices that keep it that way:

- **One shared HTTP client.** `clickup_mcp/client.py` builds a single `httpx.AsyncClient` at import time, with the `Authorization` header set once from `CLICKUP_API_TOKEN`. Every tool module imports that same instance — no per-call auth wiring, no per-module client construction.
- **Uniform dispatch, not a router library.** Each category module (tasks, goals, docs, ...) exposes `handle(name, arguments) -> Optional[List[TextContent]]`: it returns a result if it owns that tool name, or `None` so the next category gets a turn. `server.py` just loops over the category list. Adding a tool means adding one `Tool()` schema and one branch in the matching category's `handle()` — nothing else has to know about it.
- **Allow-listed field forwarding.** Handlers don't forward `arguments` verbatim into the request body; each one explicitly lists the fields it accepts (see `create_task`, `update_task`), so an unexpected key in the input is silently dropped rather than sent to ClickUp. Covered by `tests/test_request_building.py`.
- **ClickUp's array-param convention.** List-typed filters (`statuses`, `assignees`, `tags`) are sent as `key[]=value` repeated params, matching what ClickUp's API expects — not JSON-encoded arrays. Covered by `tests/test_request_building.py`.
- **Error mapping — including the honest gap.** `call_tool` wraps every dispatch in one `try/except`, catching `httpx.HTTPStatusError` and any other exception (bad/missing arguments, a non-JSON response body, a network failure) and returning `{"error": "..."}`. What it does **not** do is call `response.raise_for_status()` — so a non-2xx response from ClickUp that still has a JSON body (ClickUp's own `{"err": "...", "ECODE": "..."}` error envelope) comes back to the caller looking like ordinary data, not an error. This is real, current behavior, pinned down by `tests/test_error_mapping.py` rather than left as an assumption. Worth fixing before this server is used against a token with limited scopes.
- **Bulk operations degrade per-item, not all-or-nothing.** `bulk_create_tasks`, `bulk_update_tasks`, and `bulk_delete_tasks` catch failures per item and return a `{results, total, successful}` summary, so one bad task in a batch of 50 doesn't lose the other 49.

## Project layout

The server used to be a single ~3,200-line file. It's now split by ClickUp API area, with `server.py` as a thin entrypoint:

```
server.py                      # MCP entrypoint: registers list_tools/call_tool, runs over stdio
clickup_mcp/
  client.py                    # the shared httpx.AsyncClient + token validation
  tools/
    __init__.py                # CATEGORIES: the ordered list every dispatch/list call walks
    workspace.py                # workspaces, spaces, folders, lists (18 tools)
    tasks.py                    # tasks, comments, dependencies, attachments, watchers (14 tools)
    time_tracking.py            # timers and time entries (5 tools)
    goals.py                    # goals and key results (7 tools)
    custom_fields.py            # custom field CRUD + value get/set (6 tools)
    views.py                    # views (3 tools)
    tags.py                     # tags (3 tools)
    statuses.py                 # list statuses (3 tools)
    webhooks.py                 # webhook CRUD (4 tools)
    documents.py                # ClickUp Docs (6 tools)
    checklists.py               # task checklists (4 tools)
    task_templates.py           # template read + apply (3 tools)
    members.py                  # team members (2 tools)
    shared_hierarchy.py         # shared hierarchy (1 tool)
    bulk_operations.py          # bulk create/update/delete tasks (3 tools)
    automations.py              # automation rule CRUD (5 tools)
    enhanced_templates.py       # template create/update/delete (3 tools)
    delete_operations.py        # delete for space/folder/list/task/comment/goal/key-result (7 tools)
    dashboard_analytics.py      # dashboard + analytics + reporting (4 tools)
```

Every module follows the same shape: a `TOOLS: List[Tool]` schema list and an `async def handle(name, arguments)`. This split was verified behaviorally, not just by inspection — every one of the 101 tools was run against both the original single-file implementation and this package, through mocked HTTP, and produced byte-identical output before the old file was replaced.

## Available tools

<details>
<summary><strong>Workspace &amp; Organization</strong> — 18 tools (workspaces, spaces, folders, lists)</summary>

| Tool | Description |
|---|---|
| `get_authorized_user` | Get the authenticated user's information |
| `get_teams` | Get all teams the authenticated user is part of |
| `get_workspaces` | Get all workspaces |
| `get_workspace` | Get a specific workspace by ID |
| `get_spaces` | Get all spaces in a workspace |
| `get_space` | Get a specific space by ID |
| `create_space` | Create a new space |
| `update_space` | Update a space |
| `get_folders` | Get all folders in a space |
| `get_folder` | Get a specific folder by ID |
| `create_folder` | Create a new folder |
| `update_folder` | Update a folder |
| `get_lists` | Get all lists in a folder or space |
| `get_list` | Get a specific list by ID |
| `create_list` | Create a new list |
| `update_list` | Update a list |
| `get_list_members` | Get members of a list |
| `get_list_views` | Get views for a list |

</details>

<details>
<summary><strong>Task Management</strong> — 14 tools (CRUD, search, comments, dependencies, time, attachments)</summary>

| Tool | Description |
|---|---|
| `get_tasks` | Get tasks from a list, folder, or space with filters |
| `get_task` | Get a specific task by ID |
| `create_task` | Create a new task |
| `update_task` | Update an existing task |
| `search_tasks` | Search for tasks across workspace |
| `get_task_comments` | Get comments for a task |
| `create_task_comment` | Add a comment to a task |
| `update_task_comment` | Update a task comment |
| `get_task_dependencies` | Get task dependencies |
| `create_task_dependency` | Create a task dependency |
| `get_task_time_entries` | Get time entries for a task |
| `create_task_time_entry` | Create a time entry for a task |
| `get_task_attachments` | Get attachments for a task |
| `get_task_watchers` | Get watchers for a task |

</details>

<details>
<summary><strong>Time Tracking</strong> — 5 tools</summary>

| Tool | Description |
|---|---|
| `get_time_entries` | Get time entries with filters |
| `get_time_entry` | Get a specific time entry |
| `start_time_entry` | Start a timer for a task |
| `stop_time_entry` | Stop a running timer |
| `update_time_entry` | Update a time entry |

</details>

<details>
<summary><strong>Goals &amp; Key Results</strong> — 7 tools</summary>

| Tool | Description |
|---|---|
| `get_goals` | Get goals for a workspace |
| `get_goal` | Get a specific goal |
| `create_goal` | Create a new goal |
| `update_goal` | Update a goal |
| `get_goal_key_results` | Get key results for a goal |
| `create_goal_key_result` | Create a key result for a goal |
| `update_goal_key_result` | Update a goal key result |

</details>

<details>
<summary><strong>Custom Fields</strong> — 6 tools</summary>

| Tool | Description |
|---|---|
| `get_custom_fields` | Get custom fields for a list |
| `get_custom_field` | Get a specific custom field |
| `update_custom_field_value` | Update a custom field value for a task |
| `create_custom_field` | Create a custom field for a list |
| `delete_custom_field` | Delete a custom field |
| `remove_custom_field_value` | Remove a custom field value from a task |

</details>

<details>
<summary><strong>Views</strong> — 3 tools</summary>

| Tool | Description |
|---|---|
| `get_views` | Get views for a workspace or space |
| `get_view` | Get a specific view |
| `get_view_tasks` | Get tasks from a view |

</details>

<details>
<summary><strong>Tags</strong> — 3 tools</summary>

| Tool | Description |
|---|---|
| `get_tags` | Get tags for a workspace |
| `create_tag` | Create a tag |
| `update_tag` | Update a tag |

</details>

<details>
<summary><strong>Statuses</strong> — 3 tools</summary>

| Tool | Description |
|---|---|
| `get_list_statuses` | Get statuses for a list |
| `create_list_status` | Create a status for a list |
| `update_list_status` | Update a list status |

</details>

<details>
<summary><strong>Webhooks</strong> — 4 tools</summary>

| Tool | Description |
|---|---|
| `get_webhooks` | Get webhooks for a workspace |
| `create_webhook` | Create a webhook |
| `update_webhook` | Update a webhook |
| `delete_webhook` | Delete a webhook |

</details>

<details>
<summary><strong>Documents</strong> — 6 tools</summary>

| Tool | Description |
|---|---|
| `search_documents` | Search documents in a workspace |
| `get_document` | Get a specific document |
| `create_document` | Create a new document with rich formatting |
| `update_document` | Update a document with formatting and embeds |
| `delete_document` | Delete a document |
| `create_document_page` | Create a page in a document |

</details>

<details>
<summary><strong>Checklists</strong> — 4 tools</summary>

| Tool | Description |
|---|---|
| `get_task_checklists` | Get checklists for a task |
| `create_task_checklist` | Create a checklist for a task |
| `create_checklist_item` | Create a checklist item |
| `update_checklist_item` | Update a checklist item |

</details>

<details>
<summary><strong>Task Templates</strong> — 6 tools (read/apply + create/update/delete)</summary>

| Tool | Description |
|---|---|
| `get_task_templates` | Get task templates for a workspace |
| `get_task_template` | Get a specific task template |
| `create_task_from_template` | Create a task from a template |
| `create_task_template` | Create a new task template |
| `update_task_template` | Update a task template |
| `delete_task_template` | Delete a task template |

</details>

<details>
<summary><strong>Members</strong> — 2 tools</summary>

| Tool | Description |
|---|---|
| `get_team_members` | Get members of a team |
| `get_team_member` | Get a specific team member |

</details>

<details>
<summary><strong>Shared Hierarchy</strong> — 1 tool</summary>

| Tool | Description |
|---|---|
| `get_shared_hierarchy` | Get shared hierarchy for a workspace |

</details>

<details>
<summary><strong>Bulk Operations</strong> — 3 tools</summary>

| Tool | Description |
|---|---|
| `bulk_create_tasks` | Batch create multiple tasks, with per-item success/failure reporting |
| `bulk_update_tasks` | Batch update multiple tasks, with per-item success/failure reporting |
| `bulk_delete_tasks` | Batch delete multiple tasks, with per-item success/failure reporting |

</details>

<details>
<summary><strong>Automation Rules</strong> — 5 tools</summary>

| Tool | Description |
|---|---|
| `get_automations` | Get automation rules for a workspace |
| `get_automation` | Get a specific automation rule |
| `create_automation` | Create a new automation rule |
| `update_automation` | Update an automation rule |
| `delete_automation` | Delete an automation rule |

</details>

<details>
<summary><strong>Delete Operations</strong> — 7 tools</summary>

| Tool | Description |
|---|---|
| `delete_space` | Delete a space |
| `delete_folder` | Delete a folder |
| `delete_list` | Delete a list |
| `delete_task` | Delete a task |
| `delete_comment` | Delete a comment |
| `delete_goal` | Delete a goal |
| `delete_key_result` | Delete a key result |

</details>

<details>
<summary><strong>Dashboard &amp; Analytics</strong> — 4 tools</summary>

| Tool | Description |
|---|---|
| `get_workspace_dashboard` | Get dashboard data for a workspace |
| `get_space_dashboard` | Get dashboard data for a space |
| `get_task_analytics` | Get analytics data for tasks |
| `get_time_tracking_report` | Get time tracking report data |

</details>

## Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite (`tests/`) is organized by what it's proving, not by which file it happens to test:

- **`test_tool_schemas.py`** — one parametrized test run against all 101 tools, checking every name, description, and JSON-Schema `inputSchema` (valid types, `required` fields that actually exist in `properties`, documented parameters). This is the test that caught a real bug: `update_custom_field_value`'s `value` field declared `"type": "any"`, which isn't a JSON-Schema type at all — fixed by omitting `type` (the spec-correct way to say "no type constraint").
- **`test_request_building.py`** — asserts the actual URL, query params, and JSON body each tool sends: container-id fallback order in `get_tasks` (list → folder → space), the `key[]` array-param convention, allow-listed field forwarding in `create_task`/`update_task`, and pagination params.
- **`test_error_mapping.py`** — pins down how missing arguments, unknown tool names, non-JSON responses, network failures, and (deliberately) a ClickUp error envelope on a 4xx all come out the other side.
- **`test_bulk_operations.py`** — the per-item success/failure aggregation in the three bulk tools.
- **`test_dispatch_smoke.py`** — runs every one of the 101 tools with the minimal arguments its own schema requires, against mocked HTTP, and confirms exactly one category module claims each tool name.

All HTTP is intercepted with [respx](https://lundberg.github.io/respx/); nothing in the suite touches the network.

CI (`.github/workflows/ci.yml`) runs the suite on Python 3.11 for every push and pull request against `main`.

## Known limitations

- **Error responses aren't raised.** As noted above, `response.raise_for_status()` is never called, so a non-2xx ClickUp response with a JSON body is returned as if it were a success. Fixing this is straightforward (raise, and let the existing `except httpx.HTTPStatusError` handler — currently unreachable — do its job) but changes behavior for any client currently depending on seeing ClickUp's raw error body, so it's called out here rather than silently changed.
- **No rate-limit handling.** ClickUp enforces per-token rate limits; this server doesn't back off or retry on `429`.
- **No pagination looping.** Tools that accept a `page` parameter return one page; the caller is responsible for looping.

## License

MIT — see [LICENSE](LICENSE).
